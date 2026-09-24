-- Josie grows grapes on her 10-acre farm. Each acre produces 5 tons of grapes
-- per year, and each ton of grapes makes 2 barrels of wine.
-- How many barrels of wine does her farm produce per year?

import Mathlib.Tactic

namespace q8

def acres : ℕ := 10
def tonsPerAcre : ℕ := 5
def barrelsPerTon : ℕ := 2
def barrelsPerYear : ℕ := acres / tonsPerAcre * barrelsPerTon

theorem barrels : barrelsPerYear = 4 := by
  unfold barrelsPerYear acres tonsPerAcre barrelsPerTon
  linarith

end q8
