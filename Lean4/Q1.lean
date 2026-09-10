import Mathlib.Tactic

/-!
# GSM8K problem 1190 — nurses' bandages

A nurses' station orders bandages in bulk packs of 50. On the first day, the
nurses used 38 bandages and ordered one bulk pack of bandages. On the second
day, they used ten fewer bandages. On the third day, they ordered two bulk
packs of bandages and only used half a pack. They had 78 bandages left at the
end of the third day. How many bandages did they start with on the first day?

Category (b) sequential state-change. GSM8K stated answer: 19.
-/

namespace Gsm8k1190

def afterDay1 (start : ℤ) : ℤ := start - 38 + 50
def afterDay2 (n : ℤ) : ℤ := n - 28
def afterDay3 (n : ℤ) : ℤ := n + 100 - 25

def simulate (s : ℤ) : ℤ := afterDay3 (afterDay2 (afterDay1 s))

theorem nurses_bandages (n : ℤ) (h : simulate n = 78) : n = 19 := by
  unfold simulate afterDay1 afterDay2 afterDay3 at h
  linarith

end Gsm8k1190
