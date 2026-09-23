#!/usr/bin/env bash
# Extract tactic-level traces for every Q*.lean file via lean-repl.
# Output: data/traces/Q{n}.json (one file per theorem file).
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
REPL="${REPL:-$REPO/../lean-repl/.lake/build/bin/repl}"
OUT_DIR="$REPO/data/traces"
mkdir -p "$OUT_DIR"

if [ ! -x "$REPL" ]; then
  echo "REPL binary not found or not executable: $REPL" >&2
  exit 1
fi

cd "$REPO"

for src in Lean4/Q*.lean; do
  base=$(basename "$src" .lean)
  out="$OUT_DIR/$base.json"
  printf 'extract %-14s -> %s ... ' "$src" "$out"
  # Use a here-string so stdin closes cleanly and REPL exits after one command.
  if lake env "$REPL" <<< "{\"path\": \"$src\", \"allTactics\": true}" > "$out" 2> "$out.err"; then
    echo "ok ($(wc -c < "$out") bytes)"
    rm -f "$out.err"
  else
    echo "FAIL (see $out.err)"
  fi
done
