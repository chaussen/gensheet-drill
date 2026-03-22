import { test, expect } from '@playwright/test'
import { DRILL_SCENARIOS } from '../fixtures/sessions.ts'
import { mockDrillSession } from '../support/mock-api.ts'
import { gotoSetup, startSession, answerSingleSelect } from '../support/actions.ts'
import { assertMathmlTags, assertNoKatex } from '../support/katex.ts'
import { TEST_IDS } from '../../../frontend/src/testing/testIds.ts'

const KATEX_SCENARIOS = DRILL_SCENARIOS.filter(s =>
  s.scenario === 'year7_sqrt_foundation' ||
  s.scenario === 'year7_fraction_standard' ||
  s.scenario === 'year8_prime_factorisation' ||
  s.scenario === 'year8_measurement_nolat'
)

for (const scenario of KATEX_SCENARIOS) {
  test(`KaTeX rendering — ${scenario.scenario}`, async ({ page }) => {
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

    if (scenario.assertions.katex_present) {
      // KaTeX should be rendered in the question card
      await expect(page.locator('.katex').first()).toBeVisible()

      if (scenario.assertions.mathml_tags.length > 0) {
        await assertMathmlTags(page, scenario.assertions.mathml_tags)
      }

      // Assert option-level KaTeX count if expected
      if (scenario.assertions.option_katex_count > 0) {
        const questionCard = page.locator(`[data-testid="${TEST_IDS.views.drill}"]`)
        await expect(questionCard.locator('.katex')).toHaveCount(scenario.assertions.option_katex_count)
      }
    } else {
      await assertNoKatex(page)
    }

    // Answer and go to results
    const firstAnswer = scenario.user_answers[0]
    await answerSingleSelect(page, firstAnswer)
    await page.waitForSelector(`[data-testid="${TEST_IDS.views.results}"]`)

    // KaTeX in results breakdown should also be consistent
    if (scenario.assertions.katex_present) {
      await expect(page.locator('.katex').first()).toBeVisible()
    } else {
      await assertNoKatex(page)
    }
  })
}
