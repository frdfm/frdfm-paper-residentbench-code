"""Full-width paper figure from the GPT-6 Luna traffic-v2 rerun.

Requires Matplotlib. Optional --preview PATH exports a PNG for layout QA.
"""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / "experiments/traffic/20261029T051818764331Z-traffic-v2"
ROADS = ("north", "south", "east", "west")
QUEUE_COLOURS = ("#316da6", "#cf7828", "#795aa6", "#278979")
SIGNAL_COLOURS = ("#bd4848", "#e5b847", "#3a9863")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview", type=Path)
    args = parser.parse_args()
    config = json.loads((FOLDER / "config.json").read_text(encoding="utf-8"))
    rows = [json.loads(s) for s in (FOLDER / "run-0.jsonl").read_text(encoding="utf-8").splitlines()]
    assert config["model"] == "openai/gpt-6-luna" and config["history_turns"] == 10
    terminal = rows[-1]['trajectory'][-1]
    assert len(rows) == 60 and terminal['seconds'] == 300
    assert sum(terminal['departed'].values()) == 82 and terminal['collision_count'] == 0
    states = [rows[0]["env"]] + [s for r in rows for s in r["trajectory"]]
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11,
                         "pdf.fonttype": 42, "axes.spines.top": False,
                         "axes.spines.right": False})
    fig = plt.figure(figsize=(7.2, 4.9), layout="constrained")
    grid = fig.add_gridspec(2, 1, height_ratios=[3, 1.5], hspace=.08)
    queue = fig.add_subplot(grid[0])
    signal = fig.add_subplot(grid[1], sharex=queue)
    for road, colour in zip(ROADS, QUEUE_COLOURS):
        queue.plot([s["seconds"] for s in states], [s["queues"][road] for s in states],
                   color=colour, lw=1.6)
        readings = [r for r in rows if any(n == f"read_{road}_queue" for n, a in r["tool_calls"])]
        queue.scatter([r["env"]["seconds"] for r in readings],
                      [r["env"]["queues"][road] for r in readings], color=colour,
                      edgecolors="white", linewidths=.35, s=16, zorder=3)
    queue.set_title("GPT-6 Luna", loc="left", fontsize=13)
    queue.set_ylabel("Stopped cars waiting")
    queue.set_ylim(-.5, 21)
    queue.set_yticks([0, 5, 10, 15, 20])
    queue.tick_params(axis="x", labelbottom=False)
    queue.grid(alpha=.15)
    settings = [[{"red": 0, "yellow": 1, "green": 2}[
        (r["after_calls"][-1] if r["after_calls"] else r["env"])["signals"][road]]
        for r in rows] for road in ROADS]
    signal.pcolormesh([r["env"]["seconds"] for r in rows] + [300], range(5), settings,
                      cmap=ListedColormap(SIGNAL_COLOURS), norm=BoundaryNorm([-.5, .5, 1.5, 2.5], 3),
                      shading="flat", rasterized=False)
    signal.set_yticks([.5, 1.5, 2.5, 3.5], [r.capitalize() for r in ROADS])
    signal.set_ylim(4, 0)
    signal.set_ylabel("Traffic signals")
    signal.set_xlim(0, 300)
    signal.set_xticks([0, 60, 120, 180, 240, 300])
    signal.set_xlabel("Simulated time (seconds)")
    legend = [Line2D([], [], color=c, lw=2, label=r.capitalize()) for r, c in zip(ROADS, QUEUE_COLOURS)]
    legend += [Patch(color=c, label=n) for c, n in zip(SIGNAL_COLOURS, ["Red", "Yellow", "Green"])]
    legend += [Line2D([], [], color="#555555", marker="o", ls="", label="Sensor call")]
    fig.legend(handles=legend, loc="outside lower center", ncol=4, frameon=False, fontsize=10)
    destination = ROOT / "results/paper-figures/traffic-luna.pdf"
    destination.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(destination, metadata={"CreationDate": None, "ModDate": None})
    if args.preview:
        fig.savefig(args.preview, dpi=180)
    plt.close(fig)


if __name__ == "__main__":
    main()
