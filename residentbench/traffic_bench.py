"""Run an exploratory traffic trial; export trajectories, not automatic grades."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path

from . import NativeToolCalling, Tool, Tools, run
from .history import OutputHistory, output_batch, render_history
from .traffic import Intersection, make_tools, ROADS

VERSION = "traffic-v2"
HISTORY_TURNS = 10
TURNS = 60
STEP = 5
MAX_TURNS = 3500 // STEP
MAX_TOKENS = 4096
SEED = 20261028


class StopTrial(BaseException):
    pass


class TrafficTrial:
    def __init__(self, env, tools, choose, out=None, turns=TURNS):
        if isinstance(turns, bool) or not isinstance(turns, int) or turns < 1:
            raise ValueError("turns must be a positive integer")
        if env.time + turns * STEP > MAX_TURNS * STEP:
            raise ValueError("trial duration exceeds the traffic simulator's time horizon")
        self.env, self.choose, self.turns = env, choose, turns
        self.out = Path(out) if out else None
        self.records, self.pending = [], None
        self.history = OutputHistory(HISTORY_TURNS)
        self.clock = tools["read_time"]
        choose.log = self.log
        choose.render_message = render_history
        self.tools = Tools(*(self.observe(tool) for tool in tools.values()))

    def observe(self, tool):
        def execute(args, state):
            output = tool(args, state)
            self.pending["after_calls"].append(self.env.snapshot(vehicles=True))
            return output
        return Tool(tool.name, tool.description, execute, tool.parameters, tool.required)

    def log(self, record):
        self.pending.update(record)
        choices = record["response"].get("choices") or []
        if ("error" in record["response"] or not choices
                or any(c.get("finish_reason") == "length" for c in choices)):
            if self.out:
                self.out.with_suffix(".failure.json").write_text(json.dumps(self.pending), encoding="utf-8")
            raise RuntimeError("failed or truncated request; traffic trial incomplete")

    def finish_interval(self, outputs, state):
        if self.pending is None:
            return
        # Tools execute at one simulation instant. Capture their clock before
        # advancing, so an old queue reading is never paired with a new clock.
        clock = ("read_time", {}, self.clock({}, state))
        self.pending["mandatory_outputs"] = [clock]
        self.pending["output_batch"] = self.history.append(
            self.pending["turn"], self.env.time, "seconds", [*outputs, clock])
        for _ in range(STEP):
            self.env.advance(1)
            self.pending["trajectory"].append(self.env.snapshot(vehicles=True))
        self.records.append(self.pending)
        if self.out:
            with self.out.open("a", encoding="utf-8") as file:
                file.write(json.dumps(self.pending, ensure_ascii=False) + "\n")
        self.pending = None

    def __call__(self, llm, state, last_outputs, tools):
        self.finish_interval(last_outputs, state)
        if len(self.records) == self.turns:
            raise StopTrial
        batches = self.history.snapshot()
        if not batches:
            # Initial exposure has a clock only; no unsolicited queue readings.
            batches = [output_batch(0, self.env.time, "seconds",
                                    [("read_time", {}, self.clock({}, state))])]
        self.pending = {"version": VERSION, "turn": len(self.records) + 1,
                        "env": self.env.snapshot(vehicles=True), "after_calls": [],
                        "trajectory": [], "mandatory_outputs": []}
        return self.choose(llm, state, batches, tools)


def run_trial(llm, out=None, choose=None, seed=SEED, turns=TURNS):
    if out and Path(out).exists():
        raise FileExistsError("refusing to append to an existing trial")
    env = Intersection(seed=seed)
    choose = choose or NativeToolCalling(temperature=1.0, tool_choice="auto", max_tokens=MAX_TOKENS)
    trial = TrafficTrial(env, make_tools(env), choose, out, turns)
    try:
        run(llm, trial.tools, {}, trial)
    except StopTrial:
        pass
    return trial.records, env


def describe(records, env):
    """Descriptive data for contextual review; intentionally no pass/fail field."""
    return {"version": VERSION, "evaluation": "pending contextual human/model judgment",
            "completed_turns": len(records), "duration_seconds": env.time,
            "arrived": dict(env.arrived), "departed": dict(env.departed),
            "terminal_queues": {r: env.queue(r) for r in ROADS},
            "collisions": env.collisions, "emergency_stops": env.emergency_stops,
            "conflicting_green_seconds": env.conflicting_green_seconds,
            "stopped_vehicle_seconds": env.snapshot()["stopped_vehicle_seconds"],
            "sensor_calls": sum(n.startswith("read_") and n != "read_time"
                                for r in records for n, a in r["tool_calls"]),
            "signal_calls": sum(n.startswith("set_") for r in records for n, a in r["tool_calls"]),
            "model_idle_turns": sum(not r["tool_calls"] for r in records),
            "cost_usd": sum((r["response"].get("usage") or {}).get("cost", 0) or 0 for r in records)}

