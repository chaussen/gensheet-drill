import { test, expect } from '@playwright/test'
import { DRILL_SCENARIOS } from '../fixtures/sessions.ts'
import { mockStartError } from '../support/mock-api.ts'
import { gotoSetup, startSession } from '../support/actions.ts'
import { assertKatexFallback } from '../support/katex.ts'
import { TEST_IDS } from '../../../frontend/src/testing/testIds.ts'

const SIMPLE_SCENARIO = DRILL_SCENARIOS.find(s => s.scenario === 'year8_measurement_nolat')!

test('503 from /api/session/start shows error message', async ({ page }) => {
  await mockStartError(page, 503)
  await gotoSetup(page)

  const cfg = SIMPLE_SCENARIO.session_start_response.config
  await startSession(page, {
    yearLevel: cfg.year_level,
    strand: cfg.strand,
    difficulty: cfg.difficulty,
    count: cfg.count,
  })

  // Error message must appear in setup view
  await expect(page.locator(`[data-testid="${TEST_IDS.setup.errorMessage}"]`)).toBeVisible()

  // Still in setup view (not navigated away)
  await expect(page.locator(`[data-testid="${TEST_IDS.views.setup}"]`)).toBeVisible()
})

test('500 from /api/session/start shows error message', async ({ page }) => {
  await mockStartError(page, 500)
  await gotoSetup(page)

  const cfg = SIMPLE_SCENARIO.session_start_response.config
  await startSession(page, {
    yearLevel: cfg.year_level,
    strand: cfg.strand,
    difficulty: cfg.difficulty,
    count: cfg.count,
  })

  await expect(page.locator(`[data-testid="${TEST_IDS.setup.errorMessage}"]`)).toBeVisible()
  await expect(page.locator(`[data-testid="${TEST_IDS.views.setup}"]`)).toBeVisible()
})

test('corrupt localStorage does not crash the app', async ({ page }) => {
  // Set corrupt localStorage before navigating
  await page.goto('/')
  await page.evaluate(() => localStorage.setItem('gensheet_progress', 'INVALID_JSON_{{{'))
  await page.reload()

  // App should still load in setup view — no crash
  await expect(page.locator(`[data-testid="${TEST_IDS.views.setup}"]`)).toBeVisible()
})

test('KaTeX render error falls back to plain text', async ({ page }) => {
  // Inject a session with an option that will produce an invalid LaTeX expression
  // by setting latex_notation:true with an option text that toLatex() cannot parse cleanly
  await page.route('**/api/session/start', route =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        session_id: 'edge-001',
        config: { year_level: 8, strand: 'Algebra', difficulty: 'standard', count: 1 },
        questions: [
          {
            question_id: 'q-edge-katex',
            question_text: 'INVALID_LATEX',
            options: ['A', 'B', 'C', 'D'],
            question_type: 'single_select',
            latex_notation: true,
            vc_code: 'VC2M8A01',
            strand: 'Algebra',
            difficulty: 'standard',
            year_level: 8,
            generated_at: '2026-01-01T00:00:00Z',
          },
        ],
      }),
    })
  )
  await page.route('**/api/health', route =>
    route.fulfill({ status: 200, contentType: 'application/json', body: '{"status":"ok","ts":"2026-01-01T00:00:00Z","cache_size":0}' })
  )

  await gotoSetup(page)
  await startSession(page, { yearLevel: 8, strand: 'Algebra', difficulty: 'standard', count: 1 })

  await page.waitForSelector(`[data-testid="${TEST_IDS.views.drill}"]`)

  // Question text with invalid LaTeX should fall back gracefully (text still visible)
  await assertKatexFallback(page, 'INVALID_LATEX')

  // App should not be crashed
  await expect(page.locator(`[data-testid="${TEST_IDS.views.drill}"]`)).toBeVisible()
})
