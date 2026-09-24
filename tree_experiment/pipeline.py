#!/usr/bin/env python3
"""Tree-based mutation experiment for the Q*.lean finisher study.

Each Q*.lean file is parsed into a JSON tree whose root is the finisher, whose
middle layer is the operator expressions inside each `def`, and whose leaves
are numeric literals or references to other defs.  For every operator node we
generate variants by swapping the operator, re-evaluate the whole def-graph in
Python to recompute the theorem's RHS, emit the mutated file, and check
whether each of the six finishers still closes the goal via the leanprover
REPL.

Scope: pure-Nat Q files (Q3, Q6, Q8, Q10) for the walking skeleton.  Q1/Q2
(hypotheses, Int), Q5/Q7 (Rat), and Q9 (division) can be layered in later by
extending the expression grammar and the theorem regex.
"""

from __future__ import annotations

import ast
import csv
import json
import os
import re
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
# Where lake env should be run. If we're in a worktree under .claude/worktrees,
# `lake env` there can't see Mathlib because the worktree has no build artifacts,
# so we fall back to the shared checkout that owns the .git directory.
def _shared_repo(worktree: Path) -> Path:
    parts = worktree.parts
    if ".claude" in parts:
        i = parts.index(".claude")
        # .../<shared>/.claude/worktrees/<name>
        if i >= 1 and parts[i + 1 : i + 3] == ("worktrees",) + (parts[i + 2],):
            return Path(*parts[:i])
    return worktree
LAKE_CWD = _shared_repo(REPO)
LEAN_DIR = REPO / "Lean4"
OUT_DIR = Path(__file__).resolve().parent
TREES_DIR = OUT_DIR / "trees"
VARIANTS_DIR = OUT_DIR / "variants"
RESULTS_CSV = OUT_DIR / "results" / "results.csv"

REPL_BIN = Path(
    os.environ.get(
        "REPL_BIN",
        str(REPO.parent.parent.parent.parent / "lean-repl" / ".lake" / "build" / "bin" / "repl"),
    )
)

FINISHERS = ["rfl", "decide", "norm_num", "omega", "linarith", "ring"]
MUTATION_OPS = ["+", "-", "*", "/"]

TARGET_FILES = ["Q3.lean", "Q6.lean", "Q8.lean", "Q10.lean"]


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

NAMESPACE_RE = re.compile(r"^namespace\s+(\S+)", re.MULTILINE)
DEF_RE = re.compile(
    r"^def\s+(?P<name>\w+)\s*:\s*(?P<type>[^:=]+?)\s*:=\s*(?P<body>.+?)\s*$",
    re.MULTILINE,
)
THEOREM_RE = re.compile(
    r"^theorem\s+(?P<name>\w+)\s*:\s*(?P<lhs>[^=]+?)\s*=\s*(?P<rhs>\S+)\s*:=\s*by",
    re.MULTILINE,
)


def py_to_tree(node: ast.AST) -> dict:
    if isinstance(node, ast.Constant) and isinstance(node.value, int):
        return {"kind": "lit", "value": node.value}
    if isinstance(node, ast.Name):
        return {"kind": "ref", "name": node.id}
    if isinstance(node, ast.BinOp):
        op_map = {ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Div: "/", ast.FloorDiv: "/"}
        op = op_map.get(type(node.op))
        if op is None:
            raise ValueError(f"unsupported binop: {ast.dump(node)}")
        return {
            "kind": "op",
            "op": op,
            "children": [py_to_tree(node.left), py_to_tree(node.right)],
        }
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        inner = py_to_tree(node.operand)
        if inner["kind"] == "lit":
            return {"kind": "lit", "value": -inner["value"]}
    raise ValueError(f"unsupported node: {ast.dump(node)}")


def parse_expr(src: str) -> dict:
    return py_to_tree(ast.parse(src.strip(), mode="eval").body)


def find_finisher_line(text: str, theorem_name: str) -> int | None:
    lines = text.splitlines()
    decl_re = re.compile(rf"^(?P<indent>\s*)theorem\s+{re.escape(theorem_name)}\b")
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


def parse_file(path: Path) -> dict:
    text = path.read_text()
    ns_match = NAMESPACE_RE.search(text)
    if not ns_match:
        raise ValueError(f"no namespace in {path}")
    namespace = ns_match.group(1)

    defs: list[dict] = []
    for m in DEF_RE.finditer(text):
        body_src = m.group("body").strip()
        defs.append(
            {
                "name": m.group("name"),
                "type": m.group("type").strip(),
                "body": parse_expr(body_src),
            }
        )

    thm_match = THEOREM_RE.search(text)
    if not thm_match:
        raise ValueError(f"no theorem in {path}")
    theorem = {
        "name": thm_match.group("name"),
        "lhs": thm_match.group("lhs").strip(),
        "rhs": int(thm_match.group("rhs")),
    }

    finisher_line = find_finisher_line(text, theorem["name"])
    if finisher_line is None:
        raise ValueError(f"no finisher line in {path}")
    finisher = text.splitlines()[finisher_line].strip()

    return {
        "file": path.name,
        "namespace": namespace,
        "finisher": finisher,
        "finisher_line": finisher_line,
        "defs": defs,
        "theorem": theorem,
    }


# ---------------------------------------------------------------------------
# Tree ops
# ---------------------------------------------------------------------------


def find_op_paths(node: dict, prefix: tuple = ()) -> list[tuple]:
    out: list[tuple] = []
    if node["kind"] == "op":
        out.append(prefix)
        for i, child in enumerate(node["children"]):
            out.extend(find_op_paths(child, prefix + (i,)))
    return out


def get_at(node: dict, path: tuple) -> dict:
    for i in path:
        node = node["children"][i]
    return node


def evaluate(node: dict, env: dict) -> int:
    if node["kind"] == "lit":
        return int(node["value"])
    if node["kind"] == "ref":
        return env[node["name"]]
    left = evaluate(node["children"][0], env)
    right = evaluate(node["children"][1], env)
    op = node["op"]
    if op == "+":
        return left + right
    if op == "-":
        return max(left - right, 0)
    if op == "*":
        return left * right
    if op == "/":
        if right == 0:
            raise ZeroDivisionError
        return left // right
    raise ValueError(f"unknown op {op!r}")


def evaluate_defs(defs: list[dict]) -> dict:
    env: dict = {}
    for d in defs:
        env[d["name"]] = evaluate(d["body"], env)
    return env


# ---------------------------------------------------------------------------
# Emitter
# ---------------------------------------------------------------------------

PRECEDENCE = {"+": 1, "-": 1, "*": 2, "/": 2}


def emit_expr(node: dict, parent_prec: int = 0) -> str:
    if node["kind"] == "lit":
        return str(node["value"])
    if node["kind"] == "ref":
        return node["name"]
    op = node["op"]
    prec = PRECEDENCE[op]
    left = emit_expr(node["children"][0], prec)
    right = emit_expr(node["children"][1], prec + 1)
    text = f"{left} {op} {right}"
    if prec < parent_prec:
        return f"({text})"
    return text


def emit_variant_lean(
    tree: dict,
    mutated_defs: list[dict],
    new_rhs: int,
    new_finisher: str,
    original_text: str,
) -> str:
    lines = original_text.splitlines()

    def_body_by_name = {d["name"]: emit_expr(d["body"]) for d in mutated_defs}
    for i, line in enumerate(lines):
        m = re.match(
            r"^(?P<lead>\s*def\s+(?P<name>\w+)\s*:\s*[^:=]+?:=\s*)(?P<body>.+?)(?P<tail>\s*)$",
            line,
        )
        if m and m.group("name") in def_body_by_name:
            lines[i] = m.group("lead") + def_body_by_name[m.group("name")] + m.group("tail")

    thm_name = tree["theorem"]["name"]
    thm_re = re.compile(
        rf"^(?P<lead>\s*theorem\s+{re.escape(thm_name)}\s*:\s*[^=]+?=\s*)(?P<rhs>\S+)(?P<tail>\s*:=\s*by\s*)$"
    )
    for i, line in enumerate(lines):
        m = thm_re.match(line)
        if m:
            lines[i] = m.group("lead") + str(new_rhs) + m.group("tail")
            break

    fin_idx = tree["finisher_line"]
    orig_fin = lines[fin_idx]
    indent = orig_fin[: len(orig_fin) - len(orig_fin.lstrip())]
    lines[fin_idx] = f"{indent}{new_finisher}"

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Mutation enumeration
# ---------------------------------------------------------------------------


def enumerate_mutations(tree: dict) -> list[dict]:
    out: list[dict] = []
    for def_idx, d in enumerate(tree["defs"]):
        for path in find_op_paths(d["body"]):
            original_op = get_at(d["body"], path)["op"]
            for new_op in MUTATION_OPS:
                if new_op == original_op:
                    continue
                out.append(
                    {
                        "def_idx": def_idx,
                        "def_name": d["name"],
                        "path": list(path),
                        "original_op": original_op,
                        "new_op": new_op,
                    }
                )
    return out


def apply_mutation(tree: dict, mutation: dict) -> tuple[list[dict], int | None]:
    new_defs = deepcopy(tree["defs"])
    body = new_defs[mutation["def_idx"]]["body"]
    get_at(body, tuple(mutation["path"]))["op"] = mutation["new_op"]
    try:
        env = evaluate_defs(new_defs)
    except ZeroDivisionError:
        return new_defs, None
    lhs = tree["theorem"]["lhs"]
    if lhs not in env:
        raise ValueError(f"theorem LHS {lhs!r} is not a def name; extend the parser")
    return new_defs, env[lhs]


# ---------------------------------------------------------------------------
# REPL verifier
# ---------------------------------------------------------------------------


def repl_batch(commands: list[dict], repo: Path, timeout_s: int = 1800) -> list[dict]:
    payload = "\n\n".join(json.dumps(c) for c in commands) + "\n\n"
    proc = subprocess.run(
        ["lake", "env", str(REPL_BIN)],
        cwd=str(repo),
        input=payload,
        capture_output=True,
        text=True,
        timeout=timeout_s,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"REPL failed: {proc.stderr[:400]}")
    chunks = re.split(r"\n\s*\n", proc.stdout.strip())
    return [json.loads(c) for c in chunks if c.strip()]


def error_lines(resp: dict) -> set:
    return {
        (m.get("pos") or {}).get("line")
        for m in resp.get("messages", [])
        if m.get("severity") == "error"
    }


def first_error_msg(resp: dict) -> str:
    for m in resp.get("messages", []):
        if m.get("severity") == "error":
            return (m.get("data", "") or "").replace("\n", " ")[:180]
    return ""


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def process_file(lean_path: Path) -> tuple[dict, list[dict]]:
    tree = parse_file(lean_path)
    original_text = lean_path.read_text()
    stem = lean_path.stem

    TREES_DIR.mkdir(parents=True, exist_ok=True)
    (TREES_DIR / f"{stem}.json").write_text(json.dumps(tree, indent=2, ensure_ascii=False))

    VARIANTS_DIR.mkdir(parents=True, exist_ok=True)
    variants: list[dict] = []
    for mut_idx, mutation in enumerate(enumerate_mutations(tree)):
        mutated_defs, new_rhs = apply_mutation(tree, mutation)
        if new_rhs is None:
            continue
        for finisher in FINISHERS:
            safe_orig = mutation["original_op"].replace("/", "div")
            safe_new = mutation["new_op"].replace("/", "div")
            variant_name = (
                f"{stem}__m{mut_idx:02d}__{mutation['def_name']}"
                f"__{safe_orig}to{safe_new}__{finisher}"
            )
            variant_path = VARIANTS_DIR / f"{variant_name}.lean"
            body = emit_variant_lean(
                tree, mutated_defs, new_rhs, finisher, original_text
            )
            variant_path.write_text(body)
            variants.append(
                {
                    "mutation_idx": mut_idx,
                    "def_name": mutation["def_name"],
                    "original_op": mutation["original_op"],
                    "new_op": mutation["new_op"],
                    "new_rhs": new_rhs,
                    "finisher": finisher,
                    "path": variant_path,
                }
            )

    # Chunk to avoid REPL OOM: each {"path": ...} command creates a fresh env
    # that holds Mathlib in memory; ~18 envs saturates RAM.
    CHUNK = 6
    responses: list[dict] = []
    for start in range(0, len(variants), CHUNK):
        chunk = variants[start : start + CHUNK]
        # Include baseline in every batch so the baseline error signature is
        # measured against the exact same REPL state as the variants.
        batch_cmds = [{"path": str(lean_path)}] + [{"path": str(v["path"])} for v in chunk]
        batch_resp = repl_batch(batch_cmds, LAKE_CWD)
        baseline_errs = error_lines(batch_resp[0])
        for v, resp in zip(chunk, batch_resp[1:]):
            variant_errs = error_lines(resp)
            new_errs = variant_errs - baseline_errs
            responses.append((v, resp, new_errs))

    rows: list[dict] = []
    for v, resp, new_errs in responses:
        rows.append(
            {
                "file": lean_path.name,
                "mutation_idx": v["mutation_idx"],
                "def_name": v["def_name"],
                "original_op": v["original_op"],
                "new_op": v["new_op"],
                "new_rhs": v["new_rhs"],
                "finisher": v["finisher"],
                "ok": not new_errs,
                "err": first_error_msg(resp) if new_errs else "",
            }
        )
    return tree, rows


def main(argv: list[str]) -> int:
    targets = argv[1:] or TARGET_FILES
    all_rows: list[dict] = []
    for name in targets:
        lean_path = LEAN_DIR / name
        if not lean_path.exists():
            print(f"skip: {name} not found", flush=True)
            continue
        print(f"processing {name} ...", flush=True)
        _tree, rows = process_file(lean_path)
        ok = sum(1 for r in rows if r["ok"])
        print(f"  {name}: {ok}/{len(rows)} variants closed", flush=True)
        all_rows.extend(rows)

    RESULTS_CSV.parent.mkdir(parents=True, exist_ok=True)
    with RESULTS_CSV.open("w", newline="") as fh:
        w = csv.DictWriter(
            fh,
            fieldnames=[
                "file",
                "mutation_idx",
                "def_name",
                "original_op",
                "new_op",
                "new_rhs",
                "finisher",
                "ok",
                "err",
            ],
        )
        w.writeheader()
        w.writerows(all_rows)
    print(f"\nWrote {len(all_rows)} rows -> {RESULTS_CSV}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
