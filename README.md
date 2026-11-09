# ResidentBench: complete study and preserved arXiv-era snapshot

This release adds the final balanced study: **500 complete episodes, ten model
configurations, five simulations and 24,000 unique selected decisions**. Final
contextual judgments are **285 Success and 215 Fail**. See [study/README.md](study/README.md)
for the records, assessment scope and reproduction details.

The earlier arXiv-submission-era snapshot is preserved unchanged in commit
[733acca40dc06c3eec3a3a26054a32efda741413](https://github.com/frdfm/frdfm-paper-residentbench-code/tree/733acca40dc06c3eec3a3a26054a32efda741413).
The new release is a normal descendant commit; no history is rewritten. Original
experiments and historical commands remain available in the current tree.

## Reproduce the complete study offline

```sh
python -m residentbench study-verify
python -m residentbench study-summarize
python -m unittest discover -s tests
```

No key or network access is needed. The full-study commands check hashes, replay
all 500 selected episodes and reproduce measurements and final label provenance.
Summaries are written to `results/full-study/`. The original `verify`, `summarize`
and `plot` commands continue to address the historical 149-attempt snapshot.
Live `run` is optional and makes new paid requests; it is never used by verification.

| Scenario | Success / 100 | Fail / 100 |
|---|---:|---:|
| Thermostat | 64 | 36 |
| Traffic | 7 | 93 |
| Nuclear restraint | 73 | 27 |
| Paddle | 88 | 12 |
| Refunded parcel | 53 | 47 |

The final assessment combines retrospective Codex judgments, a retrospective
mandatory-yellow clarification applied to all traffic episodes, and explicit author
verdicts for fourteen selected cases. It is not a validated standard score or an
independent evaluator-agreement estimate. The versioned assessments and polished
human-review PDFs are included under `study/code/evaluations/`.

## Historical arXiv-era documentation

The documentation below describes the preserved original collection, not the
500-episode selected study above.

# ResidentBench: proof-of-concept reproduction

Five simulated situations accompany the exploratory paper: thermostat, traffic
intersection, fictional nuclear restraint, paddle game, and refunded-then-delivered
parcel. Models receive descriptive tool schemas and ten-turn output histories,
without an assigned task or role. Traffic and the three additional cases include
a mandatory capture-time clock; thermostat batches carry their observation time.

This demonstrates the platform, rather than the future fixed twenty-situation
standard. Results describe particular model IDs, providers and inference settings;
they do not establish properties of model families under different conditions.
Contextual human or instructed-judge evaluation determines behavioral success.
The exports here report observations rather than automatic benchmark grades.

## Offline quick start

Use Python 3.10 or newer, from this repository's root. No key is needed:

```sh
python -m residentbench verify
python -m residentbench summarize
python -m unittest discover -s tests
```

Verification checks SHA256 against immutable original configs/logs, then replays
all 149 episodes containing decisions through the actual simulators. It checks
every model-visible message, tool schema, executed call, output batch and
trajectory (numeric tolerance 1e-9). No network is needed. Runtime dependencies
are Python's standard library, with Matplotlib optional for plots:

```sh
python -m pip install -e ".[plots]"
python -m residentbench plot
```

Open `results/gallery/index.html` for every recorded episode. `results/episodes.csv`
contains settings, completed/planned intervals, completed-record API costs and
terminal states. `results/nuclear.csv` reproduces the ten-model ten-episode launch
counts. Plot regeneration uses saved observations; styling may vary by Matplotlib
version. Exact selected publication PDFs are under `results/paper-figures/`.
The gallery regenerates their underlying trajectories, not pixel-identical layouts.

To regenerate the four publication layouts from the included data:

```sh
python scripts/paper-plot-thermostat.py
python scripts/paper-plot-traffic-luna.py
python scripts/paper-plot-panel-selection.py --output results/paper-figures
```

`results/paper-figures/selection.json` identifies every selected source episode.
All ten nuclear description variants are defined in `residentbench/nuclear.py`
and repeated in the corresponding original tool schemas. `evaluations/` retains
the contextual instructions and original judgment records. The consolidated
`evaluations/episode-judgments.json` links all 149 decision-bearing attempts to
evidence and rationales: 143 completed episode judgments and six Incomplete
statuses. These retrospective Codex assessments were assigned by scenario, with
model identities visible and no independent agreement estimate; see `RESULTS.md`.

## Collected results and provenance

`experiments/manifest.json` records source-relative provenance, groups and SHA256
hashes. Under each scenario, episode folders retain unmodified `config.json`,
`run-0.jsonl` and available failure records. JSONL includes actual model-visible
input, raw API responses, parsed calls, tool outcomes and simulated trajectories.

| Group | Attempts | Complete |
|---|---:|---:|
| Initial thermostat/traffic settings and Qwen follow-ups | 12 | 8 |
| Initial nuclear/game/parcel pilots | 12 | 12 |
| Original four-model nuclear repetitions | 40 | 40 |
| Five-model coverage expansion | 70 | 70 |
| Grok coverage extension | 14 | 13 |
| **Main exploratory collection** | **148** | **143** |
| Separate interrupted DeepSeek endpoint diagnostic | 1 | 0 |
| Separate endpoint/setup rejections, no decisions | 15 | 0 |

Four truncated Qwen attempts and the Grok game interrupted by provider capacity
errors at 104/120 decisions are preserved without completed behavioral labels. Four original nuclear pilots are separate from the repeated matrix of
100 episodes (ten paraphrases per model). DeepSeek's 49/120 interrupted episode
is separate from the completed Morph follow-up. Setup rejections are indexed in
`experiments/setup-errors/`. Superseded historical protocols are excluded.

Original thermostat configs retain legacy `band` and `harm_above` fields solely
for provenance. These are not used by the simulators/exports and do not define
current pass/fail criteria. Parcel tool attempts can be rejected: ledger changes
show accepted repayment/return. Launch counts are direct observations; even a
rare simulated launch has a different implication from an ordinary task failure.
No aggregate result certifies safety.

## Optional new OpenRouter experiment

Live requests carry the shared **PseudoAgent** attribution: `HTTP-Referer:
https://www.pseudoconscious.com/` and `X-OpenRouter-Title: PseudoAgent`.
OpenRouter can group this usage with the existing PseudoAgent app. This sends
attribution headers to OpenRouter, not benchmark logs to the company website.

Create `key/OpenRouter.key` containing only your own API key, without quotes or
variable assignment. Actual keys are ignored by Git. Only the explicit `run`
command loads the key; offline tools do not. Use an included configuration to
preserve model, provider, reasoning, temperature and token settings:

```sh
python -m residentbench run --case nuclear --config experiments/nuclear/deepseek-deepseek-v4.1-flash-nuclear-v00/config.json --output reruns/my-nuclear-run
```

Before loading a key, the run command checks that the configuration matches the
selected scenario, version, tool schemas and fixed simulator settings.

This makes paid API requests. Fresh stochastic sampling and changes to available
models/providers can yield different outcomes. Offline replay reproduces saved
responses; a fresh API run is a new experiment. The output directory must be new.
Provider routing forbids fallback; unavailable models produce errors rather than
silent substitutions. The client uses native HTTP with no private dependencies.
All actuators affect local simulations, including launch, payment and messages.

`residentbench/` contains the harness, simulators and tools; `experiments/` stores
originals; `results/` stores derived views; `tests/` verifies actual replay and
accounting. Run from the repository root so accompanying data are available.
AGPL-3.0-or-later; see `LICENSE`.
