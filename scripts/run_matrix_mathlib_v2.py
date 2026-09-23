#!/usr/bin/env python3
"""Package 2 v2: text-substitution interchange matrix.

For each candidate:
  1. Read source file, locate finisher line by walking from `theorem NAME`.
  2. Write 4 variant files to scratchpad — each differs from source only in that
     one finisher-line's tactic.
  3. Load all 4 variants (and the original as baseline) in one REPL session via
     `path`. Record whether the variant introduces new errors relative to the
     baseline.

This bypasses signature reconstruction — variables, opens, macros, and special
options in the source file remain intact.
"""

from __future__ import annotations

import csv
import json
import re
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
REPL_BIN = REPO.parent / "lean-repl" / ".lake" / "build" / "bin" / "repl"
CANDIDATES_CSV = REPO / "data" / "candidates.csv"
OUT_CSV = REPO / "data" / "matrix_mathlib.csv"
SCRATCH = Path("/private/tmp/claude-502/-Users-Lisa-Documents-GitHub-lean4/4fdc1e61-8da2-4b05-93c5-3ab39975edc1/scratchpad/variants")

FINISHERS = ["rfl", "decide", "norm_num", "omega", "linarith", "ring"]


def find_finisher_line(text: str, theorem_name: str, kind: str) -> int | None:
    lines = text.splitlines()
    decl_re = re.compile(rf"^(?P<indent>\s*)(?:{kind})\s+{re.escape(theorem_name)}\b")
    theorem_idx = None
    base_indent = 0
    for i, line in enumerate(lines):
        m = decl_re.match(line)
        if m:
            theorem_idx = i
            base_indent = len(m.group("indent"))
            break
    if theorem_idx is None:
        return None
    end_sig = None
    for k in range(theorem_idx, min(theorem_idx + 20, len(lines))):
        if re.search(r":=\s*by\s*$", lines[k]):
            end_sig = k
            break
    if end_sig is None:
        return None
    last_tactic_idx = None
    j = end_sig + 1
    while j < len(lines):
        line = lines[j]
        if line.strip() == "":
            j += 1
            continue
        cur = len(line) - len(line.lstrip())
        if cur <= base_indent:
            break
        if not line.strip().startswith("--"):
            last_tactic_idx = j
        j += 1
    return last_tactic_idx


def build_variant_text(src_text: str, finisher_line_idx: int, candidate_finisher: str) -> str:
    lines = src_text.splitlines()
    orig = lines[finisher_line_idx]
    indent = orig[: len(orig) - len(orig.lstrip())]
    lines[finisher_line_idx] = f"{indent}{candidate_finisher}"
    return "\n".join(lines) + "\n"


def repl_batch(commands: list[dict], timeout_s: int = 1800) -> list[dict]:
    payload = "\n\n".join(json.dumps(c) for c in commands) + "\n\n"
    proc = subprocess.run(
        ["lake", "env", str(REPL_BIN)],
        cwd=str(REPO),
        input=payload,
        capture_output=True,
        text=True,
        timeout=timeout_s,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"REPL failed: {proc.stderr[:400]}")
    chunks = re.split(r"\n\s*\n", proc.stdout.strip())
    return [json.loads(c) for c in chunks if c.strip()]


def errors_at_or_after(resp: dict, line: int) -> list[dict]:
    out = []
    for m in resp.get("messages", []):
        if m.get("severity") != "error":
            continue
        pos = m.get("pos") or {}
        if pos.get("line", 0) >= line:
            out.append(m)
    return out


def run_candidate(candidate: dict) -> list[dict]:
    src = REPO / candidate["file"]
    if not src.exists():
        return [{
            "name": candidate["name"], "file": candidate["file"],
            "orig_finisher": candidate["finisher"], "candidate_finisher": f,
            "ok": False, "err": "source missing",
        } for f in FINISHERS]

    text = src.read_text(errors="replace")
    finisher_line = find_finisher_line(text, candidate["name"], candidate["kind"])
    if finisher_line is None:
        return [{
            "name": candidate["name"], "file": candidate["file"],
            "orig_finisher": candidate["finisher"], "candidate_finisher": f,
            "ok": False, "err": "finisher line not found",
        } for f in FINISHERS]

    SCRATCH.mkdir(parents=True, exist_ok=True)
    # Include the file stem in the variant name so two theorems with the same
    # name in different Mathlib files don't collide when workers run in parallel.
    file_stem = Path(candidate["file"]).stem
    variant_paths = []
    for f in FINISHERS:
        variant = build_variant_text(text, finisher_line, f)
        vp = SCRATCH / f"{file_stem}__{candidate['name']}__{f}.lean"
        vp.write_text(variant)
        variant_paths.append((f, vp))

    # Baseline first, then variants — one REPL session.
    commands = [{"path": str(src)}] + [{"path": str(vp)} for _, vp in variant_paths]
    responses = repl_batch(commands)
    baseline = responses[0]
    baseline_err_lines = {
        (m.get("pos") or {}).get("line")
        for m in baseline.get("messages", [])
        if m.get("severity") == "error"
    }

    rows = []
    for (f, _), resp in zip(variant_paths, responses[1:]):
        # A variant "closes the goal" iff every error line in the variant was
        # already an error line in the baseline. New errors near/at the finisher
        # line indicate the substitution failed.
        variant_err_lines = {
            (m.get("pos") or {}).get("line")
            for m in resp.get("messages", [])
            if m.get("severity") == "error"
        }
        new_errors = variant_err_lines - baseline_err_lines
        if new_errors:
            first_new = min(new_errors)
            for m in resp.get("messages", []):
                if m.get("severity") == "error" and (m.get("pos") or {}).get("line") == first_new:
                    err = m.get("data", "").replace("\n", " ")[:180]
                    break
            else:
                err = f"new error at L{first_new}"
            rows.append({
                "name": candidate["name"], "file": candidate["file"],
                "orig_finisher": candidate["finisher"], "candidate_finisher": f,
                "ok": False, "err": err,
            })
        else:
            rows.append({
                "name": candidate["name"], "file": candidate["file"],
                "orig_finisher": candidate["finisher"], "candidate_finisher": f,
                "ok": True, "err": "",
            })
    return rows


def _run_one(candidate: dict) -> list[dict]:
    """Worker entry point (must be top-level for ProcessPoolExecutor)."""
    try:
        return run_candidate(candidate)
    except Exception as e:  # noqa: BLE001
        return [{
            "name": candidate["name"], "file": candidate["file"],
            "orig_finisher": candidate["finisher"], "candidate_finisher": f,
            "ok": False, "err": f"driver error: {e}",
        } for f in FINISHERS]


def main(argv: list[str]) -> None:
    limit = None
    workers = 4
    for arg in argv[1:]:
        if arg.startswith("--workers="):
            workers = int(arg.split("=", 1)[1])
        else:
            limit = int(arg)
    candidates = list(csv.DictReader(CANDIDATES_CSV.open()))
    if limit:
        candidates = candidates[:limit]
    print(f"Processing {len(candidates)} candidates via text substitution "
          f"across {workers} workers ...", flush=True)

    all_rows: list[dict] = []
    completed = 0
    with ProcessPoolExecutor(max_workers=workers) as pool:
        future_to_cand = {pool.submit(_run_one, c): c for c in candidates}
        for fut in as_completed(future_to_cand):
            c = future_to_cand[fut]
            completed += 1
            rows = fut.result()
            n_ok = sum(1 for r in rows if r["ok"])
            print(f"[{completed:>2}/{len(candidates)} {c['finisher']:<10} "
                  f"{c['name'][:40]:<40}] {n_ok}/{len(FINISHERS)} finishers close",
                  flush=True)
            all_rows.extend(rows)

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["name", "file", "orig_finisher", "candidate_finisher", "ok", "err"])
        w.writeheader()
        w.writerows(all_rows)
    print(f"\nWrote {len(all_rows)} rows -> {OUT_CSV}")


if __name__ == "__main__":
    main(sys.argv)
