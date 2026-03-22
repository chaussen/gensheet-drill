/**
 * DDT page flow scenarios — verifying navigation between views.
 */
import type { PageFlowScenario } from '../types/fixtures.ts'

export const PAGE_FLOW_SCENARIOS = [
  {
    scenario: 'full_session_then_history',
    description: 'Complete a session then navigate to progress view and back',
    config: { year_level: 8, strand: 'Algebra', difficulty: 'standard', count: 5 },
    user_answers: [0, 0, 0, 0, 0],
    expected_views: ['setup', 'drill', 'results', 'progress', 'setup'],
  },
  {
    scenario: 'new_session_from_results',
    description: 'Results → Start New Session → returns to setup',
    config: { year_level: 7, strand: 'Number', difficulty: 'foundation', count: 5 },
    user_answers: [0, 0, 0, 0, 0],
    expected_views: ['setup', 'drill', 'results', 'setup'],
  },
  {
    scenario: 'history_from_setup',
    description: 'Setup → View Progress History → Back → Setup',
    config: { year_level: 7, strand: 'Number', difficulty: 'foundation', count: 5 },
    user_answers: [],
    expected_views: ['setup', 'progress', 'setup'],
  },
] as const satisfies readonly PageFlowScenario[]
