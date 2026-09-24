-- A glass of milk is 8 ounces of milk. John drinks 2 glasses of milk.
-- If milk has 3 calories per ounce, how many calories did he consume?

import Mathlib.Tactic

namespace q6

def ouncesPerGlass : ℕ := 8
def glasses : ℕ := 2
def caloriesPerOunce : ℕ := 3
def totalCalories : ℕ := glasses * ouncesPerGlass + caloriesPerOunce

theorem calories : totalCalories = 19 := by
  unfold totalCalories glasses ouncesPerGlass caloriesPerOunce
  omega

end q6
