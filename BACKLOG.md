# GenSheet Drill — Backlog

## 🔴 Bugs (fix immediately)
Critical bug:

after i finish all questions and submit, the page turns blank. no summary, no analysis at all.
network tab shows that backend does return the response. e.g.

```
{"session_id":"c00391ca-ea0e-497b-9a64-fabdacf47596","score":1,"total":5,"score_pct":20,"responses":[{"question_id":"35496f91-3ad6-4570-9f39-a80cfc77e03a","question_text":"It is 9:00 PM in New York (EST). What time is it in Los Angeles (PST)?","options":["9:00 PM the same day","7:00 PM the same day","6:00 PM the same day","12:00 AM the next day"],"question_type":"single_select","selected_index":0,"correct_index":2,"selected_indices":null,"correct_indices":null,"correct":false,"explanation":"","vc_code":"VC2M8M04","latex_notation":false,"time_taken_ms":3202},{"question_id":"206e47fd-49b1-4bc6-81ab-c02c3b7c987e","question_text":"Select all irrational numbers from the list. (Select all that apply.)","options":["√9","π","√3","4/7","3.14"],"question_type":"multi_select","selected_index":null,"correct_index":null,"selected_indices":[],"correct_indices":[1,2],"correct":false,"explanation":"","vc_code":"VC2M8N01","latex_notation":true,"time_taken_ms":2789},{"question_id":"a96764d6-186c-4bb5-8764-7e46c2da42dd","question_text":"A bag has 3 red and 5 blue balls. One ball is drawn, then replaced, and another is drawn. What is the probability of drawing two red balls?","options":["9/63","9/66","9/64","9/65"],"question_type":"single_select","selected_index":0,"correct_index":2,"selected_indices":null,"correct_indices":null,"correct":false,"explanation":"The correct answer is 9/64. (Probability from two-step experiments using tree diagrams)","vc_code":"VC2M8P02","latex_notation":false,"time_taken_ms":1585},{"question_id":"037c7328-4895-4bc5-989e-5e8a1788b4d5","question_text":"What is the LCM (lowest common multiple) of 39 and 17?","options":["663","662","1326","664"],"question_type":"single_select","selected_index":0,"correct_index":0,"selected_indices":null,"correct_indices":null,"correct":true,"explanation":"The correct answer is 663. (Highest Common Factor and Lowest Common Multiple)","vc_code":"VC2M8N03","latex_notation":true,"time_taken_ms":1422},{"question_id":"b60c6f5e-5e14-4a32-8576-d519c44ee8ba","question_text":"A bag has 2 red and 3 blue balls. One ball is drawn, then replaced, and another is drawn. What is the probability of drawing two red balls?","options":["4/27","4/25","4/26","4/24"],"question_type":"single_select","selected_index":0,"correct_index":1,"selected_indices":null,"correct_indices":null,"correct":false,"explanation":"The correct answer is 4/25. (Probability from two-step experiments using tree diagrams)","vc_code":"VC2M8P02","latex_notation":false,"time_taken_ms":1849}],"summary":{"score":1,"total":5,"score_pct":20,"performance_band":"needs_support","by_strand":{"Measurement":{"attempted":1,"correct":0,"score_pct":0},"Number":{"attempted":2,"correct":1,"score_pct":50},"Probability":{"attempted":2,"correct":0,"score_pct":0}},"weakest_strand":"Probability","strongest_strand":"Number","next_session_suggestion":{"strand":"Probability","difficulty":"foundation","reason":"You got 0/2 on Probability. Try foundation difficulty next."},"total_time_ms":10853,"avg_time_per_question_ms":2170,"time_band":"fast","time_accuracy_summary":"Moving quickly but missing too many — slow down and check each step."},"analysis":null,"completed_at":"2026-03-22T11:46:41.000757+00:00"}
```

no console error


## ✅ Done
### ENHANCEMENT: Replace plain text maths with KaTeX rendering

**Scope:** All question_text and MCQ option strings that contain 
maths notation.

**Install:** npm install katex react-katex

**Notation standard:** Update question templates and verifiers to 
output LaTeX notation instead of plain text:
  x^2          → x^{2}         (renders as x²)
  2^2 × 5      → 2^{2} \times 5
  sqrt(16)     → \sqrt{16}
  3/4          → \frac{3}{4}
  -3x + 5      → -3x + 5       (no change needed)
  (x+1)(x-2)   → (x+1)(x-2)   (no change needed)

**Components to update:**
  DrillQuestion.jsx — wrap question_text and each option in <InlineMath>
  ResultsScreen.jsx — same for explanation text

**Backend:** Add a latex_notation flag to question_templates.json 
per template. Algebra and Number templates need it. 
Time zone and unit conversion templates do not.

**Risk:** Notation strings currently stored in localStorage 
(session history) are plain text. After this change, they render 
correctly in ProgressView automatically since the component handles 
the rendering, not the stored string.

## ⚪ Ideas (future consideration)
<!-- Brief descriptions, not yet specced -->
### ENHANCEMENT: Back/forward navigation within a drill session

**Current behaviour:** Linear — student answers Q1, moves to Q2, 
cannot return.

**Desired behaviour:**
  - Previous / Next buttons on DrillQuestion.jsx
  - Question navigator strip (dots or numbers) showing:
      answered (filled dot), skipped (empty dot), current (highlighted)
  - Student can revisit and change any answer before final submit
  - Submit button only appears when all questions have been answered 
    (or explicitly skipped)
  - Skipped questions flagged in results screen

**State change in useSession.js:**
  Current: responses array filled linearly
  New: responses array indexed by question position, 
       entries can be null (unanswered), updated on revisit

**No backend changes needed.** Submit payload is identical — 
array of {question_id, selected_index} — just built differently.

**UX detail:** If student changes an answer, clear the selection 
highlight briefly to confirm the change registered.

### ENHANCEMENT: Wider configurable question count range

**Current:** Fixed options 5, 10, 15
**Desired:** Slider or dropdown from 5 to 40 in steps of 5

**Changes:**
  SessionSetup.jsx — replace radio buttons with a slider (5–40, step 5)
  Show estimated time next to the slider: "~{count × 1} min"
  
  backend .env: 
    MIN_QUESTIONS_PER_SESSION=5    (unchanged)
    MAX_QUESTIONS_PER_SESSION=40   (increase from 20)
  
  Question cache: pre-warm with larger batches to support 40-question 
  sessions without mid-session AI calls. Cache batch size = 40 per 
  (year × strand × difficulty) combination.

**Note:** Mixed strand sessions at 40 questions require enough 
templates per year level to avoid repetition. 
Year 7: ~25 in-scope parametric templates — fine for 40 questions 
with parameter variation. Curated bank templates may repeat if bank 
size < session count for that template type. 
Mitigation: curated_bank templates capped at floor(bank_size / 2) 
appearances per session.

### ENHANCEMENT: Retry weak questions
After results screen, one-click "Retry wrong questions only" 
starts a new session pre-populated with only the questions 
answered incorrectly. No new AI call needed — reuse same 
question objects with reshuffled options.

### ENHANCEMENT: Print / export session results
Student or parent can export results as a simple PDF summary.
Use browser print CSS rather than a PDF library — simpler, 
no new dependency.

### BACKLOG: VC code reinstatement
When the platform is pitched to schools formally, VC codes need 
to be accurate and visible. At that point: audit all template 
vc_codes against VCAA JSONs, fix mismatches, display codes in 
teacher-facing views only (not student-facing).

### BACKLOG: Code-based session summary + on-demand AI progress report
See BACKLOG_code_based_summary.md — full spec already written.





```

When you have a batch of items ready to action, give Claude Code:
```
Read BACKLOG.md. Pick all items marked "next sprint". 
Implement them one at a time in priority order. 
After each one, update BACKLOG.md to mark it done 
before starting the next.