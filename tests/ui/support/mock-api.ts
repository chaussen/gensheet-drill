import type { Page } from '@playwright/test'
import type { SessionScenario } from '../types/fixtures.ts'
import type { HealthResponse } from '../types/api.ts'

const HEALTH_RESPONSE: HealthResponse = {
  status: 'ok',
  ts: '2026-01-01T00:00:00Z',
  cache_size: 0,
}

export async function mockHealth(page: Page): Promise<void> {
  await page.route('**/api/health', route =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(HEALTH_RESPONSE),
    })
  )
}

export async function mockDrillSession(page: Page, scenario: SessionScenario): Promise<void> {
  await page.route('**/api/session/start', route =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(scenario.session_start_response),
    })
  )
  await page.route('**/api/session/*/submit', route =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(scenario.session_result_response),
    })
  )
  await mockHealth(page)
}

export async function mockStartError(page: Page, status: 503 | 500): Promise<void> {
  await page.route('**/api/session/start', route =>
    route.fulfill({
      status,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'AI service unavailable' }),
    })
  )
  await mockHealth(page)
}
