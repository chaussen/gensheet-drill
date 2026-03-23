/**
 * Single source of truth for all data-testid strings.
 * Imported by frontend components (to set attributes) and
 * by Playwright tests (to locate elements).
 *
 * Static IDs: plain string values via nested as-const object.
 * Dynamic IDs: pure functions — call-site infers the return type.
 */
export const TEST_IDS = {
  views: {
    setup:    'view-setup',
    loading:  'view-loading',
    drill:    'view-drill',
    results:  'view-results',
    progress: 'view-progress',
  },

  setup: {
    yearSelect:       'year-level-select',
    strandSelect:     'strand-select',
    difficultySelect: 'difficulty-select',
    countSelect:      'count-select',
    startBtn:         'start-session-btn',
    historyBtn:       'view-history-btn',
    errorMessage:     'setup-error-message',
  },

  drill: {
    questionCounter:   'question-counter',
    progressBar:       'progress-bar',
    timer:             'session-timer',
    multiWarning:      'multi-select-warning',
    confirmBtn:        'confirm-selection-btn',
    submittingSpinner: 'submitting-spinner',
    prevBtn:           'prev-question-btn',
    nextBtn:           'next-question-btn',
    submitBtn:         'submit-session-btn',
    navDot:      (i: number) => `nav-dot-${i}`,
    optionBtn:   (i: number) => `option-btn-${i}`,
    optionLabel: (i: number) => `option-label-${i}`,
  },

  results: {
    skippedBadge:    'skipped-badge',
    scoreDisplay:    'score-display',
    scorePercent:    'score-percent',
    performanceBand: 'performance-band',
    totalTime:       'total-time',
    avgTime:         'avg-time-per-question',
    newSessionBtn:   'new-session-btn',
    historyBtn:      'results-history-btn',
    questionRow:   (id: string) => `question-row-${id}`,
    yourAnswer:    (id: string) => `your-answer-${id}`,
    correctAnswer: (id: string) => `correct-answer-${id}`,
    explanation:   (id: string) => `explanation-${id}`,
  },

  limit: {
    container:  'limit-reached',
    message:    'limit-message',
    resetTime:  'limit-reset-time',
    unlockBtn:  'unlock-more-btn',
    historyBtn: 'limit-history-btn',
  },

  progress: {
    backBtn:           'back-btn',
    emptyState:        'progress-empty-state',
    generateReportBtn: 'generate-report-btn',
    reportOutput:      'progress-report',
    clearHistoryBtn:   'clear-history-btn',
    reportError:       'report-error',
    sessionRow:       (id: string) => `session-row-${id}`,
    sessionCheckbox:  (id: string) => `session-checkbox-${id}`,
  },
} as const
