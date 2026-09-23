#!/usr/bin/env python3
"""Summarize tactic-level traces produced by extract_traces.sh."""
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TRACE_DIR = REPO / "data" / "traces"

FINISHERS = {"rfl", "decide", "norm_num", "omega", "linarith", "ring", "simp", "exact", "trivial"}


def tactic_head(t: str) -> str:
    """First identifier of a tactic string (so 'unfold foo bar' -> 'unfold')."""
    m = re.match(r"[A-Za-z_][A-Za-z0-9_']*", t.strip())
    return m.group(0) if m else t.strip().split()[0]


def summarize(path: Path):
    data = json.loads(path.read_text())
    tactics = data.get("tactics", [])
    heads = [tactic_head(t["tactic"]) for t in tactics]
    finisher = heads[-1] if heads else "(none)"
    return {
        "file": path.stem,
        "n_tactics": len(tactics),
        "heads": heads,
        "finisher": finisher,
    }


def main():
    rows = [summarize(p) for p in sorted(TRACE_DIR.glob("Q*.json"),
                                          key=lambda p: int(re.sub(r"\D", "", p.stem) or 0))]
    print(f"{'file':<6} {'n':>3}  finisher      tactics")
    print("-" * 70)
    for r in rows:
        print(f"{r['file']:<6} {r['n_tactics']:>3}  {r['finisher']:<12}  {' · '.join(r['heads']) or '(empty)'}")
    print()
    from collections import Counter
    fin_counts = Counter(r["finisher"] for r in rows if r["n_tactics"])
    print("finisher distribution:", dict(fin_counts))
    lin_arith_targets = [r["file"] for r in rows if r["finisher"] in {"linarith", "omega"}]
    print(f"linarith/omega-finished theorems ({len(lin_arith_targets)}): {lin_arith_targets}")


if __name__ == "__main__":
    main()
