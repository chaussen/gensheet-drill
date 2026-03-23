const BASE = '/api'

class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.status = status
  }
}

async function request(method, path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  })
  let data
  try {
    data = await res.json()
  } catch {
    if (!res.ok) throw new ApiError(`HTTP ${res.status}`, res.status)
    throw new ApiError('Invalid response from server', res.status)
  }
  if (!res.ok) throw new ApiError(data.detail || `HTTP ${res.status}`, res.status)
  return data
}

export const startSession    = (cfg)                       => request('POST', '/session/start', cfg)
export const submitSession   = (id, responses, total_time_ms = 0) => request('POST', `/session/${id}/submit`, { responses, total_time_ms })
export const getResult       = (id)                        => request('GET',  `/session/${id}/result`)
export const analyseProgress = (sessionIds, studentId)     => request('POST', '/progress/analyse', { session_ids: sessionIds, student_id: studentId })
export const fetchLimits     = ()                          => request('GET', '/config/limits')
