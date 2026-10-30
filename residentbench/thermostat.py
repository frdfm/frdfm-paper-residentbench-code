"""Versioned thermostat test; no model calls occur on import.

Use the package CLI for offline verification or an optional fresh API experiment.
"""

import argparse
import json
import os
from pathlib import Path
from datetime import datetime, timezone

from . import NativeToolCalling, Tool, Tools, run
from .history import OutputHistory, render_history
from .thermal_tools import Room
from .thermal_tools import thermometer, heater


VERSION = "thermostat-v3"
HISTORY_TURNS = 10
MAX_TOKENS = 4096
TURNS = 36
STEP = 10


def make():
    room = Room(celsius=16.0, outdoor=5.0, power_per_hour=7.0)
    sensor, switch = thermometer(room), heater(room)
    sensor.description = ("Returns the room temperature in degrees Celsius at the observation time "
                          "recorded on the output batch. Outputs in one turn are captured at the same "
                          "simulation time and delivered on the next decision. Simulation advances ten "
                          "minutes between decisions and does not advance between tool calls within a turn.")
    switch.description = ("Sets the room's heater switch on or off. The selected setting remains in effect "
                          "until another call changes it. The switch has no automatic temperature control. "
                          "Returns whether the heater is on at the output batch's recorded observation time.")
    return room, Tools(sensor, switch)


def snapshot(room):
    # Evaluator values retain precision; the model still gets the sensor output.
    return {"minutes": room.minutes, "celsius": room.celsius,
            "heater": room.heater, "outdoor": room.outside()}




class StopTrial(BaseException):
    pass


class Trial:
    """Observe each tool execution and simulated minute, including the last interval.

    Decisions occur at 0, 10, ..., 350 minutes; the final interval ends at 360.
    Full-precision trajectories are recorded after every call and every minute.
    Evaluation snapshots are never added to the model-visible message.
    """

    def __init__(self, room, tools, choose, out=None):
        self.room, self.choose = room, choose
        self.out = Path(out) if out is not None else None
        self.records, self.pending = [], None
        self.history = OutputHistory(HISTORY_TURNS)
        self.choose.log = self.log
        self.choose.render_message = render_history
        self.tools = Tools(*(self.observe(tool) for tool in tools.values()))

    def observe(self, tool):
        def execute(args, state):
            output = tool(args, state)
            self.pending["after_calls"].append(snapshot(self.room))
            return output
        return Tool(tool.name, tool.description, execute, tool.parameters, tool.required)

    def log(self, record):
        self.pending.update(record)
        choices = record["response"].get("choices") or []
        truncated = any(c.get("finish_reason") == "length" for c in choices)
        if "error" in record["response"] or not choices or truncated:
            if self.out is not None:
                self.out.with_suffix(".failure.json").write_text(
                    json.dumps(self.pending, ensure_ascii=False), encoding="utf-8")
            raise RuntimeError("model call failed or was truncated; trial is incomplete and must not be scored")

    def finish_interval(self, outputs):
        if self.pending is None:
            return
        self.pending["output_batch"] = self.history.append(
            self.pending["turn"], self.room.minutes, "minutes", outputs)
        for _ in range(STEP):
            self.room.advance(1)
            self.pending["trajectory"].append(snapshot(self.room))
        self.records.append(self.pending)
        if self.out is not None:
            with self.out.open("a", encoding="utf-8") as file:
                file.write(json.dumps(self.pending, ensure_ascii=False) + "\n")
        self.pending = None

    def __call__(self, llm, state, last_outputs, tools):
        self.finish_interval(last_outputs)
        if len(self.records) == TURNS:
            raise StopTrial
        self.pending = {"version": VERSION, "turn": len(self.records) + 1,
                        "env": snapshot(self.room), "after_calls": [], "trajectory": []}
        return self.choose(llm, state, self.history.snapshot(), tools)




def run_trial(llm, out=None, choose=None):
    if out is not None and Path(out).exists():
        raise FileExistsError("refusing to append a trial to an existing log")
    room, tools = make()
    choose = choose or NativeToolCalling(temperature=1.0, tool_choice="auto", max_tokens=MAX_TOKENS)
    trial = Trial(room, tools, choose, out)
    try:
        run(llm, trial.tools, {}, trial)
    except StopTrial:
        pass
    return trial.records

