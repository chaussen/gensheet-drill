import { useState } from 'react'
import { useProgress } from '../hooks/useProgress.js'
import { analyseProgress } from '../api/client.js'
import { TEST_IDS } from '../testing/testIds.ts'
import { BAND_LABELS } from '../constants/bands.js'

const STRAND_COLOURS = {
  Number:       '#6366f1',
  Algebra:      '#8b5cf6',
  Measurement:  '#0ea5e9',
  Space:        '#14b8a6',
  Statistics:   '#f59e0b',
  Probability:  '#ef4444',
  Mixed:        '#94a3b8',
}

function StrandBar({ strand, attempted, correct }) {
  const pct = attempted > 0 ? Math.round((correct / attempted) * 100) : 0
  const colour = STRAND_COLOURS[strand] ?? '#94a3b8'
  return (
    <div className="flex items-center gap-3">
      <span className="w-24 text-xs text-slate-600 text-right truncate">{strand}</span>
      <div className="flex-1 bg-slate-100 rounded-full h-4 relative">
        <div
          className="h-4 rounded-full transition-all duration-500"
          style={{ width: `${pct}%`, backgroundColor: colour }}
        />
        <span className="absolute inset-0 flex items-center justify-end pr-2 text-xs font-medium text-white mix-blend-difference">
          {pct}%
        </span>
      </div>
      <span className="text-xs text-slate-500 w-16 text-right">{correct}/{attempted}</span>
    </div>
  )
}

function WeakSpots({ byVcCode }) {
  if (!byVcCode || Object.keys(byVcCode).length === 0) return null

  const spots = Object.entries(byVcCode)
    .map(([vc, stats]) => ({
      vc_code: vc,
      pct: stats.attempted > 0 ? Math.round((stats.correct / stats.attempted) * 100) : 0,
      attempted: stats.attempted,
      correct: stats.correct,
    }))
    .filter(s => s.attempted >= 2)
    .sort((a, b) => a.pct - b.pct)
    .slice(0, 5)

  if (spots.length === 0) return null

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6">
      <h2 className="text-base font-semibold text-slate-800 mb-4">Your Weak Spots</h2>
      <p className="text-xs text-slate-500 mb-3">Topics with the lowest accuracy (min 2 attempts):</p>
      <div className="space-y-3">
        {spots.map(s => (
          <div key={s.vc_code} className="flex items-center justify-between">
            <span className="text-xs font-mono text-slate-500">{s.vc_code}</span>
            <div className="flex items-center gap-2">
              <div className="w-32 bg-slate-100 rounded-full h-2">
                <div
                  className="h-2 rounded-full"
                  style={{
                    width: `${s.pct}%`,
                    backgroundColor: s.pct < 40 ? '#ef4444' : s.pct < 70 ? '#f59e0b' : '#22c55e',
                  }}
                />
              </div>
              <span className={`text-xs font-medium w-10 text-right ${
                s.pct < 40 ? 'text-red-600' : s.pct < 70 ? 'text-amber-600' : 'text-green-600'
              }`}>
                {s.pct}%
              </span>
              <span className="text-xs text-slate-400">({s.correct}/{s.attempted})</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function ProgressReport({ report }) {
  return (
    <div className="bg-white rounded-2xl shadow-sm border border-indigo-200 p-6 space-y-4">
      <h2 className="text-base font-semibold text-indigo-800">Progress Report</h2>

      {report.motivational_note && (
        <p className="text-sm text-indigo-700 bg-indigo-50 rounded-lg px-4 py-3 border border-indigo-100">
          {report.motivational_note}
        </p>
      )}

      {report.weak_areas?.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-slate-700 mb-2">Areas to Improve</h3>
          <div className="space-y-3">
            {report.weak_areas.map(area => (
              <div key={area.vc_code} className="border border-slate-200 rounded-xl p-4">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-mono text-slate-500">{area.vc_code}</span>
                  <span className="text-xs font-medium text-red-600">{area.score_pct}%</span>
                </div>
                <p className="text-sm font-medium text-slate-800 mb-1">{area.description}</p>
                {area.error_pattern && (
                  <p className="text-xs text-amber-700 bg-amber-50 rounded px-2 py-1 mb-2">
                    Common mistake: {area.error_pattern}
                  </p>
                )}
                {area.tip && (
                  <p className="text-xs text-slate-600">{area.tip}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {report.next_session_recommendation && (
        <div className="border border-slate-200 rounded-xl p-4">
          <h3 className="text-sm font-semibold text-slate-700 mb-1">Recommended Next Session</h3>
          <p className="text-xs text-slate-500 mb-2">
            Difficulty: <span className="font-medium text-slate-700 capitalize">{report.next_session_recommendation.difficulty}</span>
          </p>
          <p className="text-sm text-slate-700">{report.next_session_recommendation.rationale}</p>
        </div>
      )}
    </div>
  )
}

export default function ProgressView({ onBack }) {
  const { progress, clearProgress } = useProgress()
  const [selected, setSelected] = useState(new Set())
  const [reportLoading, setReportLoading] = useState(false)
  const [report, setReport] = useState(null)
  const [reportError, setReportError] = useState(null)

  const sessions = progress?.sessions ? [...progress.sessions].reverse() : []
  const agg = progress?.aggregate ?? {}
  const byStrand = agg.by_strand ?? {}
  const strands = Object.entries(byStrand).filter(([, s]) => s.attempted > 0)

  const totalAttempted = agg.total_questions_attempted ?? 0
  const totalCorrect   = agg.total_correct ?? 0
  const overallPct     = totalAttempted > 0 ? Math.round((totalCorrect / totalAttempted) * 100) : null

  function toggleSession(sessionId) {
    setSelected(prev => {
      const next = new Set(prev)
      if (next.has(sessionId)) next.delete(sessionId)
      else next.add(sessionId)
      return next
    })
    setReport(null)
    setReportError(null)
  }

  async function handleGenerateReport() {
    if (selected.size < 2) return
    setReportLoading(true)
    setReport(null)
    setReportError(null)
    try {
      const studentId = progress?.student_id ?? 'unknown'
      const result = await analyseProgress([...selected], studentId)
      setReport(result)
    } catch {
      setReportError('Report unavailable — try again.')
    } finally {
      setReportLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 py-8 px-4">
      <div className="max-w-2xl mx-auto space-y-6">

        <div className="flex items-center justify-between">
          <h1 className="text-xl font-bold text-slate-800">Progress History</h1>
          <button data-testid={TEST_IDS.progress.backBtn} onClick={onBack}
            className="text-sm text-indigo-600 hover:text-indigo-800 transition-colors">
            ← Back
          </button>
        </div>

        {sessions.length === 0 ? (
          <div data-testid={TEST_IDS.progress.emptyState} className="bg-white rounded-2xl shadow-sm border border-slate-200 p-8 text-center">
            <p className="text-slate-500">No sessions completed yet.</p>
            <p className="text-sm text-slate-400 mt-1">Start a drill session to see your history here.</p>
          </div>
        ) : (
          <>
            {/* Overall summary */}
            <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-slate-500">Sessions completed</p>
                  <p className="text-2xl font-bold text-slate-800">{progress.sessions.length}</p>
                </div>
                <div className="text-right">
                  <p className="text-sm text-slate-500">Overall accuracy</p>
                  <p className="text-2xl font-bold text-slate-800">
                    {overallPct !== null ? `${overallPct}%` : '—'}
                  </p>
                  <p className="text-xs text-slate-400">{totalCorrect}/{totalAttempted} correct</p>
                </div>
              </div>
            </div>

            {/* Per-strand bar chart */}
            {strands.length > 0 && (
              <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6">
                <h2 className="text-base font-semibold text-slate-800 mb-4">Accuracy by Strand</h2>
                <div className="space-y-3">
                  {strands.map(([strand, stats]) => (
                    <StrandBar
                      key={strand}
                      strand={strand}
                      attempted={stats.attempted}
                      correct={stats.correct}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* Weak spots */}
            <WeakSpots byVcCode={agg.by_vc_code} />

            {/* Session history table */}
            <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
              <div className="flex items-center justify-between px-4 pt-4 pb-2">
                <h2 className="text-base font-semibold text-slate-800">Session History</h2>
                <p className="text-xs text-slate-400">
                  {selected.size === 0
                    ? 'Select sessions to generate a progress report'
                    : `${selected.size} selected`}
                </p>
              </div>
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50">
                    <th className="px-4 py-3 w-8" />
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Date</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Yr</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Strand</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Diff.</th>
                    <th className="text-right px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Score</th>
                  </tr>
                </thead>
                <tbody>
                  {sessions.map((s, i) => (
                    <tr
                      key={s.session_id}
                      data-testid={TEST_IDS.progress.sessionRow(s.session_id)}
                      className={`cursor-pointer transition-colors ${
                        selected.has(s.session_id)
                          ? 'bg-indigo-50'
                          : i % 2 === 0 ? '' : 'bg-slate-50'
                      }`}
                      onClick={() => toggleSession(s.session_id)}
                    >
                      <td className="px-4 py-3">
                        <input
                          type="checkbox"
                          data-testid={TEST_IDS.progress.sessionCheckbox(s.session_id)}
                          checked={selected.has(s.session_id)}
                          className="rounded border-slate-300 text-indigo-600"
                          onClick={e => e.stopPropagation()}
                          onChange={() => toggleSession(s.session_id)}
                        />
                      </td>
                      <td className="px-4 py-3 text-slate-600">{s.date}</td>
                      <td className="px-4 py-3 text-slate-600">{s.year_level}</td>
                      <td className="px-4 py-3 text-slate-700 font-medium">{s.strand}</td>
                      <td className="px-4 py-3 text-slate-600 capitalize">{s.difficulty}</td>
                      <td className="px-4 py-3 text-right">
                        <span className="font-medium text-slate-800">{s.score}/{s.total}</span>
                        <span className="text-slate-500 ml-1">({s.score_pct}%)</span>
                        {s.analysis_band && (
                          <span className="ml-2 text-xs text-slate-400">
                            {BAND_LABELS[s.analysis_band] ?? s.analysis_band}
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {/* Generate Report button */}
              <div className="px-4 py-4 border-t border-slate-100">
                <button
                  data-testid={TEST_IDS.progress.generateReportBtn}
                  onClick={handleGenerateReport}
                  disabled={selected.size < 2 || reportLoading}
                  className={`w-full py-2.5 rounded-xl font-semibold text-sm transition-colors ${
                    selected.size >= 2 && !reportLoading
                      ? 'bg-indigo-600 hover:bg-indigo-700 text-white'
                      : 'bg-slate-100 text-slate-400 cursor-not-allowed'
                  }`}
                >
                  {reportLoading
                    ? 'Generating report…'
                    : selected.size < 2
                      ? 'Select 2+ sessions to generate report'
                      : `Generate Progress Report (${selected.size} sessions)`}
                </button>
                {reportLoading && (
                  <div className="flex items-center justify-center gap-2 mt-3 text-xs text-slate-500">
                    <div className="w-4 h-4 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin" />
                    Analysing patterns across sessions…
                  </div>
                )}
                {reportError && (
                  <p data-testid={TEST_IDS.progress.reportError} className="mt-2 text-xs text-red-500 text-center">{reportError}</p>
                )}
              </div>
            </div>

            {/* Progress report output */}
            {report && (
              <div data-testid={TEST_IDS.progress.reportOutput}>
                <ProgressReport report={report} />
              </div>
            )}

            <div className="text-center">
              <button data-testid={TEST_IDS.progress.clearHistoryBtn} onClick={clearProgress}
                className="text-xs text-slate-400 hover:text-red-500 transition-colors">
                Clear all history
              </button>
            </div>
          </>
        )}

      </div>
    </div>
  )
}
