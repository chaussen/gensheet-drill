import { useState, useRef, useCallback } from 'react'
import * as api from '../api/client.js'
import { useProgress } from './useProgress.js'

const initialState = {
  sessionId:     null,
  questions:     [],
  config:        null,
  answers:       new Map(),
  questionIndex: 0,
  result:        null,
  loading:       false,
  error:         null,
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
    return {
      total_time_ms:  sessionStartRef.current ? Date.now() - sessionStartRef.current : 0,
      question_times: { ...questionTimesRef.current },
    }
  }

  // ── Actions ───────────────────────────────────────────────────────────────────

  async function startSession(config) {
    setState(s => ({ ...s, loading: true, error: null }))
    try {
      const data = await api.startSession(config)
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
      setState(s => ({ ...s, loading: false, error: e.message }))
    }
  }

  function answerQuestion(selectionOrArray) {
    const q = state.questions[state.questionIndex]
    if (!q) return

    // Record time spent on this question before advancing
    recordQuestionTime(q.question_id)

    const isMulti = Array.isArray(selectionOrArray)
    setState(s => {
      const answers = new Map(s.answers)
      answers.set(q.question_id, {
        selectedIndex:   isMulti ? null : selectionOrArray,
        selectedIndices: isMulti ? selectionOrArray : null,
      })
      return {
        ...s,
        answers,
        questionIndex: s.questionIndex + 1,
      }
    })
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
    result:          state.result,
    loading:         state.loading,
    error:           state.error,
    sessionStartTime,
    // actions
    startSession,
    startSessionTimer,
    answerQuestion,
    submitSession,
    resetSession,
  }
}
