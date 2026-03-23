/**
 * Tier configuration — fetched from backend, cached in memory.
 * Fallback to free-tier defaults if the fetch fails.
 */

const FALLBACK_CONFIG = {
  tier: 'free',
  daily_session_limit: 3,
  max_question_count: 10,
  question_count_options: [5, 10],
}

let _cached = null

export async function fetchTierConfig() {
  if (_cached) return _cached
  try {
    const res = await fetch('/api/config/limits')
    if (!res.ok) throw new Error(res.statusText)
    _cached = await res.json()
    return _cached
  } catch {
    _cached = FALLBACK_CONFIG
    return _cached
  }
}

export function getCachedTierConfig() {
  return _cached ?? FALLBACK_CONFIG
}
