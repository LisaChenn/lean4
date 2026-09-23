#!/usr/bin/env python3
"""Package 1: scan the local Mathlib checkout for short proofs whose terminal
tactic is one of the closed-form finishers.

Writes data/candidates.csv (a balanced sample) and data/candidates_all.csv
(everything matched, for auditing).
"""

from __future__ import annotations

import csv
import random
import re
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MATHLIB_ROOT = REPO / ".lake" / "packages" / "mathlib" / "Mathlib"
FINISHERS = ["rfl", "decide", "norm_num", "omega", "linarith", "ring"]
MAX_TACTICS = 5
SAMPLE_PER_FINISHER = 12  # 6 * 12 = 72 → we'll manually cull to ~50

KIND_RE = re.compile(r"^(?P<indent>\s*)(?P<kind>theorem|lemma|example)\b")
BY_RE = re.compile(r":=\s*by\s*$")
NAME_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_.']*")
HEAD_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def strip_block_comments(text: str) -> str:
    """Remove /-...-/ blocks so docstring code examples don't pollute matches."""
    out: list[str] = []
    depth = 0
    i = 0
    while i < len(text):
        if text[i:i + 2] == "/-":
            depth += 1
            i += 2
        elif text[i:i + 2] == "-/":
            depth = max(0, depth - 1)
            i += 2
        else:
            if depth == 0:
                out.append(text[i])
            i += 1
    return "".join(out)


def find_candidates_in_file(path: Path):
    try:
        text = path.read_text(errors="replace")
    except OSError:
        return
    text = strip_block_comments(text)
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        m = KIND_RE.match(lines[i])
        if not m:
            i += 1
            continue
        base = len(m.group("indent"))
        kind = m.group("kind")

        # Signature can span several lines. Look ahead ≤20 lines for `:= by`.
        end_sig = None
        for k in range(20):
            if i + k >= len(lines):
                break
            if BY_RE.search(lines[i + k]):
                end_sig = i + k
                break
        if end_sig is None:
            i += 1
            continue

        # Proof body: strictly-indented lines after `:= by`, until dedent.
        proof: list[str] = []
        j = end_sig + 1
        while j < len(lines):
            line = lines[j]
            if line.strip() == "":
                j += 1
                continue
            cur = len(line) - len(line.lstrip())
            if cur <= base:
                break
            proof.append(line.strip())
            j += 1

        real = [p for p in proof if not p.startswith("--")]
        if not real or len(real) > MAX_TACTICS:
            i = max(j, i + 1)
            continue

        last = re.sub(r"--.*$", "", real[-1]).strip()
        head = HEAD_RE.match(last)
        if not head or head.group(0) not in FINISHERS:
            i = max(j, i + 1)
            continue

        # For `example`, no name to extract.
        rest = lines[i][base + len(kind):].lstrip()
        nm = NAME_RE.match(rest)
        name = nm.group(0) if (kind != "example" and nm) else f"example@L{i + 1}"

        yield {
            "file": str(path.relative_to(REPO)),
            "line": i + 1,
            "kind": kind,
            "name": name,
            "finisher": head.group(0),
            "n_tactics": len(real),
            "last_tactic": last,
        }
        i = max(j, i + 1)


def main() -> None:
    all_rows: list[dict] = []
    n_files = 0
    for p in MATHLIB_ROOT.rglob("*.lean"):
        n_files += 1
        all_rows.extend(find_candidates_in_file(p))
    print(f"Scanned {n_files} files, matched {len(all_rows)} candidate proofs.")

    by_fin: dict[str, list[dict]] = defaultdict(list)
    for r in all_rows:
        by_fin[r["finisher"]].append(r)

    print("\nCounts per finisher:")
    for f in FINISHERS:
        print(f"  {f:<10} {len(by_fin[f]):>6}")

    # Balanced sample, deterministic.
    rng = random.Random(0)
    sample: list[dict] = []
    for f in FINISHERS:
        pool = list(by_fin[f])
        rng.shuffle(pool)
        sample.extend(pool[:SAMPLE_PER_FINISHER])

    # Persist both the full list and the sample.
    fields = ["file", "line", "kind", "name", "finisher", "n_tactics", "last_tactic"]
    for out_name, rows in [
        ("candidates_all.csv", all_rows),
        ("candidates.csv", sample),
    ]:
        out = REPO / "data" / out_name
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)
        print(f"Wrote {len(rows):>5} rows -> {out}")

    print("\nSample preview:")
    print(f"{'finisher':<10} {'kind':<8} {'n':>2}  {'name':<40} {'file':<40}")
    for r in sample:
        print(f"{r['finisher']:<10} {r['kind']:<8} {r['n_tactics']:>2}  {r['name'][:40]:<40} {r['file'][-40:]}")


if __name__ == "__main__":
    main()
