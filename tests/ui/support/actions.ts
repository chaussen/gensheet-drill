import type { Page } from '@playwright/test'
import { expect } from '@playwright/test'
import { TEST_IDS } from '../../../frontend/src/testing/testIds.ts'
import type { YearLevel, Strand, Difficulty, QuestionType } from '../types/api.ts'

export interface SessionConfig {
  readonly yearLevel: YearLevel
  readonly strand: Strand
  readonly difficulty: Difficulty
  readonly count: number
}

export async function gotoSetup(page: Page): Promise<void> {
  await page.evaluate(() => localStorage.clear())
  await page.goto('/')
  await page.waitForSelector(`[data-testid="${TEST_IDS.views.setup}"]`)
}

export async function startSession(page: Page, cfg: SessionConfig): Promise<void> {
  await page.selectOption(`[data-testid="${TEST_IDS.setup.yearSelect}"]`, String(cfg.yearLevel))
  await page.selectOption(`[data-testid="${TEST_IDS.setup.strandSelect}"]`, cfg.strand)
  await page.selectOption(`[data-testid="${TEST_IDS.setup.difficultySelect}"]`, cfg.difficulty)
  await page.selectOption(`[data-testid="${TEST_IDS.setup.countSelect}"]`, String(cfg.count))
  await page.click(`[data-testid="${TEST_IDS.setup.startBtn}"]`)
}

export async function answerSingleSelect(page: Page, optionIndex: number): Promise<void> {
  await page.click(`[data-testid="${TEST_IDS.drill.optionBtn(optionIndex)}"]`)
}

export async function answerMultiSelect(page: Page, indices: readonly number[]): Promise<void> {
  for (const i of indices) {
    await page.click(`[data-testid="${TEST_IDS.drill.optionLabel(i)}"]`)
  }
  await page.click(`[data-testid="${TEST_IDS.drill.confirmBtn}"]`)
}

export async function completeDrillSession(
  page: Page,
  userAnswers: readonly number[],
  questionType: QuestionType = 'single_select',
  multiAnswerGroups?: readonly (readonly number[])[],
): Promise<void> {
  await page.waitForSelector(`[data-testid="${TEST_IDS.views.drill}"]`)

  if (questionType === 'multi_select' && multiAnswerGroups != null) {
    for (const group of multiAnswerGroups) {
      await answerMultiSelect(page, group)
    }
  } else {
    for (const answer of userAnswers) {
      await expect(page.locator(`[data-testid="${TEST_IDS.drill.optionBtn(answer)}"]`)).toBeVisible()
      await answerSingleSelect(page, answer)
    }
  }

  await page.waitForSelector(`[data-testid="${TEST_IDS.views.results}"]`)
}
