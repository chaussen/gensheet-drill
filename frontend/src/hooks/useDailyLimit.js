import { useMemo } from 'react'
import { STORAGE_KEY } from './useProgress.js'

function readSessions() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const record = JSON.parse(raw)
    return record?.sessions ?? []
  } catch {
    return []
  }
}

/**
 * Derive daily session usage from existing localStorage progress data.
 * Returns { sessionsToday, limitReached, remainingSessions, resetTime }.
 */
export function useDailyLimit(tierConfig, refreshKey) {
  return useMemo(() => {
    // Use UTC date — matches how useProgress stores session dates
    const today = new Date().toISOString().slice(0, 10)
    const sessions = readSessions()
    const sessionsToday = sessions.filter(s => s.date === today).length
    const limit = tierConfig?.daily_session_limit ?? 3
    const limitReached = sessionsToday >= limit

    // Next UTC midnight — consistent with how session dates are stored
    const now = new Date()
    const resetTime = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate() + 1))

    return {
      sessionsToday,
      limitReached,
      remainingSessions: Math.max(0, limit - sessionsToday),
      resetTime,
    }
  // refreshKey lets callers force a recompute after a session completes
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tierConfig, refreshKey])
}
