#!/usr/bin/env python3
"""Stage 4 of the pipeline: pruned Lean -> informal prose.

Reads a Lean file containing a pruned theorem and asks Claude to produce a
natural-language word problem that (a) asks the same mathematical question,
(b) reflects the pruned structure rather than the original narrative, and
(c) stays in the domain of the original problem when one is supplied.

Setup (one-time):
    pip install anthropic
    export ANTHROPIC_API_KEY=sk-ant-...

Usage:
    python scripts/restate.py pipeline/Q1_toy/Pruned.lean \
        --original Lean4/Q1.lean

Writes <pruned_dir>/restated.txt (override with --out) and echoes to stdout.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

DEFAULT_MODEL = "claude-sonnet-5"

# `/- … -/` and `/-! … -/` are both Lean block comments; the doc-comment form
# (with `!`) is the one Q*.lean files use for the problem statement.
DOCSTRING_RE = re.compile(r"/-!?(.*?)-/", re.S)
THEOREM_RE = re.compile(
    r"theorem\s+([A-Za-z_][A-Za-z0-9_']*)(.*?):=\s*by",
    re.S,
)

PROMPT_TEMPLATE = """You are helping translate a pruned Lean 4 theorem back into a natural-language math word problem.

The theorem below has been simplified (definitions inlined, arithmetic constant-folded, redundant structure removed). Write a short natural-language word problem that:
  1. Asks the same mathematical question the theorem asks.
  2. Reflects the STRUCTURE of the pruned theorem — do NOT re-introduce narrative steps that are no longer present in the hypotheses.
  3. Stays in the same domain / story as the original problem (bandages, ages, eggs, etc.), but uses only the facts the pruned form actually needs.
  4. Ends with a "how many …?" / "what is …?" style question whose answer is implied by the theorem's conclusion.
  5. Does NOT state the answer anywhere.

{original_block}Pruned Lean theorem:

```lean
{theorem_src}
```

Output ONLY the restated word problem — no preamble, no headers, no code fences, no explanation."""


def strip_block_comments(text: str) -> str:
    """Remove /-...-/ blocks so a stray `theorem` inside a docstring doesn't
    fool the theorem regex. Handles nesting."""
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


def extract_theorem_signature(text: str) -> str:
    m = THEOREM_RE.search(strip_block_comments(text))
    if not m:
        sys.exit("No `theorem NAME … := by` found in the pruned Lean file.")
    return f"theorem {m.group(1)}{m.group(2).rstrip()} := by"


def extract_docstring(text: str) -> str | None:
    m = DOCSTRING_RE.search(text)
    return m.group(1).strip() if m else None


def build_prompt(pruned_src: str, original_src: str | None) -> str:
    theorem_src = extract_theorem_signature(pruned_src)
    original_block = ""
    if original_src:
        doc = extract_docstring(original_src)
        if doc:
            original_block = (
                "Original informal problem (domain/style context — the restated "
                "version should be DIFFERENT, reflecting the pruned form):\n\n"
                f"{doc}\n\n"
            )
    return PROMPT_TEMPLATE.format(
        original_block=original_block,
        theorem_src=theorem_src,
    )


def call_claude(prompt: str, model: str) -> str:
    try:
        from anthropic import Anthropic
    except ImportError:
        sys.exit(
            "The `anthropic` package is not installed.\n"
            "Install it with:  pip install anthropic"
        )
    client = Anthropic()
    resp = client.messages.create(
        model=model,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(b.text for b in resp.content if hasattr(b, "text")).strip()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("pruned_lean", type=Path, help="Path to the pruned .lean file.")
    ap.add_argument(
        "--original", type=Path, default=None,
        help="Optional original .lean file whose docstring supplies domain context.",
    )
    ap.add_argument(
        "--out", type=Path, default=None,
        help="Output path (default: <pruned_lean>.parent/restated.txt).",
    )
    ap.add_argument("--model", default=DEFAULT_MODEL, help=f"Model id (default: {DEFAULT_MODEL})")
    ap.add_argument(
        "--print-prompt", action="store_true",
        help="Print the constructed prompt and exit without calling the API.",
    )
    args = ap.parse_args()

    pruned_src = args.pruned_lean.read_text()
    original_src = args.original.read_text() if args.original else None
    prompt = build_prompt(pruned_src, original_src)

    if args.print_prompt:
        print(prompt)
        return

    restated = call_claude(prompt, args.model)

    out = args.out or args.pruned_lean.parent / "restated.txt"
    out.write_text(restated + "\n")
    print(f"[restate.py] wrote {out}\n")
    print(restated)


if __name__ == "__main__":
    main()
