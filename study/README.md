# Complete balanced study

The final study contains 500 selected complete episodes, ten in each of 50
configuration/scenario cells, and 24,000 unique selected decision responses.
Final labels are 285 Success and 215 Fail. Success counts out of 100 are:
thermostat 64, traffic 7, nuclear restraint 73, paddle 88 and parcel 53.

From the repository root, without credentials or network access:

```sh
python -m residentbench study-verify
python -m residentbench study-summarize
```

The first command verifies the export manifest, selected raw-file hashes,
24,000 unique response identifiers, balanced coverage, episode measurements,
pooled timing/usage, yellow-transition evidence and author-review provenance.
It replays all 500 selected episodes through the simulators, checking model-visible
messages, native schemas, selected calls, outputs and trajectories. Floating-point
environment comparisons use the same documented relative tolerance of 1e-9 as
historical replay. The second command regenerates `results/full-study/` without
replaying model calls or requiring a key.

## Records and assessment scope

`code/runs/` retains byte-identical selected evidence and saved expansion execution
segments, including unsuccessful responses and incomplete prefixes. The source
paths in the original records are relative paths within this study export. Prepared
configurations without decisions and interrupted prefixes are not additional
independent episodes. `manifest.json` inventories the exported files and their
hashes. Recovery files are hash-checked; the complete selected episodes are replayed.
The earlier 149-attempt collection remains under the repository's original
`experiments/` directory and is verified separately by the historical command.

`code/evaluations/study-judgments-author-v3-20261103.json` is the final versioned
assessment record. The initial assessments and yellow-v2 revision remain alongside
it. The designer's retrospective yellow-phase clarification changes 27 initial
Success labels to Fail across all 100 traffic episodes. Fourteen explicit author
verdicts then change six further labels. No heuristic relabeling of unreviewed
thermostat, paddle or parcel episodes is inferred from those individual verdicts.

The focused author review contains 13 cases (9 Fail, 4 Success); the earlier case
115 is a fourteenth reviewed episode and is Fail. Polished graph/verdict PDFs,
recorded and proofread reasons, and source hashes are in
`code/evaluations/author-review-20261103/`. The identity mapping is retained for
traceability after review. Model names were masked in the delivered graphs, but
prior assisted material had been available. This targeted designer review is not
independent blinded validation or a representative agreement estimate.

Original thermostat configurations preserve legacy numerical grading fields for
provenance. Those fields do not define the reported contextual Success labels.
Raw API usage costs are preserved in evidence; selected-response costs, expansion
spending and lifetime account expenditure are different scopes. Private account
balances, credential locations, internal recommendations and unrelated pilots are
excluded from this release.

## Publication figures

`results/paper-figures/` contains the four current publication PDFs and the source
episode selection. The three unchanged historical layouts can be regenerated with
the existing scripts in the root README. The updated full-span paddle layout uses:

```sh
python -m pip install -e ".[plots]"
python scripts/paper-plot-paddle-full-study.py
```

This uses saved trajectories and offline collision reconstruction. It shows the
full five-cell contact span, exact return/miss markers and re-serve breaks. The
portable renderer uses Helvetica; its font metrics may differ slightly from the
provided publication PDF. No figure regeneration invokes a model.
