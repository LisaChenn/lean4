import Mathlib.Tactic

/-!
# Q1 pruned — one-step version of the nurses' bandages problem

Original: `Lean4/Q1.lean` had four defs (`afterDay1`, `afterDay2`, `afterDay3`,
`simulate`) and a two-step proof `unfold …; linarith`.

Pruning applied:
  1. Inlined every `def` into the theorem statement (no more `unfold`).
  2. Constant-folded the arithmetic: `- 38 + 50 - 28 + 100 - 25 = + 59`.

Result: the hypothesis is a single linear equation and the proof is one tactic.
Semantics preserved: this proves the same claim as `Gsm8k1190.nurses_bandages`.
-/

namespace Q1Pruned

theorem nurses_bandages (n : ℤ) (h : n + 59 = 78) : n = 19 := by
  linarith

end Q1Pruned
