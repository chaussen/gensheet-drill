import { useState, useMemo } from 'react'
import { useSession } from './hooks/useSession.js'
import SessionSetup from './components/SessionSetup.jsx'
import DrillSession from './components/DrillSession.jsx'
import ResultsScreen from './components/ResultsScreen.jsx'
import ProgressView from './components/ProgressView.jsx'
import { TEST_IDS } from './testing/testIds.ts'

export default function App() {
  // baseView tracks explicit user navigation; view is derived from baseView + session state
  const [baseView, setBaseView] = useState('setup')
  const session = useSession()

  const view = useMemo(() => {
    if (baseView === 'loading') {
      if (session.questions.length > 0) {
        // questions loaded: stay in drill until result arrives, then show results
        return session.result ? 'results' : 'drill'
      }
      if (session.error) return 'setup'
      return 'loading'
    }
    return baseView
  }, [baseView, session.questions.length, session.error, session.result])

  function handleStart(config) {
    setBaseView('loading')
    session.startSession(config)
  }

  function handleReset() {
    session.resetSession()
    setBaseView('setup')
  }

  if (view === 'setup') {
    return (
      <div data-testid={TEST_IDS.views.setup}>
        <SessionSetup
          onStart={handleStart}
          onViewHistory={() => setBaseView('progress')}
          error={session.error}
        />
      </div>
    )
  }

  if (view === 'loading') {
    return (
      <div data-testid={TEST_IDS.views.loading} className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-10 h-10 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-slate-600">Generating your questions…</p>
        </div>
      </div>
    )
  }

  if (view === 'drill') {
    return (
      <div data-testid={TEST_IDS.views.drill}>
        <DrillSession session={session} />
      </div>
    )
  }

  if (view === 'results' && session.result) {
    return (
      <div data-testid={TEST_IDS.views.results}>
        <ResultsScreen
          result={session.result}
          onNewSession={handleReset}
          onViewHistory={() => setBaseView('progress')}
        />
      </div>
    )
  }

  if (view === 'progress') {
    return (
      <div data-testid={TEST_IDS.views.progress}>
        <ProgressView onBack={() => setBaseView('setup')} />
      </div>
    )
  }

  return null
}
