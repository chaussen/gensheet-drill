import { useState, useRef, useCallback } from 'react'
import * as api from '../api/client.js'
import { useProgress } from './useProgress.js'

const initialState = {
  sessionId:     null,
  questions:     [],
  config:        null,
  answers:       new Map(),   // question_id -> { selectedIndex | selectedIndices }
  questionIndex: 0,
  result:        null,
  loading:       false,
  error:         null,
  errorCode:     null,
}

export function useSession() {
  const [state, setState] = useState(initialState)
  const [sessionStartTime, setSessionStartTime] = useState(null)
  const { saveSession } = useProgress()

  // Timing refs — mutations don't trigger re-renders
  const sessionStartRef  = useRef(null)
  const questionStartRef = useRef(null)
  const questionTimesRef = useRef({})

  // Derived
  const currentQuestion = state.questions[state.questionIndex] ?? null
  const totalQuestions  = state.questions.length
  const answeredCount   = state.answers.size

  // ── Timer helpers ─────────────────────────────────────────────────────────────

  const startSessionTimer = useCallback(() => {
    const now = Date.now()
    sessionStartRef.current  = now
    questionStartRef.current = now
    questionTimesRef.current = {}
    setSessionStartTime(now)
  }, [])

  function recordQuestionTime(question_id) {
    if (!questionStartRef.current) return
    const elapsed = Date.now() - questionStartRef.current
    questionTimesRef.current[question_id] =
      (questionTimesRef.current[question_id] || 0) + elapsed
    questionStartRef.current = Date.now()
  }

  function finaliseTimings() {
    // Record time for the question the student is currently viewing
    if (currentQuestion) {
      recordQuestionTime(currentQuestion.question_id)
    }
    return {
      total_time_ms:  sessionStartRef.current ? Date.now() - sessionStartRef.current : 0,
      question_times: { ...questionTimesRef.current },
    }
  }

  // ── Navigation ────────────────────────────────────────────────────────────────

  function goToQuestion(index) {
    if (index < 0 || index >= totalQuestions) return
    // Record time on the question we're leaving
    if (currentQuestion) {
      recordQuestionTime(currentQuestion.question_id)
    }
    // Reset timer for the question we're navigating to
    questionStartRef.current = Date.now()
    setState(s => ({ ...s, questionIndex: index }))
  }

  // ── Actions ───────────────────────────────────────────────────────────────────

  async function startSession(config, studentId) {
    setState(s => ({ ...s, loading: true, error: null }))
    try {
      const payload = studentId ? { ...config, student_id: studentId } : config
      const data = await api.startSession(payload)
      setState(s => ({
        ...s,
        sessionId:     data.session_id,
        questions:     data.questions,
        config,
        answers:       new Map(),
        questionIndex: 0,
        result:        null,
        loading:       false,
        error:         null,
      }))
    } catch (e) {
      setState(s => ({ ...s, loading: false, error: e.message, errorCode: e.status === 429 ? 'DAILY_LIMIT' : null }))
    }
  }

  function setAnswer(selectionOrArray, { advance = false } = {}) {
    const q = state.questions[state.questionIndex]
    if (!q) return

    // Record time on the current question before potentially advancing
    if (advance) recordQuestionTime(q.question_id)

    const isMulti = Array.isArray(selectionOrArray)
    setState(s => {
      const answers = new Map(s.answers)
      answers.set(q.question_id, {
        selectedIndex:   isMulti ? null : selectionOrArray,
        selectedIndices: isMulti ? selectionOrArray : null,
      })
      const nextIndex = advance && s.questionIndex < s.questions.length - 1
        ? s.questionIndex + 1
        : s.questionIndex
      return { ...s, answers, questionIndex: nextIndex }
    })

    // Reset question timer for the next question
    if (advance) questionStartRef.current = Date.now()
  }

  async function submitSession() {
    setState(s => ({ ...s, loading: true }))
    try {
      const timings = finaliseTimings()
      const responses = state.questions.map(q => {
        const ans = state.answers.get(q.question_id)
        const base = {
          question_id:   q.question_id,
          time_taken_ms: timings.question_times[q.question_id] ?? 0,
        }
        if (q.question_type === 'multi_select') {
          return { ...base, selected_indices: ans?.selectedIndices ?? [] }
        }
        return { ...base, selected_index: ans?.selectedIndex ?? 0 }
      })
      const result = await api.submitSession(state.sessionId, responses, timings.total_time_ms)
      saveSession(result, state.config)
      setState(s => ({ ...s, result, loading: false }))
    } catch (e) {
      setState(s => ({ ...s, loading: false, error: e.message }))
    }
  }

  function resetSession() {
    sessionStartRef.current  = null
    questionStartRef.current = null
    questionTimesRef.current = {}
    setSessionStartTime(null)
    setState({ ...initialState, answers: new Map() })
  }

  return {
    // state
    sessionId:       state.sessionId,
    questions:       state.questions,
    config:          state.config,
    currentQuestion,
    questionIndex:   state.questionIndex,
    totalQuestions,
    answers:         state.answers,
    answeredCount,
    result:          state.result,
    loading:         state.loading,
    error:           state.error,
    errorCode:       state.errorCode,
    sessionStartTime,
    // actions
    startSession,
    startSessionTimer,
    setAnswer,
    goToQuestion,
    submitSession,
    resetSession,
  }
}
