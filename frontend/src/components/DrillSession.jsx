import { useState, useEffect, useRef } from 'react'
import DrillQuestion from './DrillQuestion.jsx'
import { TEST_IDS } from '../testing/testIds.ts'

function SessionTimer({ startTime }) {
  const [elapsed, setElapsed] = useState(0)
  useEffect(() => {
    if (!startTime) return
    const interval = setInterval(() => setElapsed(Date.now() - startTime), 1000)
    return () => clearInterval(interval)
  }, [startTime])

  const minutes = Math.floor(elapsed / 60000)
  const seconds = Math.floor((elapsed % 60000) / 1000)
  return (
    <span data-testid={TEST_IDS.drill.timer} className="text-sm text-slate-500 tabular-nums">
      ⏱ {String(minutes).padStart(2, '0')}:{String(seconds).padStart(2, '0')}
    </span>
  )
}

export default function DrillSession({ session }) {
  const {
    currentQuestion, questionIndex, totalQuestions, questions, answers,
    config, loading, sessionStartTime, answeredCount, error,
    startSessionTimer, setAnswer, goToQuestion, submitSession,
  } = session

  // All hooks must be called before any early return
  const timerStartedRef = useRef(false)
  const [showSkipWarning, setShowSkipWarning] = useState(false)

  const allAnswered = answeredCount === totalQuestions

  useEffect(() => {
    if (questions.length > 0 && !timerStartedRef.current) {
      timerStartedRef.current = true
      startSessionTimer()
    }
  }, [questions.length, startSessionTimer])

  if (loading) {
    return (
      <div data-testid={TEST_IDS.drill.submittingSpinner} className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-10 h-10 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-slate-600">Submitting your answers…</p>
        </div>
      </div>
    )
  }

  if (!currentQuestion) return null

  const progressPct = (answeredCount / totalQuestions) * 100
  const isLastQuestion = questionIndex >= totalQuestions - 1
  const selectedAnswer = answers.get(currentQuestion.question_id) ?? null

  function handleSubmit() {
    if (!allAnswered) {
      setShowSkipWarning(true)
      return
    }
    submitSession()
  }

  function confirmSubmitWithSkips() {
    setShowSkipWarning(false)
    submitSession()
  }

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      {/* Header */}
      <div className="bg-white border-b border-slate-200 px-4 py-3">
        <div className="max-w-2xl mx-auto flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-slate-600">
            {config?.strand} · {config?.difficulty}
          </span>
          <div className="flex items-center gap-3">
            <span data-testid={TEST_IDS.drill.questionCounter} className="text-sm text-slate-500">
              {questionIndex + 1} / {totalQuestions}
            </span>
            <SessionTimer startTime={sessionStartTime} />
          </div>
        </div>
        {/* Progress bar */}
        <div className="max-w-2xl mx-auto bg-slate-200 rounded-full h-2 mb-3">
          <div
            data-testid={TEST_IDS.drill.progressBar}
            className="bg-indigo-500 rounded-full h-2 transition-all duration-300"
            style={{ width: `${progressPct}%` }}
          />
        </div>
        {/* Question navigator strip */}
        <div className="max-w-2xl mx-auto flex flex-wrap gap-1.5 justify-center">
          {questions.map((q, i) => {
            const isAnswered = answers.has(q.question_id)
            const isCurrent  = i === questionIndex
            return (
              <button
                key={q.question_id}
                data-testid={TEST_IDS.drill.navDot(i)}
                onClick={() => goToQuestion(i)}
                className={[
                  'w-7 h-7 rounded-full text-xs font-bold transition-all',
                  isCurrent
                    ? 'ring-2 ring-indigo-500 ring-offset-1'
                    : '',
                  isAnswered
                    ? 'bg-indigo-500 text-white'
                    : 'bg-slate-200 text-slate-500',
                ].join(' ')}
              >
                {i + 1}
              </button>
            )
          })}
        </div>
      </div>

      {/* Question */}
      <div className="flex-1 flex items-start justify-center p-4 pt-8">
        <div className="w-full max-w-2xl">
          <DrillQuestion
            key={currentQuestion.question_id}
            question={currentQuestion}
            questionNumber={questionIndex + 1}
            totalQuestions={totalQuestions}
            selectedAnswer={selectedAnswer}
            onSelect={setAnswer}
          />

          {/* Navigation buttons */}
          <div className="flex items-center justify-between mt-4 gap-3">
            <button
              data-testid={TEST_IDS.drill.prevBtn}
              onClick={() => goToQuestion(questionIndex - 1)}
              disabled={questionIndex === 0}
              className="px-4 py-2 rounded-xl text-sm font-medium border border-slate-300 text-slate-700 hover:bg-slate-50 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
            >
              ← Previous
            </button>

            <div className="flex flex-col items-center gap-1">
              <button
                data-testid={TEST_IDS.drill.submitBtn}
                onClick={handleSubmit}
                disabled={loading}
                className={`px-6 py-2 rounded-xl text-sm font-semibold transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${
                  allAnswered
                    ? 'bg-green-600 hover:bg-green-700 text-white'
                    : 'bg-slate-200 hover:bg-slate-300 text-slate-700'
                }`}
              >
                Submit{!allAnswered ? ` (${answeredCount}/${totalQuestions})` : ''}
              </button>
            </div>

            {!isLastQuestion ? (
              <button
                data-testid={TEST_IDS.drill.nextBtn}
                onClick={() => goToQuestion(questionIndex + 1)}
                className="px-4 py-2 rounded-xl text-sm font-medium border border-slate-300 text-slate-700 hover:bg-slate-50 transition-colors"
              >
                Next →
              </button>
            ) : (
              <div className="w-[85px]" />
            )}
          </div>

          {/* Warning when submitting with unanswered questions (hide once all are answered) */}
          {showSkipWarning && !allAnswered && (
            <div className="mt-3 bg-amber-50 border border-amber-200 rounded-xl p-4 text-center">
              <p className="text-sm text-amber-800 mb-2">
                You have {totalQuestions - answeredCount} unanswered question{totalQuestions - answeredCount > 1 ? 's' : ''}. Unanswered questions will be marked incorrect.
              </p>
              <div className="flex gap-2 justify-center">
                <button
                  onClick={confirmSubmitWithSkips}
                  className="px-4 py-1.5 rounded-lg text-sm font-medium bg-amber-600 hover:bg-amber-700 text-white transition-colors"
                >
                  Submit anyway
                </button>
                <button
                  onClick={() => setShowSkipWarning(false)}
                  className="px-4 py-1.5 rounded-lg text-sm font-medium border border-slate-300 text-slate-700 hover:bg-slate-50 transition-colors"
                >
                  Go back
                </button>
              </div>
            </div>
          )}

          {/* Submission error — shown if the API call fails after clicking Submit */}
          {error && (
            <div className="mt-3 bg-red-50 border border-red-200 rounded-xl p-4 text-center">
              <p className="text-sm text-red-800 mb-2">
                Could not submit your session. Please try again.
              </p>
              <button
                onClick={submitSession}
                className="px-4 py-1.5 rounded-lg text-sm font-medium bg-red-600 hover:bg-red-700 text-white transition-colors"
              >
                Retry
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
