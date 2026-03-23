import { TEST_IDS } from '../testing/testIds.ts'

const STRANDS = ['Number', 'Algebra', 'Measurement', 'Space', 'Statistics', 'Probability', 'Mixed']
const DIFFICULTIES = [
  { value: 'foundation', label: 'Foundation' },
  { value: 'standard',   label: 'Standard'   },
  { value: 'advanced',   label: 'Advanced'   },
]

export default function SessionSetup({ onStart, onViewHistory, error, tierConfig }) {
  function handleSubmit(e) {
    e.preventDefault()
    const fd = new FormData(e.target)
    onStart({
      year_level: Number(fd.get('year_level')),
      strand:     fd.get('strand'),
      difficulty: fd.get('difficulty'),
      count:      Number(fd.get('count')),
    })
  }

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-8 w-full max-w-md">
        <h1 className="text-2xl font-bold text-slate-800 mb-1">GenSheet Drill</h1>
        <p className="text-slate-500 text-sm mb-6">Victorian Curriculum Mathematics — Years 7–9</p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Year Level</label>
            <select name="year_level" defaultValue="8" data-testid={TEST_IDS.setup.yearSelect}
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500">
              <option value="7">Year 7</option>
              <option value="8">Year 8</option>
              <option value="9">Year 9</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Strand</label>
            <select name="strand" defaultValue="Mixed" data-testid={TEST_IDS.setup.strandSelect}
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500">
              {STRANDS.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Difficulty</label>
            <select name="difficulty" defaultValue="standard" data-testid={TEST_IDS.setup.difficultySelect}
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500">
              {DIFFICULTIES.map(d => <option key={d.value} value={d.value}>{d.label}</option>)}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Questions</label>
            <select name="count" defaultValue={String(tierConfig?.question_count_options?.[1] ?? tierConfig?.question_count_options?.[0] ?? 10)} data-testid={TEST_IDS.setup.countSelect}
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500">
              {(tierConfig?.question_count_options ?? [5, 10]).map(n => (
                <option key={n} value={n}>{n} questions</option>
              ))}
            </select>
          </div>

          {error && (
            <div data-testid={TEST_IDS.setup.errorMessage} className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-3 py-2">
              {error}
            </div>
          )}

          <button type="submit" data-testid={TEST_IDS.setup.startBtn}
            className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-2.5 rounded-xl transition-colors">
            Start Session
          </button>
        </form>

        <button onClick={onViewHistory} data-testid={TEST_IDS.setup.historyBtn}
          className="mt-4 w-full text-sm text-indigo-600 hover:text-indigo-800 transition-colors py-1">
          View Progress History
        </button>
      </div>
    </div>
  )
}
