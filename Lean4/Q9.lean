-- Charlie has three times as many Facebook friends as Dorothy.
-- James has four times as many friends on Facebook as Dorothy.
-- If Charlie has 12 friends on Facebook, how many Facebook friends does James have?

import Mathlib.Tactic

namespace q9

def charlieFriends : ℕ := 12
def dorothyFriends : ℕ := charlieFriends / 3
def jamesFriends : ℕ := 4 * dorothyFriends

theorem james : jamesFriends = 16 := by
  unfold jamesFriends dorothyFriends charlieFriends
  norm_num

end q9
