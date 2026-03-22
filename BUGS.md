# GenSheet Drill — Bug Tracker

Bugs are logged here. Fixed bugs are kept for historical reference.

## BUG-001 — Simultaneous equations: invalid coefficients "1x", "0x", and "+-" sign in question text
**Found:** 2026-03-22
**Status:** Resolved
**Reproduce:**
  Question type: Year 9 Advanced Algebra — T-9A-04 (simultaneous equations)
  Actual: "y = 1x + -4  y = 0x + 3  What is the value of x?"
  Expected: "y = x - 4  y = 3  What is the value of x?"
**Root cause:** `question_template` uses `{a}x + {b}` placeholders. Python `.format()` substitutes literally — `a=1` → "1x", `a=0` → "0x", `b=-4` → "+ -4". The existing composite placeholder handler only covers `{ax}` style, not separated `{a}x`.
**Root cause class:** FORMAT_MISMATCH
**Fix applied:** Added `_clean_math_coefficients(text)` post-processing pass in `question_service.py` applied after every `_render_question_text` call. Handles: `1x`→`x`, `-1x`→`-x`, `0x + c`→`c`, `0x - c`→`-c`, `+ -N`→`- N`, `- -N`→`+ N`. Also benefits T-9A-03 context variants.
**Resolved:** 2026-03-22

## BUG-003 — Repeated "Select all quadratic equations" questions within a single session
**Found:** 2026-03-22
**Status:** Resolved
**Reproduce:**
  Session: Year 9 Advanced Algebra
  Actual: Seven questions in a row with identical question text "Select all quadratic equations."
  Expected: No question text should repeat within a session
**Root cause:** T-9A-05 in MULTI_SELECT_BANKS had 3 items all with the same question_text. `random.choices` (with replacement) at the template selection stage could allocate more slots than unique texts existed; the cycling fallback then repeated items, producing 7 identical-looking questions.
**Root cause class:** DISTRACTOR_FALLBACK (over-selection of a small curated bank)
**Fix applied:**
  1. `question_service.py` MULTI_SELECT_BANKS T-9A-05: gave each of the 3 items a distinct question_text ("Select all quadratic equations." / "Which of the following are quadratic equations?" / "Identify all quadratic equations from the list.")
  2. `question_service.py` generate_session_questions: added session-level deduplication by question_text as a safety net for all templates
**Resolved:** 2026-03-22

## BUG-002 — Verification crash: `_transversal_angle` does not handle "supplementary" relationship
**Found:** 2026-03-22
**Status:** Resolved
**Reproduce:**
  Running `python3 backend/services/verification.py` — test case T-7M-04 with `relationship: "supplementary"`
  Actual: `ValueError: Unknown transversal relationship: supplementary`
  Expected: returns 115 (= 180 - 65)
**Root cause:** `_transversal_angle` handled "corresponding", "alternate", "co-interior" but was missing the "supplementary" branch. Supplementary transversal angles sum to 180°, same formula as co-interior.
**Root cause class:** WRONG_VERIFIER_BRANCH
**Fix applied:** Added `elif "supplementary" in rel: return 180 - a` to `_transversal_angle` in `backend/services/verification.py`. Mirrors existing `_angle_relationship` which already handled this correctly for T-7M-04b.
**Resolved:** 2026-03-22
