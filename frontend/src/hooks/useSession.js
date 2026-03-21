import { useState, useEffect, useRef } from 'react'
import * as api from '../api/client.js'
import { useProgress } from './useProgress.js'

const POLL_INTERVAL_MS = 3000
const POLL_TIMEOUT_MS  = 30000

const initialState = {
  sessionId:        null,
  questions:        [],
  config:           null,
  answers:          new Map(),
  questionIndex:    0,
  questionStartedAt: null,
  result:           null,
  loading:          false,
  error:            null,
  analysisPolling:  false,
}

export function useSession() {
  const [state, setState] = useState(initialState)
  const { saveSession, updateAnalysis } = useProgress()
  const pollRef = useRef(null)

  // Derived
  const currentQuestion = state.questions[state.questionIndex] ?? null
  const totalQuestions  = state.questions.length

  // ── Polling: start when result arrives without analysis ──────────────────────
  useEffect(() => {
    if (!state.result || state.result.analysis !== null) return

    setState(s => ({ ...s, analysisPolling: true }))
    const deadline = Date.now() + POLL_TIMEOUT_MS

    pollRef.current = setInterval(async () => {
      if (Date.now() > deadline) {
        clearInterval(pollRef.current)
        setState(s => ({ ...s, analysisPolling: false }))
        return
      }
      try {
        const fresh = await api.getResult(state.sessionId)
        if (fresh.analysis !== null) {
          clearInterval(pollRef.current)
          setState(s => ({ ...s, result: fresh, analysisPolling: false }))
          updateAnalysis(state.sessionId, fresh.analysis)
        }
      } catch {
        // keep polling until deadline
      }
    }, POLL_INTERVAL_MS)

    return () => clearInterval(pollRef.current)
  }, [state.result?.session_id, state.result?.analysis])   // re-run only when result identity changes

  // ── Actions ──────────────────────────────────────────────────────────────────

  async function startSession(config) {
    setState(s => ({ ...s, loading: true, error: null }))
    try {
      const data = await api.startSession(config)
      setState(s => ({
        ...s,
        sessionId:         data.session_id,
        questions:         data.questions,
        config,
        answers:           new Map(),
        questionIndex:     0,
        questionStartedAt: Date.now(),
        result:            null,
        loading:           false,
        error:             null,
        analysisPolling:   false,
      }))
    } catch (e) {
      setState(s => ({ ...s, loading: false, error: e.message }))
    }
  }

  function answerQuestion(selectedIndex) {
    const q = state.questions[state.questionIndex]
    if (!q) return
    const timeTakenMs = state.questionStartedAt ? Date.now() - state.questionStartedAt : null

    setState(s => {
      const answers = new Map(s.answers)
      answers.set(q.question_id, { selectedIndex, timeTakenMs })
      return {
        ...s,
        answers,
        questionIndex:     s.questionIndex + 1,
        questionStartedAt: Date.now(),
      }
    })
  }

  async function submitSession() {
    setState(s => ({ ...s, loading: true }))
    try {
      const responses = state.questions.map(q => {
        const ans = state.answers.get(q.question_id)
        return {
          question_id:    q.question_id,
          selected_index: ans?.selectedIndex ?? 0,
          time_taken_ms:  ans?.timeTakenMs ?? null,
        }
      })
      const result = await api.submitSession(state.sessionId, responses)
      saveSession(result, state.config)
      setState(s => ({ ...s, result, loading: false }))
    } catch (e) {
      setState(s => ({ ...s, loading: false, error: e.message }))
    }
  }

  function resetSession() {
    clearInterval(pollRef.current)
    setState(initialState)
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
    analysisPolling: state.analysisPolling,
    // actions
    startSession,
    answerQuestion,
    submitSession,
    resetSession,
  }
}
