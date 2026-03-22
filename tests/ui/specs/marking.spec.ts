import { test, expect } from '@playwright/test'
import { DRILL_SCENARIOS } from '../fixtures/sessions.ts'
import { mockDrillSession } from '../support/mock-api.ts'
import { gotoSetup, startSession, completeDrillSession } from '../support/actions.ts'
import { TEST_IDS } from '../../../frontend/src/testing/testIds.ts'

const SCORE_SCENARIOS = DRILL_SCENARIOS.filter(s =>
  s.scenario === 'all_correct_exceeding' ||
  s.scenario === 'all_wrong_needs_support' ||
  s.scenario === 'wrong_answer_shows_correct'
)

for (const scenario of SCORE_SCENARIOS) {
  test(`marking — ${scenario.scenario}`, async ({ page }) => {
    await mockDrillSession(page, scenario)
    await gotoSetup(page)

    const cfg = scenario.session_start_response.config
    await startSession(page, {
      yearLevel: cfg.year_level,
      strand: cfg.strand,
      difficulty: cfg.difficulty,
      count: cfg.count,
    })

    await completeDrillSession(page, scenario.user_answers)

    // Score display
    await expect(page.locator(`[data-testid="${TEST_IDS.results.scoreDisplay}"]`))
      .toContainText(String(scenario.assertions.expected_score))

    // Score percent
    await expect(page.locator(`[data-testid="${TEST_IDS.results.scorePercent}"]`))
      .toContainText(String(scenario.assertions.expected_score_pct))

    // Performance band
    const bandTexts = {
      needs_support: 'Needs Support',
      developing: 'Developing',
      strong: 'Strong',
      exceeding: 'Exceeding',
    } as const
    await expect(page.locator(`[data-testid="${TEST_IDS.results.performanceBand}"]`))
      .toContainText(bandTexts[scenario.assertions.expected_band])

    // Verify correct-answer testid visibility per response
    for (const r of scenario.session_result_response.responses) {
      // yourAnswer always present
      await expect(page.locator(`[data-testid="${TEST_IDS.results.yourAnswer(r.question_id)}"]`))
        .toBeHidden() // collapsed by default — expand first

      // Click the question row to expand
      await page.click(`[data-testid="${TEST_IDS.results.questionRow(r.question_id)}"]`)

      await expect(page.locator(`[data-testid="${TEST_IDS.results.yourAnswer(r.question_id)}"]`))
        .toBeVisible()

      if (r.correct) {
        // correctAnswer testid should NOT be present when answer is correct
        await expect(page.locator(`[data-testid="${TEST_IDS.results.correctAnswer(r.question_id)}"]`))
          .toHaveCount(0)
      } else {
        // correctAnswer testid MUST be present when answer is wrong
        await expect(page.locator(`[data-testid="${TEST_IDS.results.correctAnswer(r.question_id)}"]`))
          .toBeVisible()
      }

      // Explanation always present when expanded
      await expect(page.locator(`[data-testid="${TEST_IDS.results.explanation(r.question_id)}"]`))
        .toBeVisible()
    }
  })
}

test('multi-select question — confirm button required, warning visible', async ({ page }) => {
  const scenario = DRILL_SCENARIOS.find(s => s.scenario === 'multi_select_question')!
  await mockDrillSession(page, scenario)
  await gotoSetup(page)

  const cfg = scenario.session_start_response.config
  await startSession(page, {
    yearLevel: cfg.year_level,
    strand: cfg.strand,
    difficulty: cfg.difficulty,
    count: cfg.count,
  })

  await page.waitForSelector(`[data-testid="${TEST_IDS.views.drill}"]`)

  // Warning visible
  await expect(page.locator(`[data-testid="${TEST_IDS.drill.multiWarning}"]`)).toBeVisible()

  // Confirm button present but disabled with no selections
  await expect(page.locator(`[data-testid="${TEST_IDS.drill.confirmBtn}"]`)).toBeDisabled()

  // Select options and confirm
  await page.click(`[data-testid="${TEST_IDS.drill.optionLabel(0)}"]`)
  await page.click(`[data-testid="${TEST_IDS.drill.optionLabel(2)}"]`)

  await expect(page.locator(`[data-testid="${TEST_IDS.drill.confirmBtn}"]`)).toBeEnabled()
  await page.click(`[data-testid="${TEST_IDS.drill.confirmBtn}"]`)

  await page.waitForSelector(`[data-testid="${TEST_IDS.views.results}"]`)
  await expect(page.locator(`[data-testid="${TEST_IDS.results.scoreDisplay}"]`)).toContainText('1')
})
