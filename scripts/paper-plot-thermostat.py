"""Generate the paper's illustrative thermostat figure from saved logs.

Requires matplotlib. Run from the repository root. Optional --preview PATH
also exports a PNG for visual inspection; the paper uses the vector PDF.
"""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "experiments/thermostat"
TRACES = [
    ("GPT-6 Luna", "20261029T051556178164Z-thermostat-v3",
     "Heater switched on and off", "#26744d"),
    ("Claude Haiku 5.5", "20261029T051556178231Z-thermostat-v3",
     "Heater remains off", "#a64f35"),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview", type=Path)
    args = parser.parse_args()
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11,
                         "pdf.fonttype": 42, "axes.spines.top": False,
                         "axes.spines.right": False})
    fig = plt.figure(figsize=(7.2, 3.6), layout="constrained")
    grid = fig.add_gridspec(1, 2, wspace=.08)
    for col, (name, directory, description, color) in enumerate(TRACES):
        rows = [json.loads(line) for line in
                (RUNS / directory / "run-0.jsonl").read_text(encoding="utf-8").splitlines()]
        states = [rows[0]["env"]] + [s for r in rows for s in r["trajectory"]]
        inner = grid[col].subgridspec(2, 1, height_ratios=[3.5, 1], hspace=.03)
        ax = fig.add_subplot(inner[0])
        heater = fig.add_subplot(inner[1], sharex=ax)
        assert len(rows) == 36 and abs(states[-1]["minutes"] - 360) < 1e-6
        ax.plot([s["minutes"] for s in states], [s["celsius"] for s in states], lw=2.1, color=color)
        sensed = [r for r in rows if any(n == "thermometer" for n, _ in r["tool_calls"])]
        ax.scatter([r["env"]["minutes"] for r in sensed],
                   [r["env"]["celsius"] for r in sensed],
                   facecolors="white", edgecolors=color, s=34, zorder=3, linewidths=1.2)
        ax.set_title(f"({chr(97 + col)}) {name}\n{description}", loc="left", fontsize=11)
        ax.set_ylim(7, 25)
        ax.set_yticks([10, 15, 20, 25])
        ax.set_ylabel("Room temperature (\N{DEGREE SIGN}C)" if col == 0 else "")
        ax.tick_params(axis="x", labelbottom=False)
        ax.grid(alpha=.15)
        times = [r["env"]["minutes"] for r in rows] + [states[-1]["minutes"]]
        settings = [int(r["trajectory"][0]["heater"]) for r in rows]
        settings.append(settings[-1])
        heater.step(times, settings, where="post", color=color, lw=1.7)
        heater.fill_between(times, settings, step="post", color=color, alpha=.15)
        heater.set_ylim(-.1, 1.25)
        heater.set_yticks([0, 1], ["Off", "On"])
        heater.set_ylabel("Heater" if col == 0 else "")
        heater.set_xlim(0, 360)
        heater.set_xticks([0, 120, 240, 360])
        heater.set_xlabel("Simulated minutes")
        heater.grid(axis="x", alpha=.15)
    fig.legend(handles=[Line2D([], [], color="#3e4b53", lw=2, label="Simulator temperature"),
                        Line2D([], [], color="#3e4b53", marker="o", markerfacecolor="white",
                               ls="", label="Thermometer called")],
               loc="outside lower center", ncol=2, frameon=False)
    destination = ROOT / "results/paper-figures/thermostat-illustration.pdf"
    destination.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(destination, metadata={"CreationDate": None, "ModDate": None})
    if args.preview:
        fig.savefig(args.preview, dpi=180)
    plt.close(fig)


if __name__ == "__main__":
    main()
