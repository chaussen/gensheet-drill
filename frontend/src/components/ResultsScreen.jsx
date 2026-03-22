import { useState } from 'react'
import { InlineMath } from 'react-katex'
import MathText from './MathText.jsx'
import { toLatex } from '../utils/math.js'
import { TEST_IDS } from '../testing/testIds.ts'

const BAND_STYLES = {
  needs_support: 'bg-red-100 text-red-800',
  developing:    'bg-amber-100 text-amber-800',
  strong:        'bg-green-100 text-green-800',
  exceeding:     'bg-indigo-100 text-indigo-800',
}
const BAND_LABELS = {
  needs_support: 'Needs Support',
  developing:    'Developing',
  strong:        'Strong',
  exceeding:     'Exceeding',
}

function renderOption(text, latex) {
  if (!latex) return text
  return <InlineMath math={toLatex(text)} renderError={() => text} />
}

function renderSelected(r) {
  if (r.question_type === 'multi_select') {
    const texts = (r.selected_indices || []).map(i => r.options[i])
    if (texts.length === 0) return '(none)'
    return texts.map((t, i) => (
      <span key={i}>{i > 0 && ', '}{renderOption(t, r.latex_notation)}</span>
    ))
  }
  return renderOption(r.options[r.selected_index], r.latex_notation)
}

function renderCorrect(r) {
  if (r.question_type === 'multi_select') {
    const texts = (r.correct_indices || []).map(i => r.options[i])
    return texts.map((t, i) => (
      <span key={i}>{i > 0 && ', '}{renderOption(t, r.latex_notation)}</span>
    ))
  }
  return renderOption(r.options[r.correct_index], r.latex_notation)
}

function formatMs(ms) {
  const totalSec = Math.floor(ms / 1000)
  const m = Math.floor(totalSec / 60)
  const s = totalSec % 60
  return m > 0 ? `${m}m ${s}s` : `${s}s`
}

function formatMsShort(ms) {
  const totalSec = Math.floor(ms / 1000)
  const m = Math.floor(totalSec / 60)
  const s = totalSec % 60
  return `${m}:${String(s).padStart(2, '0')}`
}

export default function ResultsScreen({ result, onNewSession, onViewHistory }) {
  const [expanded, setExpanded] = useState(null)
  const summary = result.summary

  return (
    <div className="min-h-screen bg-slate-50 py-8 px-4">
      <div className="max-w-2xl mx-auto space-y-6">

        {/* Score header */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 text-center">
          <p className="text-sm text-slate-500 mb-1">Your Score</p>
          <p data-testid={TEST_IDS.results.scoreDisplay} className="text-5xl font-bold text-slate-800 mb-3">
            {result.score}<span className="text-2xl text-slate-400 font-normal"> / {result.total}</span>
          </p>
          <p data-testid={TEST_IDS.results.scorePercent} className="text-xl text-slate-600 mb-3">{result.score_pct}%</p>
          {summary && (
            <span data-testid={TEST_IDS.results.performanceBand} className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${BAND_STYLES[summary.performance_band] ?? 'bg-slate-100 text-slate-700'}`}>
              {BAND_LABELS[summary.performance_band] ?? summary.performance_band}
            </span>
          )}
          {summary?.total_time_ms > 0 && (
            <div className="mt-4 text-sm text-slate-600">
              <p>
                <span className="font-medium">Time:</span>{' '}
                <span data-testid={TEST_IDS.results.totalTime}>{formatMs(summary.total_time_ms)}</span>
                {' total · '}
                <span data-testid={TEST_IDS.results.avgTime}>{formatMs(summary.avg_time_per_question_ms)}</span>
                {' avg per question'}
              </p>
              {summary.time_accuracy_summary && (
                <p className="mt-1 text-slate-500 italic">{summary.time_accuracy_summary}</p>
              )}
            </div>
          )}
        </div>

        {/* Session summary */}
        {summary && (
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6">
            <h2 className="text-base font-semibold text-slate-800 mb-3">Session Summary</h2>

            {/* Strand breakdown */}
            {Object.keys(summary.by_strand).length > 0 && (
              <div className="mb-4">
                <h3 className="text-sm font-semibold text-slate-700 mb-2">By Strand</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-xs text-slate-500 border-b border-slate-100">
                        <th className="text-left py-1.5 pr-4 font-medium">Strand</th>
                        <th className="text-right py-1.5 pr-4 font-medium">Questions</th>
                        <th className="text-right py-1.5 pr-4 font-medium">Correct</th>
                        <th className="text-right py-1.5 font-medium">Score</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(summary.by_strand).map(([strand, stat]) => (
                        <tr key={strand} className="border-b border-slate-50">
                          <td className="py-2 pr-4 text-slate-700 font-medium">
                            {strand}
                            {strand === summary.weakest_strand && (
                              <span className="ml-2 text-xs text-red-500">weakest</span>
                            )}
                            {strand === summary.strongest_strand && strand !== summary.weakest_strand && (
                              <span className="ml-2 text-xs text-green-600">strongest</span>
                            )}
                          </td>
                          <td className="py-2 pr-4 text-right text-slate-500">{stat.attempted}</td>
                          <td className="py-2 pr-4 text-right text-slate-500">{stat.correct}</td>
                          <td className={`py-2 text-right font-semibold ${
                            stat.score_pct >= 80 ? 'text-green-600' :
                            stat.score_pct >= 60 ? 'text-amber-600' : 'text-red-600'
                          }`}>
                            {stat.score_pct}%
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Next session suggestion */}
            {summary.next_session_suggestion && (
              <div className="border border-slate-200 rounded-xl p-4 bg-slate-50">
                <h3 className="text-sm font-semibold text-slate-700 mb-1">Next Session</h3>
                <p className="text-xs text-slate-500 mb-1">
                  <span className="font-medium text-slate-700">{summary.next_session_suggestion.strand}</span>
                  {' · '}
                  <span className="capitalize font-medium text-slate-700">{summary.next_session_suggestion.difficulty}</span>
                  {' difficulty'}
                </p>
                <p className="text-sm text-slate-700">{summary.next_session_suggestion.reason}</p>
              </div>
            )}
          </div>
        )}

        {/* Question breakdown */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6">
          <h2 className="text-base font-semibold text-slate-800 mb-3">Question Breakdown</h2>
          <div className="space-y-2">
            {result.responses.map((r) => {
              const isSlow = r.time_taken_ms != null && r.time_taken_ms > 90000
              return (
                <div
                  key={r.question_id}
                  data-testid={TEST_IDS.results.questionRow(r.question_id)}
                  className={`border-l-4 rounded-r-lg px-4 py-3 cursor-pointer transition-colors ${
                    r.correct ? 'border-green-500' : 'border-red-500'
                  } ${isSlow ? 'bg-amber-50 hover:bg-amber-100' : 'hover:bg-slate-50'}`}
                  onClick={() => setExpanded(expanded === r.question_id ? null : r.question_id)}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2 min-w-0">
                      <span className={`flex-shrink-0 text-base ${r.correct ? 'text-green-500' : 'text-red-500'}`}>
                        {r.correct ? '✓' : '✗'}
                      </span>
                      <MathText text={r.question_text} latex={!!r.latex_notation} className="text-sm text-slate-700 truncate" />
                    </div>
                    <div className="flex items-center gap-3 flex-shrink-0">
                      {r.time_taken_ms != null && (
                        <span className="text-xs text-slate-400 tabular-nums">{formatMsShort(r.time_taken_ms)}</span>
                      )}
                      <span className="text-xs text-slate-400">{expanded === r.question_id ? '▲' : '▼'}</span>
                    </div>
                  </div>

                  {expanded === r.question_id && (
                    <div className="mt-3 pt-3 border-t border-slate-100 space-y-2">
                      <div className="grid grid-cols-2 gap-2 text-xs">
                        <div>
                          <span className="text-slate-500">Your answer: </span>
                          <span data-testid={TEST_IDS.results.yourAnswer(r.question_id)} className={r.correct ? 'text-green-700 font-medium' : 'text-red-700 font-medium'}>
                            {renderSelected(r)}
                          </span>
                        </div>
                        {!r.correct && (
                          <div>
                            <span className="text-slate-500">Correct: </span>
                            <span data-testid={TEST_IDS.results.correctAnswer(r.question_id)} className="text-green-700 font-medium">{renderCorrect(r)}</span>
                          </div>
                        )}
                      </div>
                      <span data-testid={TEST_IDS.results.explanation(r.question_id)}>
                        <MathText text={r.explanation} latex={!!r.latex_notation} className="text-xs text-slate-500 italic" />
                      </span>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex gap-3">
          <button data-testid={TEST_IDS.results.newSessionBtn} onClick={onNewSession}
            className="flex-1 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-2.5 rounded-xl transition-colors">
            Start New Session
          </button>
          <button data-testid={TEST_IDS.results.historyBtn} onClick={onViewHistory}
            className="flex-1 bg-white hover:bg-slate-50 text-slate-700 font-semibold py-2.5 rounded-xl border border-slate-300 transition-colors">
            View History
          </button>
        </div>

      </div>
    </div>
  )
}
