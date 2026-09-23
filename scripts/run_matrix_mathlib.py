#!/usr/bin/env python3
"""Package 2: interchange matrix over Mathlib candidates.

Session-reuse strategy:
  For each candidate C in data/candidates.csv:
    1. Load C's source file via `path` -> env N (~9s).
    2. Send 4 probes as `cmd` in env N (~1s each).
       Each probe wraps `example <sig> := by <preamble>; <candidate finisher>`
       inside the theorem's original namespace chain, so unqualified references
       to same-file definitions resolve.

Signature and preamble are extracted verbatim from source (pretty-printed goal
states aren't round-trip safe due to `↑` coercions).
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
CANDIDATES_CSV = REPO / "data" / "candidates.csv"
OUT_CSV = REPO / "data" / "matrix_mathlib.csv"

FINISHERS = ["rfl", "decide", "norm_num", "omega", "linarith", "ring"]

NS_OPEN_RE = re.compile(r"^\s*namespace\s+([A-Za-z_][A-Za-z0-9_.']*)")
NS_CLOSE_RE = re.compile(r"^\s*end\s+([A-Za-z_][A-Za-z0-9_.']*)")


def extract_context(file_path: Path, theorem_name: str, kind: str) -> dict | None:
    text = file_path.read_text(errors="replace")
    lines = text.splitlines()
    # Locate the theorem/lemma declaration line.
    decl_re = re.compile(
        rf"^(?P<indent>\s*)(?P<kind>{kind})\s+{re.escape(theorem_name)}\b" 
    )
    theorem_idx = None
    for i, line in enumerate(lines):
        if decl_re.match(line):
            theorem_idx = i
            break
    if theorem_idx is None:
        return None

    # Walk back to build the namespace stack.
    ns_stack: list[str] = []
    for i in range(theorem_idx):
        m_open = NS_OPEN_RE.match(lines[i])
        if m_open:
            ns_stack.append(m_open.group(1))
            continue
        m_close = NS_CLOSE_RE.match(lines[i])
        if m_close and ns_stack and ns_stack[-1] == m_close.group(1):
            ns_stack.pop()

    # Find the end of the signature (`:= by` at end of line).
    base_indent = len(decl_re.match(lines[theorem_idx]).group("indent"))
    end_sig_idx = None
    for k in range(theorem_idx, min(theorem_idx + 20, len(lines))):
        if re.search(r":=\s*by\s*$", lines[k]):
            end_sig_idx = k
            break
    if end_sig_idx is None:
        return None

    # Signature text: everything after the theorem name up to `:= by`.
    joined = "\n".join(lines[theorem_idx : end_sig_idx + 1])
    body_start = decl_re.match(lines[theorem_idx]).end()
    # Offset body_start into `joined`: it's the same offset since line 0 of
    # `joined` is `lines[theorem_idx]`.
    sig_and_end = joined[body_start:]
    m_by = re.search(r":=\s*by\s*$", sig_and_end)
    signature = sig_and_end[: m_by.start()].strip()

    # Proof body: strictly-indented non-blank lines after `:= by`, until dedent.
    proof: list[str] = []
    j = end_sig_idx + 1
    while j < len(lines):
        line = lines[j]
        if line.strip() == "":
            j += 1
            continue
        cur = len(line) - len(line.lstrip())
        if cur <= base_indent:
            break
        proof.append(line)
        j += 1
    real = [p for p in proof if not p.strip().startswith("--")]
    if not real:
        return None

    return {
        "namespaces": ns_stack,
        "signature": signature,
        "preamble": real[:-1],
        "original_finisher_line": real[-1],
    }


def build_probe(ctx: dict, candidate_finisher: str, probe_id: int) -> str:
    ns_open = "\n".join(f"namespace {n}" for n in ctx["namespaces"])
    ns_close = "\n".join(f"end {n}" for n in reversed(ctx["namespaces"]))
    preamble_block = "\n".join(ctx["preamble"])
    sig = ctx["signature"]
    body = f"example {sig} := by\n{preamble_block}\n  {candidate_finisher}"
    parts = [f"namespace _probe_{probe_id}"]
    if ns_open:
        parts.append(ns_open)
    parts.append(body)
    if ns_close:
        parts.append(ns_close)
    parts.append(f"end _probe_{probe_id}")
    return "\n".join(parts)


def repl_batch(commands: list[dict]) -> list[dict]:
    payload = "\n\n".join(json.dumps(c) for c in commands) + "\n\n"
    proc = subprocess.run(
        ["lake", "env", str(REPL_BIN)],
        cwd=str(REPO),
        input=payload,
        capture_output=True,
        text=True,
        timeout=1800,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"REPL failed: {proc.stderr[:400]}")
    chunks = re.split(r"\n\s*\n", proc.stdout.strip())
    return [json.loads(c) for c in chunks if c.strip()]


def response_ok(resp: dict) -> tuple[bool, str]:
    if resp.get("sorries"):
        return False, "sorries remain"
    for msg in resp.get("messages", []):
        if msg.get("severity") == "error":
            data = msg.get("data", "")
            return False, data.replace("\n", " ")[:180]
    return True, ""


def run_candidate(candidate: dict, probe_id_start: int) -> tuple[list[dict], int]:
    src = REPO / candidate["file"]
    if not src.exists():
        return [
            {
                "name": candidate["name"],
                "file": candidate["file"],
                "orig_finisher": candidate["finisher"],
                "candidate_finisher": f,
                "ok": False,
                "err": f"source file missing: {src}",
            }
            for f in FINISHERS
        ], probe_id_start

    ctx = extract_context(src, candidate["name"], candidate["kind"])
    if ctx is None:
        return [
            {
                "name": candidate["name"],
                "file": candidate["file"],
                "orig_finisher": candidate["finisher"],
                "candidate_finisher": f,
                "ok": False,
                "err": "context extraction failed",
            }
            for f in FINISHERS
        ], probe_id_start

    commands = [{"path": candidate["file"]}]
    probe_ids = []
    for f in FINISHERS:
        pid = probe_id_start + len(probe_ids)
        probe_ids.append((f, pid))
        commands.append({"cmd": build_probe(ctx, f, pid), "env": 0})

    responses = repl_batch(commands)
    # responses[0] = file-load ack; responses[1:] = probe results
    load_resp = responses[0]
    load_errors = [m for m in load_resp.get("messages", []) if m.get("severity") == "error"]
    if load_errors:
        first = load_errors[0].get("data", "").replace("\n", " ")[:120]
        note = f"file-load failed ({len(load_errors)} errors): {first}"
        return [
            {
                "name": candidate["name"],
                "file": candidate["file"],
                "orig_finisher": candidate["finisher"],
                "candidate_finisher": f,
                "ok": False,
                "err": note,
            }
            for f in FINISHERS
        ], probe_id_start + len(FINISHERS)
    rows = []
    for (f, pid), resp in zip(probe_ids, responses[1:]):
        ok, err = response_ok(resp)
        rows.append(
            {
                "name": candidate["name"],
                "file": candidate["file"],
                "orig_finisher": candidate["finisher"],
                "candidate_finisher": f,
                "ok": ok,
                "err": err,
            }
        )
    return rows, probe_id_start + len(FINISHERS)


def main(argv: list[str]) -> None:
    limit = int(argv[1]) if len(argv) > 1 else None
    candidates = list(csv.DictReader(CANDIDATES_CSV.open()))
    if limit:
        candidates = candidates[:limit]
    print(f"Processing {len(candidates)} candidates...")

    all_rows: list[dict] = []
    pid = 0
    for c in candidates:
        print(f"[{c['finisher']:<10} {c['name'][:40]:<40}]")
        try:
            rows, pid = run_candidate(c, pid)
        except Exception as e:  # noqa: BLE001
            print(f"  ERROR: {e}")
            rows = [
                {
                    "name": c["name"],
                    "file": c["file"],
                    "orig_finisher": c["finisher"],
                    "candidate_finisher": f,
                    "ok": False,
                    "err": f"driver error: {e}",
                }
                for f in FINISHERS
            ]
        for r in rows:
            mark = "✓" if r["ok"] else "✗"
            print(f"  {mark} {r['candidate_finisher']:<10} {r['err'][:80]}")
        all_rows.extend(rows)

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="") as fh:
        w = csv.DictWriter(
            fh,
            fieldnames=["name", "file", "orig_finisher", "candidate_finisher", "ok", "err"],
        )
        w.writeheader()
        w.writerows(all_rows)
    print(f"\nWrote {len(all_rows)} rows -> {OUT_CSV}")


if __name__ == "__main__":
    main(sys.argv)
