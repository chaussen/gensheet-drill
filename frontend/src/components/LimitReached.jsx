import { TEST_IDS } from '../testing/testIds.ts'

export default function LimitReached({ resetTime, sessionsToday, onViewHistory }) {
  const resetStr = resetTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', timeZoneName: 'short' })

  return (
    <div data-testid={TEST_IDS.limit.container}
      className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-8 w-full max-w-md text-center">
        <h1 className="text-2xl font-bold text-slate-800 mb-1">GenSheet Drill</h1>
        <p className="text-slate-500 text-sm mb-6">Victorian Curriculum Mathematics — Years 7–9</p>

        <div className="bg-amber-50 border border-amber-200 rounded-xl p-5 mb-6">
          <p data-testid={TEST_IDS.limit.message} className="text-amber-800 font-medium mb-2">
            You've completed your {sessionsToday} sessions for today!
          </p>
          <p data-testid={TEST_IDS.limit.resetTime} className="text-amber-700 text-sm">
            Sessions reset at midnight ({resetStr}).
          </p>
        </div>

        <button data-testid={TEST_IDS.limit.unlockBtn}
          onClick={() => { /* Subscription flow — coming soon */ }}
          className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-2.5 rounded-xl transition-colors mb-3">
          Unlock More Sessions
        </button>
        <p className="text-xs text-slate-400 mb-2">Coming soon</p>

        <button onClick={onViewHistory} data-testid={TEST_IDS.limit.historyBtn}
          className="w-full text-sm text-indigo-600 hover:text-indigo-800 transition-colors py-1">
          View Progress History
        </button>
      </div>
    </div>
  )
}
