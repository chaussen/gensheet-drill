import { useState } from 'react'

export const STORAGE_KEY = 'gensheet_progress'

function readFromStorage() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

function writeToStorage(record) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(record))
  } catch {
    // quota exceeded — silently ignore
  }
}

function initRecord() {
  return {
    student_id: crypto.randomUUID(),
    created_at: new Date().toISOString(),
    sessions: [],
    aggregate: {
      total_questions_attempted: 0,
      total_correct: 0,
      by_vc_code: {},
      by_strand: {},
      last_updated: new Date().toISOString(),
    },
  }
}

export function useProgress() {
  const [progress, setProgress] = useState(() => readFromStorage())

  function saveSession(result, config) {
    const record = readFromStorage() ?? initRecord()

    const entry = {
      session_id:    result.session_id,
      date:          new Date().toISOString().slice(0, 10),
      year_level:    config.year_level,
      strand:        config.strand,
      difficulty:    config.difficulty,
      score:         result.score,
      total:         result.total,
      score_pct:     result.score_pct,
      summary:       result.summary ?? null,
      weak_vc_codes:            [],
      analysis_band:            result.summary?.performance_band ?? null,
      total_time_ms:            result.summary?.total_time_ms ?? 0,
      avg_time_per_question_ms: result.summary?.avg_time_per_question_ms ?? 0,
      time_band:                result.summary?.time_band ?? '',
    }
    record.sessions.push(entry)

    // Update aggregate
    record.aggregate.total_questions_attempted += result.total
    record.aggregate.total_correct += result.score

    const strand = config.strand
    if (!record.aggregate.by_strand[strand]) {
      record.aggregate.by_strand[strand] = { attempted: 0, correct: 0 }
    }
    record.aggregate.by_strand[strand].attempted += result.total
    record.aggregate.by_strand[strand].correct   += result.score

    for (const r of result.responses) {
      const vc = r.vc_code
      if (!record.aggregate.by_vc_code[vc]) {
        record.aggregate.by_vc_code[vc] = { attempted: 0, correct: 0 }
      }
      record.aggregate.by_vc_code[vc].attempted += 1
      if (r.correct) record.aggregate.by_vc_code[vc].correct += 1
    }

    record.aggregate.last_updated = new Date().toISOString()

    writeToStorage(record)
    setProgress({ ...record })
  }

  function updateAnalysis(sessionId, analysis) {
    const record = readFromStorage()
    if (!record) return
    const entry = record.sessions.find(s => s.session_id === sessionId)
    if (!entry) return
    entry.weak_vc_codes = (analysis.weak_areas ?? []).map(w => w.vc_code)
    entry.analysis_band = analysis.performance_band
    writeToStorage(record)
    setProgress({ ...record })
  }

  function clearProgress() {
    localStorage.removeItem(STORAGE_KEY)
    setProgress(null)
  }

  return { progress, saveSession, updateAnalysis, clearProgress }
}
