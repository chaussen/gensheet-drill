import { useProgress } from '../hooks/useProgress.js'

const BAND_LABELS = {
  needs_support: 'Needs Support',
  developing:    'Developing',
  strong:        'Strong',
  exceeding:     'Exceeding',
}

export default function ProgressView({ onBack }) {
  const { progress, clearProgress } = useProgress()
  const sessions = progress?.sessions ? [...progress.sessions].reverse() : []

  return (
    <div className="min-h-screen bg-slate-50 py-8 px-4">
      <div className="max-w-2xl mx-auto space-y-6">

        <div className="flex items-center justify-between">
          <h1 className="text-xl font-bold text-slate-800">Progress History</h1>
          <button onClick={onBack}
            className="text-sm text-indigo-600 hover:text-indigo-800 transition-colors">
            ← Back
          </button>
        </div>

        {sessions.length === 0 ? (
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-8 text-center">
            <p className="text-slate-500">No sessions completed yet.</p>
            <p className="text-sm text-slate-400 mt-1">Start a drill session to see your history here.</p>
          </div>
        ) : (
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50">
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Date</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Year</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Strand</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Difficulty</th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Score</th>
                </tr>
              </thead>
              <tbody>
                {sessions.map((s, i) => (
                  <tr key={s.session_id} className={i % 2 === 0 ? '' : 'bg-slate-50'}>
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
          </div>
        )}

        {sessions.length > 0 && (
          <div className="text-center">
            <button onClick={clearProgress}
              className="text-xs text-slate-400 hover:text-red-500 transition-colors">
              Clear all history
            </button>
          </div>
        )}

      </div>
    </div>
  )
}
