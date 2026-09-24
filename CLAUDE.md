# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A research experiment on **tactic-finisher interchangeability** in Lean 4 / Mathlib. Two data sources feed the same question ("when the author wrote `linarith`, would `omega`/`norm_num`/… have closed the goal?"):

1. `Lean4/Q{1..10}.lean` — ten hand-formalized GSM8K arithmetic word problems, each a small `theorem … := by unfold …; <finisher>` proof.
2. Mathlib candidates — short (`≤ MAX_TACTICS=5` tactic) proofs in the vendored Mathlib checkout whose terminal tactic is one of the tracked finishers.

The finishers under study: `rfl`, `decide`, `norm_num`, `omega`, `linarith`, `ring`. Ranked by cost in `scripts/analyze_matrix.py::SIMPLICITY` (rfl cheapest, linarith heaviest) — cost order drives the "compression" analysis.

## External dependency: lean-repl

Scripts drive Lean through the [leanprover-community REPL](https://github.com/leanprover-community/repl), expected as a **sibling checkout**: `../lean-repl/.lake/build/bin/repl` (see `REPL_BIN` in the Python drivers and `$REPL` in `extract_traces.sh`). It must be built (`lake build` inside `../lean-repl`) before any script here works. The REPL is invoked with `lake env` from this repo so it inherits our Mathlib env.

## Common commands

```bash
# Build the Lean library (from repo root).
lake build

# End-to-end pipeline for the local Q*.lean experiment.
scripts/extract_traces.sh                    # -> data/traces/Q{n}.json  (needs lean-repl built)
python scripts/summarize_traces.py           # prints finisher head distribution
python scripts/run_matrix.py                 # -> data/matrix.csv  (Q*.lean × 4 finishers)

# Mathlib candidate pipeline.
python scripts/find_mathlib_candidates.py    # scans .lake/packages/mathlib -> data/candidates{,_all}.csv
python scripts/run_matrix_mathlib_v2.py [LIMIT] [--workers=N]
                                             # -> data/matrix_mathlib.csv (parallel, text-substitution variants)
python scripts/analyze_matrix.py             # prints interchange-rate matrix + compression stats

# Run one specific candidate row (useful when debugging a probe):
python scripts/run_matrix_mathlib_v2.py 1    # process only the first row of candidates.csv
```

There is no test suite. "Passing" for a variant means: after text-substituting the finisher line, loading the modified file in the REPL introduces **no new error lines** relative to the baseline load (see `errors_at_or_after` and the baseline diff in `run_matrix_mathlib_v2.py`).

## Two probe strategies — know which one you're touching

Both `run_matrix*.py` families share the same premise (swap the last tactic, check whether the goal still closes) but differ in how they reconstruct the proof:

- **`run_matrix.py` / `run_matrix_mathlib.py` (signature-reconstruction)**: parses `theorem NAME sig := by …` out of source and sends a synthetic `example sig := by <preamble>; <finisher>` to the REPL inside the original namespace. Fragile — pretty-printed goal states aren't round-trippable (they insert `↑` coercions), which is why the driver reads the signature *verbatim from source* rather than from REPL output.
- **`run_matrix_mathlib_v2.py` (text-substitution, preferred for Mathlib)**: writes N variant files to the scratchpad, each identical to the original except that the finisher line is replaced. Loads each via `{"path": ...}`. Bypasses signature reconstruction entirely — `variable`s, `open`s, macros, and local options remain intact. This is the version to prefer/extend.

Variant files land in a hard-coded scratchpad path inside `run_matrix_mathlib_v2.py` (`SCRATCH = /private/tmp/claude-502/.../scratchpad/variants`). If that session-id-bearing path becomes stale, update the constant — it isn't parameterized.

## Repo layout worth knowing

- `Lean4/Q*.lean` — one theorem per file, each `import Mathlib.Tactic` + a `namespace` + defs + one theorem. Category comments (e.g. "sequential state-change") indicate the GSM8K taxonomy bucket.
- `Lean4.lean` — the lakefile's `defaultTargets` root. **Note:** it currently `import Lean4.Basic` but `Lean4/Basic.lean` does not exist, so `lake build` on the default target fails; the Q files build individually. Either add `Basic.lean` or fix the root import if you need a clean top-level build.
- `Extraction/ProbeAll.lean` — one-line `import Mathlib`, used as a scratch env for probes.
- `data/traces/Q*.json` — REPL `allTactics: true` output per Q file (input to `run_matrix.py` and `summarize_traces.py`).
- `data/candidates.csv` — balanced sample (12 per finisher) written by `find_mathlib_candidates.py`. `data/candidates_all.csv` is the unfiltered superset.
- `data/matrix.csv`, `data/matrix_mathlib.csv` — final experiment outputs.
- `csv/notes.txt` — hand notes on which finisher is appropriate when (design rationale, not code).

## Conventions when editing

- `lakefile.toml` sets `autoImplicit = false`. Declarations must bind their variables explicitly.
- Toolchain is pinned via `lean-toolchain` (`leanprover/lean4:v4.34.0-rc2`). Do not upgrade Lean without also refreshing the Mathlib pin in `lake-manifest.json`.
- Q files follow a stable shape: docstring → `namespace X` → `def`s for named quantities → one theorem, proof body `unfold …; <finisher>`. Preserve this shape when adding Q11+ so the probe scripts keep parsing them.
- When adding a finisher to the study, update **all** of: `FINISHERS` in `run_matrix*.py`, `FINISHERS` in `find_mathlib_candidates.py`, `FINISHERS` and `SIMPLICITY` in `analyze_matrix.py`, and (if it should count in the trace summary) `FINISHERS` in `summarize_traces.py`. There is no shared constants module.
