import { useState, useEffect } from 'react'
import { useSession } from './hooks/useSession.js'
import SessionSetup from './components/SessionSetup.jsx'
import DrillSession from './components/DrillSession.jsx'
import ResultsScreen from './components/ResultsScreen.jsx'
import ProgressView from './components/ProgressView.jsx'

export default function App() {
  const [view, setView] = useState('setup')
  const session = useSession()

  // loading → drill once questions arrive
  useEffect(() => {
    if (view === 'loading' && session.questions.length > 0) {
      setView('drill')
    }
  }, [session.questions.length, view])

  // loading → setup on error
  useEffect(() => {
    if (view === 'loading' && session.error) {
      setView('setup')
    }
  }, [session.error, view])

  function handleStart(config) {
    setView('loading')
    session.startSession(config)
  }

  function handleReset() {
    session.resetSession()
    setView('setup')
  }

  if (view === 'setup') {
    return (
      <SessionSetup
        onStart={handleStart}
        onViewHistory={() => setView('progress')}
        loading={false}
        error={session.error}
      />
    )
  }

  if (view === 'loading') {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-10 h-10 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-slate-600">Generating your questions…</p>
        </div>
      </div>
    )
  }

  if (view === 'drill') {
    return (
      <DrillSession
        session={session}
        onSubmit={() => setView('results')}
      />
    )
  }

  if (view === 'results') {
    return (
      <ResultsScreen
        result={session.result}
        analysisPolling={session.analysisPolling}
        onNewSession={handleReset}
        onViewHistory={() => setView('progress')}
      />
    )
  }

  if (view === 'progress') {
    return (
      <ProgressView onBack={() => setView('setup')} />
    )
  }

  return null
}
