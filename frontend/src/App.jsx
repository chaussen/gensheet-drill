import { useState, useMemo, useEffect } from "react";
import { useSession } from "./hooks/useSession.js";
import { useProgress } from "./hooks/useProgress.js";
import { useDailyLimit } from "./hooks/useDailyLimit.js";
import { fetchTierConfig } from "./config/tierConfig.js";
import SessionSetup from "./components/SessionSetup.jsx";
import DrillSession from "./components/DrillSession.jsx";
import ResultsScreen from "./components/ResultsScreen.jsx";
import ProgressView from "./components/ProgressView.jsx";
import LimitReached from "./components/LimitReached.jsx";
import Footer from "./components/Footer.jsx";
import { TEST_IDS } from "./testing/testIds.ts";

function Layout({ children }) {
  return (
    <div className="min-h-screen flex flex-col bg-slate-50">
      <main>{children}</main>
      <Footer />
    </div>
  );
}

export default function App() {
  // baseView tracks explicit user navigation; view is derived from baseView + session state
  const [baseView, setBaseView] = useState("setup");
  const [tierConfig, setTierConfig] = useState(null);
  const session = useSession();
  const { progress } = useProgress();

  // refreshKey increments after each session result so useDailyLimit recomputes
  const refreshKey = progress?.sessions?.length ?? 0;
  const dailyLimit = useDailyLimit(tierConfig, refreshKey);

  useEffect(() => {
    fetchTierConfig().then(setTierConfig);
  }, []);

  const studentId = progress?.student_id ?? null;

  const view = useMemo(() => {
    if (baseView === "loading") {
      if (session.questions.length > 0) {
        // questions loaded: stay in drill until result arrives, then show results
        return session.result ? "results" : "drill";
      }
      if (session.error) return "setup";
      return "loading";
    }
    return baseView;
  }, [baseView, session.questions.length, session.error, session.result]);

  function handleStart(config) {
    setBaseView("loading");
    session.startSession(config, studentId);
  }

  function handleReset() {
    session.resetSession();
    setBaseView("setup");
  }

  if (view === "setup") {
    // Show limit-reached screen if daily cap is hit or backend returned 429
    if (dailyLimit.limitReached || session.errorCode === "DAILY_LIMIT") {
      return (
        <Layout>
          <div data-testid={TEST_IDS.views.setup}>
            <LimitReached
              resetTime={dailyLimit.resetTime}
              sessionsToday={dailyLimit.sessionsToday}
              onViewHistory={() => setBaseView("progress")}
            />
          </div>
        </Layout>
      );
    }

    return (
      <Layout>
        <div data-testid={TEST_IDS.views.setup}>
          <SessionSetup
            onStart={handleStart}
            onViewHistory={() => setBaseView("progress")}
            error={session.error}
            tierConfig={tierConfig}
          />
        </div>
      </Layout>
    );
  }

  if (view === "loading") {
    return (
      <Layout>
        <div
          data-testid={TEST_IDS.views.loading}
          className="min-h-screen bg-slate-50 flex items-center justify-center"
        >
          <div className="text-center">
            <div className="w-10 h-10 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
            <p className="text-slate-600">Generating your questions…</p>
          </div>
        </div>
      </Layout>
    );
  }

  if (view === "drill") {
    return (
      <Layout>
        <div data-testid={TEST_IDS.views.drill}>
          <DrillSession session={session} />
        </div>
      </Layout>
    );
  }

  if (view === "results" && session.result) {
    return (
      <Layout>
        <div data-testid={TEST_IDS.views.results}>
          <ResultsScreen
            result={session.result}
            onNewSession={handleReset}
            onViewHistory={() => setBaseView("progress")}
          />
        </div>
      </Layout>
    );
  }

  if (view === "progress") {
    return (
      <Layout>
        <div data-testid={TEST_IDS.views.progress}>
          <ProgressView
            onBack={() => setBaseView(session.result ? "results" : "setup")}
          />
        </div>
      </Layout>
    );
  }

  return null;
}
