/**
 * DDT edge case and error scenarios.
 */
import type { EdgeCaseScenario } from '../types/fixtures.ts'

export const EDGE_CASE_SCENARIOS = [
  {
    scenario: 'error_503',
    description: '503 from /api/session/start shows error message in setup view',
    setup: 'error_503',
    assertions: {
      errorVisible: true,
      appLoads: true,
    },
  },
  {
    scenario: 'error_500',
    description: '500 from /api/session/start shows error message in setup view',
    setup: 'error_500',
    assertions: {
      errorVisible: true,
      appLoads: true,
    },
  },
  {
    scenario: 'corrupt_localStorage',
    description: 'Corrupt localStorage does not crash the app',
    setup: 'corrupt_localStorage',
    assertions: {
      appLoads: true,
    },
  },
  {
    scenario: 'katex_fallback',
    description: 'Invalid LaTeX renders as fallback plain text, not a crash',
    setup: 'katex_fallback',
    assertions: {
      appLoads: true,
      fallbackText: 'INVALID_LATEX',
    },
  },
] as const satisfies readonly EdgeCaseScenario[]
