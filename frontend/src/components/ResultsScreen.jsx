import { useState } from 'react'

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

function Spinner() {
  return (
    <div className="flex items-center gap-3 text-slate-500 text-sm py-4">
      <div className="w-5 h-5 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin flex-shrink-0" />
      Generating personalised analysis…
    </div>
  )
}

export default function ResultsScreen({ result, analysisPolling, onNewSession, onViewHistory }) {
  const [expanded, setExpanded] = useState(null)
  const analysis = result.analysis

  return (
    <div className="min-h-screen bg-slate-50 py-8 px-4">
      <div className="max-w-2xl mx-auto space-y-6">

        {/* Score header */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 text-center">
          <p className="text-sm text-slate-500 mb-1">Your Score</p>
          <p className="text-5xl font-bold text-slate-800 mb-3">
            {result.score}<span className="text-2xl text-slate-400 font-normal"> / {result.total}</span>
          </p>
          <p className="text-xl text-slate-600 mb-3">{result.score_pct}%</p>
          {analysis && (
            <span className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${BAND_STYLES[analysis.performance_band] ?? 'bg-slate-100 text-slate-700'}`}>
              {BAND_LABELS[analysis.performance_band] ?? analysis.performance_band}
            </span>
          )}
        </div>

        {/* Analysis */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6">
          <h2 className="text-base font-semibold text-slate-800 mb-3">Personalised Analysis</h2>

          {analysisPolling && !analysis && <Spinner />}
          {!analysisPolling && !analysis && (
            <p className="text-sm text-slate-500">Analysis unavailable — try again later.</p>
          )}

          {analysis && (
            <div className="space-y-5">
              {analysis.motivational_note && (
                <p className="text-sm text-indigo-700 bg-indigo-50 rounded-lg px-4 py-3 border border-indigo-100">
                  {analysis.motivational_note}
                </p>
              )}

              {analysis.weak_areas?.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-slate-700 mb-2">Areas to Improve</h3>
                  <div className="space-y-3">
                    {analysis.weak_areas.map(area => (
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

              {analysis.next_session_recommendation && (
                <div className="border border-slate-200 rounded-xl p-4">
                  <h3 className="text-sm font-semibold text-slate-700 mb-1">Next Session</h3>
                  <p className="text-xs text-slate-500 mb-2">
                    Difficulty: <span className="font-medium text-slate-700 capitalize">{analysis.next_session_recommendation.difficulty}</span>
                  </p>
                  <p className="text-sm text-slate-700">{analysis.next_session_recommendation.rationale}</p>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Question breakdown */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6">
          <h2 className="text-base font-semibold text-slate-800 mb-3">Question Breakdown</h2>
          <div className="space-y-2">
            {result.responses.map((r, i) => (
              <div
                key={r.question_id}
                className={`border-l-4 rounded-r-lg px-4 py-3 cursor-pointer hover:bg-slate-50 transition-colors ${
                  r.correct ? 'border-green-500' : 'border-red-500'
                }`}
                onClick={() => setExpanded(expanded === r.question_id ? null : r.question_id)}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2 min-w-0">
                    <span className={`flex-shrink-0 text-base ${r.correct ? 'text-green-500' : 'text-red-500'}`}>
                      {r.correct ? '✓' : '✗'}
                    </span>
                    <p className="text-sm text-slate-700 truncate">{r.question_text}</p>
                  </div>
                  <span className="text-xs text-slate-400 flex-shrink-0">{expanded === r.question_id ? '▲' : '▼'}</span>
                </div>

                {expanded === r.question_id && (
                  <div className="mt-3 pt-3 border-t border-slate-100 space-y-2">
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div>
                        <span className="text-slate-500">Your answer: </span>
                        <span className={r.correct ? 'text-green-700 font-medium' : 'text-red-700 font-medium'}>
                          {r.options[r.selected_index]}
                        </span>
                      </div>
                      {!r.correct && (
                        <div>
                          <span className="text-slate-500">Correct: </span>
                          <span className="text-green-700 font-medium">{r.options[r.correct_index]}</span>
                        </div>
                      )}
                    </div>
                    <p className="text-xs text-slate-500 italic">{r.explanation}</p>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex gap-3">
          <button onClick={onNewSession}
            className="flex-1 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-2.5 rounded-xl transition-colors">
            Start New Session
          </button>
          <button onClick={onViewHistory}
            className="flex-1 bg-white hover:bg-slate-50 text-slate-700 font-semibold py-2.5 rounded-xl border border-slate-300 transition-colors">
            View History
          </button>
        </div>

      </div>
    </div>
  )
}
