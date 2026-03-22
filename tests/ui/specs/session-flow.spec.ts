import { test, expect } from '@playwright/test'
import { DRILL_SCENARIOS } from '../fixtures/sessions.ts'
import { mockDrillSession } from '../support/mock-api.ts'
import { gotoSetup, startSession, completeDrillSession } from '../support/actions.ts'
import { TEST_IDS } from '../../../frontend/src/testing/testIds.ts'

// Use a simple single-select scenario for flow tests
const FLOW_SCENARIO = DRILL_SCENARIOS.find(s => s.scenario === 'all_correct_exceeding')!

test('setup view visible on load', async ({ page }) => {
  await mockDrillSession(page, FLOW_SCENARIO)
  await gotoSetup(page)
  await expect(page.locator(`[data-testid="${TEST_IDS.views.setup}"]`)).toBeVisible()
})

test('setup → drill → results navigation', async ({ page }) => {
  await mockDrillSession(page, FLOW_SCENARIO)
  await gotoSetup(page)

  const cfg = FLOW_SCENARIO.session_start_response.config
  await startSession(page, {
    yearLevel: cfg.year_level,
    strand: cfg.strand,
    difficulty: cfg.difficulty,
    count: cfg.count,
  })

  // Drill view appears
  await expect(page.locator(`[data-testid="${TEST_IDS.views.drill}"]`)).toBeVisible()

  // Timer and progress bar are present
  await expect(page.locator(`[data-testid="${TEST_IDS.drill.timer}"]`)).toBeVisible()
  await expect(page.locator(`[data-testid="${TEST_IDS.drill.progressBar}"]`)).toBeVisible()

  await completeDrillSession(page, FLOW_SCENARIO.user_answers)

  // Results view appears
  await expect(page.locator(`[data-testid="${TEST_IDS.views.results}"]`)).toBeVisible()
})

test('results → view history → back to setup', async ({ page }) => {
  await mockDrillSession(page, FLOW_SCENARIO)
  await gotoSetup(page)

  const cfg = FLOW_SCENARIO.session_start_response.config
  await startSession(page, {
    yearLevel: cfg.year_level,
    strand: cfg.strand,
    difficulty: cfg.difficulty,
    count: cfg.count,
  })

  await completeDrillSession(page, FLOW_SCENARIO.user_answers)

  // Navigate to progress
  await page.click(`[data-testid="${TEST_IDS.results.historyBtn}"]`)
  await expect(page.locator(`[data-testid="${TEST_IDS.views.progress}"]`)).toBeVisible()

  // Navigate back to setup
  await page.click(`[data-testid="${TEST_IDS.progress.backBtn}"]`)
  await expect(page.locator(`[data-testid="${TEST_IDS.views.setup}"]`)).toBeVisible()
})

test('results → start new session returns to setup', async ({ page }) => {
  await mockDrillSession(page, FLOW_SCENARIO)
  await gotoSetup(page)

  const cfg = FLOW_SCENARIO.session_start_response.config
  await startSession(page, {
    yearLevel: cfg.year_level,
    strand: cfg.strand,
    difficulty: cfg.difficulty,
    count: cfg.count,
  })

  await completeDrillSession(page, FLOW_SCENARIO.user_answers)

  await page.click(`[data-testid="${TEST_IDS.results.newSessionBtn}"]`)
  await expect(page.locator(`[data-testid="${TEST_IDS.views.setup}"]`)).toBeVisible()
})

test('setup → view progress history → back', async ({ page }) => {
  await mockDrillSession(page, FLOW_SCENARIO)
  await gotoSetup(page)

  await page.click(`[data-testid="${TEST_IDS.setup.historyBtn}"]`)
  await expect(page.locator(`[data-testid="${TEST_IDS.views.progress}"]`)).toBeVisible()

  // Empty state shown (no sessions in localStorage)
  await expect(page.locator(`[data-testid="${TEST_IDS.progress.emptyState}"]`)).toBeVisible()

  await page.click(`[data-testid="${TEST_IDS.progress.backBtn}"]`)
  await expect(page.locator(`[data-testid="${TEST_IDS.views.setup}"]`)).toBeVisible()
})

test('question counter increments as questions are answered', async ({ page }) => {
  await mockDrillSession(page, FLOW_SCENARIO)
  await gotoSetup(page)

  const cfg = FLOW_SCENARIO.session_start_response.config
  await startSession(page, {
    yearLevel: cfg.year_level,
    strand: cfg.strand,
    difficulty: cfg.difficulty,
    count: cfg.count,
  })

  await expect(page.locator(`[data-testid="${TEST_IDS.drill.questionCounter}"]`)).toContainText('1 / 5')

  await page.click(`[data-testid="${TEST_IDS.drill.optionBtn(FLOW_SCENARIO.user_answers[0])}"]`)
  await expect(page.locator(`[data-testid="${TEST_IDS.drill.questionCounter}"]`)).toContainText('2 / 5')
})
