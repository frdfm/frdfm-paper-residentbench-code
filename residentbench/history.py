"""Bounded factual output history; excludes replies, reasoning and private state."""
from collections import deque
import copy
from .model import render


def output_batch(turn, time, unit, outputs):
    return {"turn": turn, "observed_at": {"value": time, "unit": unit},
            "outputs": render({}, outputs)["last_outputs"]}


class OutputHistory:
    def __init__(self, turns=10):
        if turns < 1:
            raise ValueError("history length must be positive")
        self.turns = turns
        self.batches = deque(maxlen=turns)

    def append(self, turn, time, unit, outputs):
        batch = output_batch(turn, time, unit, outputs)
        self.batches.append(copy.deepcopy(batch))
        return batch

    def snapshot(self):
        return copy.deepcopy(list(self.batches))


def render_history(state, batches):
    return {"state": render(state, [])["state"], "output_history": copy.deepcopy(batches)}
