const BASE = '/api'

async function request(method, path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  })
  const data = await res.json()
  if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`)
  return data
}

export const startSession    = (cfg)                       => request('POST', '/session/start', cfg)
export const submitSession   = (id, responses, total_time_ms = 0) => request('POST', `/session/${id}/submit`, { responses, total_time_ms })
export const getResult       = (id)                        => request('GET',  `/session/${id}/result`)
export const analyseProgress = (sessionIds, studentId)     => request('POST', '/progress/analyse', { session_ids: sessionIds, student_id: studentId })
