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

export const startSession  = (cfg)           => request('POST', '/session/start', cfg)
export const submitSession = (id, responses) => request('POST', `/session/${id}/submit`, { responses })
export const getResult     = (id)            => request('GET',  `/session/${id}/result`)
