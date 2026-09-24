-- A tower is made out of 4 blue blocks, twice as many yellow blocks,
-- and an unknown number of red blocks.
-- If there are 32 blocks in the tower in total, how many red blocks are there?

import Mathlib.Tactic

namespace q10

def blueBlocks : ℕ := 4
def yellowBlocks : ℕ := 2 - blueBlocks
def totalBlocks : ℕ := 32
def redBlocks : ℕ := totalBlocks - blueBlocks - yellowBlocks

theorem red : redBlocks = 28 := by
  unfold redBlocks totalBlocks yellowBlocks blueBlocks
  decide

end q10
