/**
 * TypeScript mirrors of backend Pydantic models.
 * Keep in sync with backend/models/schemas.py.
 */

export type PerformanceBand = 'needs_support' | 'developing' | 'strong' | 'exceeding'
export type Difficulty = 'foundation' | 'standard' | 'advanced'
export type Strand = 'Number' | 'Algebra' | 'Measurement' | 'Space' | 'Statistics' | 'Probability' | 'Mixed'
export type QuestionType = 'single_select' | 'multi_select'
export type YearLevel = 7 | 8 | 9

export interface QuestionObjectPublic {
  readonly question_id: string
  readonly question_text: string
  readonly options: readonly string[]
  readonly question_type: QuestionType
  readonly latex_notation: boolean
  readonly vc_code: string
  readonly strand: string
  readonly difficulty: Difficulty
  readonly year_level: YearLevel
  readonly generated_at: string
}

export interface SessionConfig {
  readonly year_level: YearLevel
  readonly strand: Strand
  readonly difficulty: Difficulty
  readonly count: number
}

export interface SessionStartResponse {
  readonly session_id: string
  readonly questions: readonly QuestionObjectPublic[]
  readonly config: SessionConfig
}

export interface ResponseResultItem {
  readonly question_id: string
  readonly question_text: string
  readonly options: readonly string[]
  readonly question_type: QuestionType
  readonly latex_notation: boolean
  readonly vc_code: string
  readonly selected_index: number | null
  readonly selected_indices: readonly number[] | null
  readonly correct_index: number
  readonly correct_indices: readonly number[] | null
  readonly correct: boolean
  readonly explanation: string
  readonly time_taken_ms: number | null
}

export interface StrandStat {
  readonly attempted: number
  readonly correct: number
  readonly score_pct: number
}

export interface NextSessionSuggestion {
  readonly strand: Strand
  readonly difficulty: Difficulty
  readonly reason: string
}

export interface SessionSummary {
  readonly performance_band: PerformanceBand
  readonly total_time_ms: number
  readonly avg_time_per_question_ms: number
  readonly time_accuracy_summary: string | null
  readonly by_strand: Readonly<Record<string, StrandStat>>
  readonly weakest_strand: string | null
  readonly strongest_strand: string | null
  readonly next_session_suggestion: NextSessionSuggestion | null
}

export interface SessionResultResponse {
  readonly session_id: string
  readonly score: number
  readonly total: number
  readonly score_pct: number
  readonly responses: readonly ResponseResultItem[]
  readonly summary: SessionSummary | null
}

export interface HealthResponse {
  readonly status: 'ok'
  readonly ts: string
  readonly cache_size: number
}
