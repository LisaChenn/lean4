-- A company bought $400000 worth of equipment from a retailer business,
-- but pieces of equipment worth 40% of the total number were faulty.
-- If they returned the faulty pieces of equipment to the seller,
-- calculate the total amount of money spent on functioning pieces of equipment.

import Mathlib.Tactic

namespace q7

def totalCost : ℚ := 400000
def faultyFraction : ℚ := 40 / 100
def functioningCost : ℚ := totalCost * (1 - faultyFraction)

theorem functioning : functioningCost = 240000 := by
  unfold functioningCost totalCost faultyFraction
  norm_num

end q7
