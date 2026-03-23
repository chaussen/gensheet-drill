# GenSheet Drill — Backlog

## 🔴 Bugs (fix immediately)
✅ All fixed:
1. Next button hidden on last question (spacer keeps layout stable)
2. Single-select auto-advances to next question (like before); stays put on revisit/change
3. Submit button always visible; warns about unanswered questions with confirm dialog
4. Set DEFAULT_TIER=dev in .env for unlimited sessions (9999/day, all question counts)

## Next Sprint
### ✅ DONE: Back/forward navigation within a drill session
Implemented: navigator strip with numbered dots, Prev/Next buttons,
Submit button appears when all answered, skipped questions flagged
in results. Answer change triggers brief opacity flash.

## Future Sprint
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



```

When you have a batch of items ready to action, give Claude Code:
```
Read BACKLOG.md. Pick all items marked "next sprint". 
Implement them one at a time in priority order. 
After each one, update BACKLOG.md to mark it done 
before starting the next.