#!/usr/bin/env python3
"""Experiment A: finisher interchange matrix.

For each Q{n}.lean file:
  1. Load the file in a fresh REPL session (gives us env with Mathlib + defs).
  2. Reconstruct the theorem signature from the pre-unfold goal state in the trace.
  3. For each candidate finisher, send an `example` command that replays the
     original `unfold …` then applies the candidate. Record success/failure.

Output: data/matrix.csv with columns (file, finisher, ok, err_snippet).
"""

from __future__ import annotations

import csv
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
REPL_BIN = REPO.parent / "lean-repl" / ".lake" / "build" / "bin" / "repl"
TRACE_DIR = REPO / "data" / "traces"
OUT_CSV = REPO / "data" / "matrix.csv"

FINISHERS = ["rfl", "norm_num", "omega", "linarith"]

NAMESPACE_RE = re.compile(r"^\s*namespace\s+([A-Za-z_][A-Za-z0-9_']*)", re.M)
# Grab the raw signature text between `theorem <name>` and `:= by`.
# Pretty-printed goals aren't round-trip safe (they insert `↑` coercions), so we
# parse the source directly.
THEOREM_RE = re.compile(
    r"theorem\s+[A-Za-z_][A-Za-z0-9_']*(?P<sig>.*?):=\s*by",
    re.S,
)


def get_namespace(src_path: Path) -> str | None:
    m = NAMESPACE_RE.search(src_path.read_text())
    return m.group(1) if m else None


def get_theorem_signature(src_path: Path) -> str:
    m = THEOREM_RE.search(src_path.read_text())
    if not m:
        raise ValueError(f"No theorem in {src_path}")
    return m.group("sig").strip()


def repl_exchange(commands: list[dict]) -> list[dict]:
    """Send a list of JSON commands to a fresh REPL, blank-line separated, and
    parse the JSON objects returned on stdout."""
    payload = "\n\n".join(json.dumps(c) for c in commands) + "\n\n"
    proc = subprocess.run(
        ["lake", "env", str(REPL_BIN)],
        cwd=str(REPO),
        input=payload,
        capture_output=True,
        text=True,
        timeout=600,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"REPL failed: {proc.stderr[:400]}")
    # REPL emits one JSON object per command, separated by blank lines.
    chunks = re.split(r"\n\s*\n", proc.stdout.strip())
    return [json.loads(c) for c in chunks if c.strip()]


def response_ok(resp: dict) -> tuple[bool, str]:
    """A probe succeeded iff there are no error messages and no sorries."""
    if resp.get("sorries"):
        return False, "sorries remain"
    for msg in resp.get("messages", []):
        if msg.get("severity") == "error":
            data = msg.get("data", "")
            return False, data.replace("\n", " ")[:180]
    return True, ""


def probe_file(qfile: Path) -> list[dict]:
    trace = json.loads((TRACE_DIR / f"{qfile.stem}.json").read_text())
    tactics = trace.get("tactics", [])
    if len(tactics) < 2:
        print(f"  [skip {qfile.stem}: needs ≥2 tactics, has {len(tactics)}]")
        return []

    unfold_cmd = tactics[0]["tactic"]
    sig = get_theorem_signature(qfile)
    ns = get_namespace(qfile)

    # First command: load the file to establish env with Mathlib + the file's defs.
    load_cmd = {"path": f"Lean4/{qfile.name}"}
    probes = []
    for fin in FINISHERS:
        body = f"example {sig} := by\n  {unfold_cmd}\n  {fin}"
        if ns:
            body = f"namespace {ns}\n{body}\nend {ns}"
        probes.append({"cmd": body, "env": 0})

    responses = repl_exchange([load_cmd, *probes])
    # responses[0] is the load response; responses[1:] are the probe responses.
    results = []
    for fin, resp in zip(FINISHERS, responses[1:]):
        ok, err = response_ok(resp)
        results.append({"file": qfile.stem, "finisher": fin, "ok": ok, "err": err})
        mark = "✓" if ok else "✗"
        print(f"  {mark} {fin:<10} {err[:80]}")
    return results


def main():
    rows: list[dict] = []
    for qfile in sorted(
        (REPO / "Lean4").glob("Q*.lean"),
        key=lambda p: int(re.sub(r"\D", "", p.stem) or 0),
    ):
        print(f"[{qfile.stem}]")
        try:
            rows.extend(probe_file(qfile))
        except Exception as e:  # noqa: BLE001
            print(f"  ERROR: {e}")
            for fin in FINISHERS:
                rows.append({"file": qfile.stem, "finisher": fin, "ok": False, "err": f"driver error: {e}"})
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["file", "finisher", "ok", "err"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nWrote {len(rows)} rows to {OUT_CSV}")


if __name__ == "__main__":
    sys.exit(main())
