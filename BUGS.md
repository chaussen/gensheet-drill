# GenSheet Drill — Bug Tracker

Bugs are logged here. Fixed bugs are kept for historical reference.

---

## BUG-001 — Y9 Number: duplicate questions within a session
**Found:** 2026-04-03
**Status:** Resolved
**Reproduce:**
  Start a 10-question Year 9 Number session (any difficulty).
  Actual: 3 out of 10 questions are word-for-word identical.
  Expected: all question texts are distinct.
**Root cause:** `generate_session_questions` deduplicates by `question_text` only for curated-bank templates. Y9 Number has 4 templates; `random.choices` picks the same parametric template multiple times, and the AI often returns identical params, producing identical question texts. Parametric templates were explicitly excluded from deduplication on the incorrect assumption that AI params are always varied.
**Root cause class:** PARAM_CONSTRAINT_VIOLATED
**Fix applied:** Removed the `curated_template_ids` restriction from the deduplication block in `generate_session_questions` — now ALL templates deduplicate by `question_text`. Updated the inline comment. (`backend/services/question_service.py`)
**Resolved:** 2026-04-03

---

## BUG-002 — Y9 Number (T-9N-02): scientific notation value displays as Python float repr; exponent not wrapped in LaTeX braces
**Found:** 2026-04-03
**Status:** Resolved
**Reproduce:**
  Start a Year 9 Number session. Observe T-9N-02 question and its MCQ options.
  Actual (question text): "Express 5.6e-05 in scientific notation." — value already looks like scientific notation (Python repr), confusing students.
  Actual (options): answers like "5.6 × 10^-5" render as "5.6 × 10^-5" in plain text instead of $5.6 \times 10^{-5}$.
  Expected (question text): "Express 0.000056 in scientific notation."
  Expected (options): properly typeset LaTeX with braced exponents.
**Root cause:** Two causes: (A) The `value` param is a Python float; `{value}` in the question template formats it with Python's default float repr (e.g. `5.6e-05`) instead of decimal notation. (B) `_to_latex_inner` converts `**N` → `^{N}` but never wraps bare `^N` patterns in braces, so the verifier's output `"5.6 × 10^-5"` becomes `$5.6 \times 10^-5$` in LaTeX — `^-` superscripts only the minus sign.
**Root cause class:** FORMAT_MISMATCH
**Fix applied:** (A) In `build_question`, for T-9N-02, convert the float `value` param to a decimal string via `Decimal` before question text rendering. (B) In `_to_latex_inner`, added `re.sub(r'\^(-?\d+)', r'^{\1}', s)` to wrap all bare `^N` / `^-N` in braces. (`backend/services/question_service.py`)
**Resolved:** 2026-04-03

---

## BUG-003 — Skipped questions shown as "wrong answer selected" in results
**Found:** 2026-04-03
**Status:** Resolved
**Reproduce:**
  Start a session, skip one or more questions (navigate past without selecting), then submit.
  Actual: skipped questions show a red ✗ border and "Your answer: Option A" in the breakdown (as if option A was selected).
  Expected: skipped questions show grey `—` border and a "skipped" badge; no "Your answer" row.
**Root cause:** `submitSession` in `useSession.js` builds responses with `ans?.selectedIndex ?? 0`. When a question is skipped, `ans` is undefined, so `selectedIndex` falls back to `0` — the first option is sent as the student's answer. The backend marks this as correct=false (unless option 0 happens to be correct). `isSkipped()` in `ResultsScreen` checks `r.selected_index == null`, which is false for index 0, so the question renders as wrong.
**Root cause class:** SCHEMA_DRIFT
**Fix applied:** In `useSession.js`, changed `?? 0` → `?? null` for single-select and `?? []` → `?? null` for multi-select skipped submissions. Updated `ResponseItem` validator in `schemas.py` to accept both `selected_index` and `selected_indices` being null (skipped). Added `test_submit_skipped_questions` test. (`frontend/src/hooks/useSession.js`, `backend/models/schemas.py`, `backend/tests/test_session_endpoints.py`)
**Resolved:** 2026-04-03

---

## BUG-004 — No way to return to question review after viewing progress history
**Found:** 2026-04-03
**Status:** Resolved
**Reproduce:**
  Complete a session → see ResultsScreen → click "View History" → AI generates progress report → click "← Back".
  Actual: "← Back" navigates to Session Setup, discarding the ResultsScreen with question breakdown.
  Expected: "← Back" returns to the most recent ResultsScreen so the student can review questions.
**Root cause:** ProgressView's `onBack` callback always calls `setBaseView('setup')`. The session result is still held in `useSession` state, but there is no navigation path back to 'results' from the progress view.
**Root cause class:** SCHEMA_DRIFT
**Fix applied:** In `App.jsx`, changed ProgressView's `onBack` to `() => setBaseView(session.result ? 'results' : 'setup')`. Since `session.result` is only cleared on `resetSession()` (which is called when starting a new session), the Back button returns to ResultsScreen when a recent result exists. (`frontend/src/App.jsx`)
**Resolved:** 2026-04-03

---

## BUG-005 — Probability question with p > 1 (e.g. "probability of winning is 7/6")
**Found:** 2026-04-07
**Status:** Resolved
**Reproduce:**
  Session: Year 8, Probability, Standard, 10 Questions
  Actual: A question appeared with probability value 7/6 (e.g. "The probability of winning a game is 7/6. What is the probability of NOT winning?"), yielding an answer of -1/6. Mathematically invalid — probabilities must be in [0, 1].
  Expected: All generated probability fractions should satisfy numerator < denominator.
**Root cause:** Templates T-7P-03 and T-8P-01 declare `p_constraint: "p_numerator < p_denominator"` in their params, but no code enforces this. The AI can return (or the fallback generator can produce) p_numerator ≥ p_denominator. For T-7P-03: p_numerator max=7, denominator choices include 4, 5, 6 — so 7/6, 7/5, 7/4 are all possible. For T-8P-01: p_numerator max=9, denominator choices include 2, 4, 5 — so 9/2, 9/4 etc. are all possible.
**Root cause class:** PARAM_CONSTRAINT_VIOLATED
**Fix applied:** Added `_PROBABILITY_PARAM_TEMPLATES` constant and `_probability_params_valid()` helper in question_service.py. In `_fallback_params`, raises max_attempts to 40 for probability templates and validates p_numerator < p_denominator in the fourth pass. In the main generation loop, added post-generation validation matching the existing algebra integer-constraint pattern (retry up to 3 times with fallback, skip slot on failure). (`backend/services/question_service.py`)
**Resolved:** 2026-04-07

---

## BUG-006 — Submit button does nothing after navigating back between questions
**Found:** 2026-04-07
**Status:** Resolved
**Reproduce:**
  Session: Year 8, Mixed, Standard, 5 Questions
  Steps: Answer all 5 questions (auto-advance brings you to Q5). Navigate back to Q1 via ← Previous or nav dots. Click the green Submit button.
  Actual: Clicking Submit appears to do nothing — no spinner, no results screen, no error message. The button remains green and clickable but the session is never submitted. Also, on the last question, a "Next" button was present that wrapped navigation to Q1 (unclear if intentional).
  Expected: Submit should work from any question once all questions are answered. An error should be displayed if submission fails.
**Root cause:** Two issues: (1) `submitSession()` in useSession.js catches errors and stores them in `session.error`, but DrillSession.jsx never renders `session.error`. Any backend failure (e.g. Render free tier restart clears the in-memory session cache, returning 404) silently resets loading to false, making it appear that clicking Submit did nothing. (2) `showSkipWarning` local state in DrillSession is never cleared when `allAnswered` transitions to true, so a stale warning can appear showing "0 unanswered questions." The "Next" button wrapping to Q1 is not present in the current code (already fixed in a prior commit).
**Root cause class:** SCHEMA_DRIFT (error field is in schema/state but never rendered)
**Fix applied:** Added error display in DrillSession.jsx showing `session.error` with a retry button when submission fails. Changed skip warning condition to `showSkipWarning && !allAnswered` so stale warning state is ignored once all questions are answered. Added `disabled={loading}` to the Submit button to prevent double-clicks during submission. (`frontend/src/components/DrillSession.jsx`)
**Resolved:** 2026-04-07
