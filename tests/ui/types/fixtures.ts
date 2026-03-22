/**
 * Types for test scenario shapes.
 * Derived from fixture constants — not defined independently.
 */
import type { SessionStartResponse, SessionResultResponse, PerformanceBand, YearLevel, Strand, Difficulty, QuestionType } from './api.ts'

export interface SessionScenario {
  readonly scenario: string
  readonly description: string
  readonly session_start_response: SessionStartResponse
  readonly user_answers: readonly number[]
  readonly session_result_response: SessionResultResponse
  readonly assertions: {
    readonly katex_present: boolean
    readonly mathml_tags: readonly string[]
    readonly option_katex_count: number
    readonly expected_score: number
    readonly expected_score_pct: number
    readonly expected_band: PerformanceBand
  }
}

export interface PageFlowConfig {
  readonly year_level: YearLevel
  readonly strand: Strand
  readonly difficulty: Difficulty
  readonly count: number
}

export type ViewName = 'setup' | 'drill' | 'results' | 'progress'

export interface PageFlowScenario {
  readonly scenario: string
  readonly description: string
  readonly config: PageFlowConfig
  readonly user_answers: readonly number[]
  readonly expected_views: readonly ViewName[]
}

export interface EdgeCaseScenario {
  readonly scenario: string
  readonly description: string
  readonly setup: 'error_503' | 'error_500' | 'corrupt_localStorage' | 'katex_fallback'
  readonly assertions: {
    readonly errorVisible?: boolean
    readonly appLoads?: boolean
    readonly fallbackText?: string
  }
}

export interface MultiSelectScenario extends SessionScenario {
  readonly question_type: QuestionType
  readonly multi_answer_indices: readonly number[]
}
