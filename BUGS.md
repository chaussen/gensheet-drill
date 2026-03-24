# GenSheet Drill — Bug Tracker
UX issues:
1. in multi-select questions, once the user hits the confirm selection button, the page does not auto navigate to the next question. this is inconsistent with single answer questions where click on the button goes to the next. 
2. question rendering issue:  "Solve simultaneously: y=x+6y=x+6 y = 4 What is the value of x?." on the UI, the `y=x+6` is rendered in kalex, but `y = 4` is still plain text. as a result, these two do not look consistent in style. also there is no limiter between them, so y = 4 looks like part of the equation. 
3. still non-standard algebra expression: question is `A line has gradient 1 and y-intercept 4. What is the equation of the line?`. one of the answers is `y = 1x + 4`, rendered in katex. maybe the format verification fails to apply to katex expressions
4. in summary page, even i got 100%, it says `weakest`: year 9 algebra, advanced. it says `Algebra  weakest   7   7   100%`

Logs:
i can see lots of logs from backend. e.g.
Could not derive y2 from rule 'y2 = y1 + vertical_leg×scale': name 'vertical_leg' is not defined
Verification failed for T-9A-04c (params={'pythagorean_triple': [3, 4, 5], 'scale': 2, 'x1': 0, 'y1': 3}): 'x2'
validate_question rejected assembled question for T-9A-01
Could not derive x2 from rule 'x2 = x1 + 2k where k ∈ [-4, 4]\{0}, ensuring midpoint x = x1+k is integer': invalid character '∈' (U+2208) (<rule>, line 1)
Could not derive y2 from rule 'y2 = y1 + 2j where j ∈ [-4, 4]\{0}, ensuring midpoint y = y1+j is integer': invalid character '∈' (U+

are these normal?