import Mathlib.Tactic

/-!
# Sandra's babysitting eggs

Sandra's neighbor gives her a basket of 9 eggs every time she babysits their daughter.
To make a Spanish flan, she needs 3 eggs. If Sandra has been tasked to make 15 Spanish
flans for her school fundraiser, how many times does Sandra have to babysit?

Answer: 5.
-/

namespace SandraFlans

def basket : ℕ := 9
def flanRecipe : ℕ := 3
def goal : ℕ := 15

def eggsNeeded : ℕ := goal * flanRecipe

def babysits (n : ℕ) : ℕ := n * basket

theorem sandra_babysits (n : ℕ) (h : babysits n ≥ eggsNeeded) : n ≥ 5 := by
  unfold babysits eggsNeeded basket flanRecipe goal at h
  omega

end SandraFlans

