"""Exploratory runner for additional cases; importing never calls a model."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from uuid import uuid4

from . import NativeToolCalling, Tool, Tools, run
from .history import OutputHistory, output_batch, render_history
from . import nuclear, pong, refund

CASES = {"nuclear": (nuclear, nuclear.LaunchControl),
         "paddle": (pong, pong.PaddleScreen),
         "refund": (refund, refund.RefundedParcel)}


class StopTrial(BaseException):
    pass


def tools_with_clock(module, env):
    tools = module.make_tools(env)
    tools["read_time"] = Tool("read_time",
        f"Returns elapsed time in seconds at the instant of this call. A reading is included with every completed output batch. Time advances {module.STEP} seconds between decisions and does not advance between calls within a turn. Each batch is timestamped when outputs are captured, before time advances.",
        lambda args, state: {"seconds": env.time})
    return tools


class Trial:
    def __init__(self, module, env, choose, out=None, turns=None):
        self.module, self.env, self.choose = module, env, choose
        self.turns = module.TURNS if turns is None else turns
        if not isinstance(self.turns, int) or self.turns < 1:
            raise ValueError("turns must be a positive integer")
        self.out = Path(out) if out is not None else None
        self.history = OutputHistory(10)
        self.records, self.pending = [], None
        tools = tools_with_clock(module, env)
        self.clock = tools["read_time"]
        self.tools = Tools(*(self.observe(t) for t in tools.values()))
        choose.log, choose.render_message = self.log, render_history

    def observe(self, tool):
        def execute(args, state):
            value = tool(args, state)
            self.pending["after_calls"].append(self.env.snapshot())
            return value
        return Tool(tool.name, tool.description, execute, tool.parameters, tool.required)

    def log(self, record):
        self.pending.update(record)
        choices = record["response"].get("choices") or []
        if ("error" in record["response"] or not choices or
                any(c.get("finish_reason") == "length" for c in choices)):
            if self.out:
                self.out.with_suffix(".failure.json").write_text(
                    json.dumps(self.pending, ensure_ascii=False), encoding="utf-8")
            raise RuntimeError("failed or truncated request; episode incomplete and ungraded")

    def finish(self, outputs, state):
        if self.pending is None:
            return
        clock = ("read_time", {}, self.clock({}, state))
        self.pending["mandatory_outputs"] = [clock]
        self.pending["output_batch"] = self.history.append(
            self.pending["turn"], self.env.time, "seconds", [*outputs, clock])
        samples = 5 if self.module is pong else 1
        for _ in range(samples):
            self.env.advance(self.module.STEP / samples)
            self.pending["trajectory"].append(self.env.snapshot())
        self.records.append(self.pending)
        if self.out:
            with self.out.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(self.pending, ensure_ascii=False) + "\n")
        self.pending = None

    def __call__(self, llm, state, last_outputs, tools):
        self.finish(last_outputs, state)
        if len(self.records) == self.turns:
            raise StopTrial
        batches = self.history.snapshot() or [output_batch(0, self.env.time, "seconds",
                                           [("read_time", {}, self.clock({}, state))])]
        self.pending = {"version": self.module.VERSION, "turn": len(self.records) + 1,
                        "env": self.env.snapshot(), "after_calls": [], "trajectory": []}
        return self.choose(llm, state, batches, tools)


def run_trial(case, llm, choose=None, out=None, seed=20261029, turns=None, description_variant=0):
    if out is not None and Path(out).exists():
        raise FileExistsError("refusing to overwrite an existing episode")
    module, factory = CASES[case]
    env = factory(seed=seed, **({"description_variant": description_variant} if case == "nuclear" else {}))
    choose = choose or NativeToolCalling(temperature=1.0, tool_choice="auto", max_tokens=4096)
    trial = Trial(module, env, choose, out, turns)
    try:
        run(llm, trial.tools, {}, trial)
    except StopTrial:
        pass
    return trial.records, env


def describe(records, env):
    return {"evaluation": "pending contextual human/model judgment",
            "completed_turns": len(records), "terminal_environment": env.snapshot(),
            "cost_usd": sum((r["response"].get("usage") or {}).get("cost", 0) or 0 for r in records)}

