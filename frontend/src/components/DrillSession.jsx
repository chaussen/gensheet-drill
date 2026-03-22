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
    currentQuestion, questionIndex, totalQuestions, questions,
    config, loading, sessionStartTime,
    startSessionTimer, answerQuestion, submitSession,
  } = session

  // Keep a ref to the latest submitSession so the effect never has a stale closure
  const submitRef = useRef(submitSession)


  // Start timer when first question renders (once only)
  const timerStartedRef = useRef(false)
  useEffect(() => {
    if (questions.length > 0 && !timerStartedRef.current) {
      timerStartedRef.current = true
      startSessionTimer()
    }
  }, [questions.length, startSessionTimer])

  // Auto-submit when all questions answered
  useEffect(() => {
    if (totalQuestions > 0 && questionIndex >= totalQuestions) {
      submitRef.current()
    }
  }, [questionIndex, totalQuestions])

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

  const progressPct = (questionIndex / totalQuestions) * 100

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
        <div className="max-w-2xl mx-auto bg-slate-200 rounded-full h-2">
          <div
            data-testid={TEST_IDS.drill.progressBar}
            className="bg-indigo-500 rounded-full h-2 transition-all duration-300"
            style={{ width: `${progressPct}%` }}
          />
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
            onAnswer={answerQuestion}
          />
        </div>
      </div>
    </div>
  )
}
