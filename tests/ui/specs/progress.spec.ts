import { test, expect } from '@playwright/test'
import { DRILL_SCENARIOS } from '../fixtures/sessions.ts'
import { mockDrillSession } from '../support/mock-api.ts'
import { gotoSetup, startSession, completeDrillSession } from '../support/actions.ts'
import { TEST_IDS } from '../../../frontend/src/testing/testIds.ts'

const SIMPLE_SCENARIO = DRILL_SCENARIOS.find(s => s.scenario === 'all_correct_exceeding')!

test('localStorage has session entry after completing a session', async ({ page }) => {
  await mockDrillSession(page, SIMPLE_SCENARIO)
  await gotoSetup(page)

  const cfg = SIMPLE_SCENARIO.session_start_response.config
  await startSession(page, {
    yearLevel: cfg.year_level,
    strand: cfg.strand,
    difficulty: cfg.difficulty,
    count: cfg.count,
  })

  await completeDrillSession(page, SIMPLE_SCENARIO.user_answers)

  const raw = await page.evaluate(() => localStorage.getItem('gensheet_progress'))
  expect(raw).not.toBeNull()

  const progress = JSON.parse(raw!) as { sessions: unknown[] }
  expect(progress.sessions).toHaveLength(1)
})

test('progress view shows session row after completing a session', async ({ page }) => {
  await mockDrillSession(page, SIMPLE_SCENARIO)
  await gotoSetup(page)

  const cfg = SIMPLE_SCENARIO.session_start_response.config
  await startSession(page, {
    yearLevel: cfg.year_level,
    strand: cfg.strand,
    difficulty: cfg.difficulty,
    count: cfg.count,
  })

  await completeDrillSession(page, SIMPLE_SCENARIO.user_answers)

  // Go to progress view
  await page.click(`[data-testid="${TEST_IDS.results.historyBtn}"]`)
  await expect(page.locator(`[data-testid="${TEST_IDS.views.progress}"]`)).toBeVisible()

  // Session row exists (using the session_id from the mock response)
  const sessionId = SIMPLE_SCENARIO.session_result_response.session_id
  await expect(page.locator(`[data-testid="${TEST_IDS.progress.sessionRow(sessionId)}"]`)).toBeVisible()
})

test('progress view shows empty state when no sessions', async ({ page }) => {
  await mockDrillSession(page, SIMPLE_SCENARIO)
  await gotoSetup(page)

  await page.click(`[data-testid="${TEST_IDS.setup.historyBtn}"]`)
  await expect(page.locator(`[data-testid="${TEST_IDS.progress.emptyState}"]`)).toBeVisible()
})

test('clear history removes sessions from localStorage', async ({ page }) => {
  await mockDrillSession(page, SIMPLE_SCENARIO)
  await gotoSetup(page)

  const cfg = SIMPLE_SCENARIO.session_start_response.config
  await startSession(page, {
    yearLevel: cfg.year_level,
    strand: cfg.strand,
    difficulty: cfg.difficulty,
    count: cfg.count,
  })

  await completeDrillSession(page, SIMPLE_SCENARIO.user_answers)

  // Navigate to progress
  await page.click(`[data-testid="${TEST_IDS.results.historyBtn}"]`)

  // Clear history
  await page.click(`[data-testid="${TEST_IDS.progress.clearHistoryBtn}"]`)

  // Empty state now visible
  await expect(page.locator(`[data-testid="${TEST_IDS.progress.emptyState}"]`)).toBeVisible()

  // localStorage cleared
  const raw = await page.evaluate(() => localStorage.getItem('gensheet_progress'))
  const hasNoSessions = raw === null || JSON.parse(raw).sessions?.length === 0
  expect(hasNoSessions).toBe(true)
})
