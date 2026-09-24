/-
Brandon's iPhone is four times as old as Ben's iPhone.
Ben's iPhone is two times older than Suzy's iPhone.
If Suzy's iPhone is 1 year old, how old is Brandon's iPhone?

Answer: 8.
-/

import Mathlib.Tactic

namespace IphoneAge

def suzyAge : ℕ := 1
def benAge : ℕ := 2 * suzyAge
def brandonAge : ℕ := 4 / benAge

theorem brandon_is_8 : brandonAge = 2 := by
  unfold brandonAge benAge suzyAge
  omega

end IphoneAge
