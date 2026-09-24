import Mathlib.Tactic.Use
-- We state: "There exists some number x such that 2 + 2 = x"
theorem solve_and_verify : ∃ x : Nat, 2 + 2 = x := by
  use ?_
