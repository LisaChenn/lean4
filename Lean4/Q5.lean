-- Benny saw a 10-foot shark with 2 6-inch remoras attached to it.
-- What percentage of the shark's body length is the combined length of the remoras?

import Mathlib.Tactic

namespace q5

def sharkLengthInches : ℕ := 10 * 12
def remoraLengthInches : ℕ := 6
def numRemoras : ℕ := 2
def combinedRemoraLength : ℕ := numRemoras * remoraLengthInches

theorem percentage :
    (combinedRemoraLength : ℚ) / sharkLengthInches * 100 = 10 := by
  unfold combinedRemoraLength numRemoras remoraLengthInches sharkLengthInches
  norm_num

end q5
