#!/usr/bin/env python3
"""Analyze data/matrix_mathlib.csv into headline numbers for the paper.

Produces:
  1. Interchange rate matrix (per (original_finisher, candidate_finisher) pair):
     among proofs whose author used A, what fraction also close with B?
  2. Compression rate: for what fraction of proofs does a simpler finisher work?
  3. Coverage: how many candidates yielded meaningful data (i.e. their file
     loaded cleanly and the original finisher succeeded on itself).
"""

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MATRIX_CSV = REPO / "data" / "matrix_mathlib.csv"
CANDIDATES_CSV = REPO / "data" / "candidates.csv"

FINISHERS = ["rfl", "decide", "norm_num", "omega", "linarith", "ring"]
# Cost order: cheaper first. rfl is trivial; ring is heaviest normalization.
SIMPLICITY = {name: i for i, name in enumerate(["rfl", "decide", "norm_num", "ring", "omega", "linarith"])}


def load_matrix() -> list[dict]:
    rows = list(csv.DictReader(MATRIX_CSV.open()))
    for r in rows:
        r["ok"] = r["ok"] == "True"
    return rows


def per_candidate(rows: list[dict]) -> dict[str, dict]:
    """Group rows by candidate name -> {finisher: ok, ...}."""
    per: dict[str, dict] = defaultdict(dict)
    orig: dict[str, str] = {}
    for r in rows:
        per[r["name"]][r["candidate_finisher"]] = r["ok"]
        orig[r["name"]] = r["orig_finisher"]
    for name in per:
        per[name]["_orig"] = orig[name]
    return per


def interchange_matrix(per: dict[str, dict]) -> dict:
    """For each (author's-choice A, candidate B) pair, fraction of A-authored
    proofs where B also closes."""
    ok_count: dict[tuple[str, str], int] = Counter()
    total: dict[str, int] = Counter()
    for name, results in per.items():
        A = results["_orig"]
        # Only count proofs where A itself succeeded (i.e., meaningful baseline).
        if not results.get(A, False):
            continue
        total[A] += 1
        for B in FINISHERS:
            if results.get(B, False):
                ok_count[(A, B)] += 1
    return {"ok": ok_count, "total": total}


def coverage_stats(per: dict[str, dict]) -> dict:
    """How many candidates produced meaningful data?"""
    n_all = len(per)
    n_orig_ok = sum(1 for r in per.values() if r.get(r["_orig"], False))
    n_all_fail = sum(1 for r in per.values() if not any(r.get(f, False) for f in FINISHERS))
    return {"total": n_all, "orig_ok": n_orig_ok, "all_fail": n_all_fail}


def compression_stats(per: dict[str, dict]) -> dict:
    """A proof is 'compressible' if a strictly simpler finisher (than the
    author's) also closes the goal."""
    reachable = 0
    compressible = 0
    savings: Counter = Counter()
    for name, results in per.items():
        A = results["_orig"]
        if not results.get(A, False):
            continue
        reachable += 1
        a_cost = SIMPLICITY[A]
        cheaper = [B for B in FINISHERS if SIMPLICITY[B] < a_cost and results.get(B, False)]
        if cheaper:
            compressible += 1
            best = min(cheaper, key=lambda b: SIMPLICITY[b])
            savings[(A, best)] += 1
    return {"reachable": reachable, "compressible": compressible, "savings": savings}


def main() -> None:
    rows = load_matrix()
    per = per_candidate(rows)

    print("== Coverage ==")
    cov = coverage_stats(per)
    print(f"  total candidates:                       {cov['total']}")
    print(f"  original finisher reproduces baseline:  {cov['orig_ok']}")
    print(f"  all 6 finishers fail (unusable row):    {cov['all_fail']}")
    print()

    print("== Interchange rate matrix (rows = author's finisher, cols = candidate) ==")
    im = interchange_matrix(per)
    header = "author\\cand   " + "".join(f"{f:>10}" for f in FINISHERS) + f"    {'N':>4}"
    print(header)
    for A in FINISHERS:
        n = im["total"].get(A, 0)
        cells = []
        for B in FINISHERS:
            k = im["ok"].get((A, B), 0)
            cells.append("     -    " if n == 0 else f"{k}/{n:<4} ".rjust(10))
        print(f"  {A:<12}" + "".join(cells) + f"    {n:>4}")
    print()

    print("== Compression ==")
    comp = compression_stats(per)
    n = comp["reachable"]
    c = comp["compressible"]
    pct = 100 * c / n if n else 0
    print(f"  reachable proofs (author's finisher works): {n}")
    print(f"  compressible (a cheaper finisher works):    {c}  ({pct:.1f}%)")
    print("  savings (author → cheaper):")
    for (A, best), k in comp["savings"].most_common():
        print(f"    {A:<10} -> {best:<10}  x {k}")


if __name__ == "__main__":
    main()
