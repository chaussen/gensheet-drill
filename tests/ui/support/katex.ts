import type { Page, Locator } from '@playwright/test'
import { expect } from '@playwright/test'

/**
 * Assert exactly N .katex spans are present within a locator (default: full page).
 */
export async function assertKatexCount(locator: Locator, count: number): Promise<void> {
  await expect(locator.locator('.katex')).toHaveCount(count)
}

/**
 * Assert that the first .katex-mathml math element contains all listed MathML tag names.
 */
export async function assertMathmlTags(page: Page, tags: readonly string[]): Promise<void> {
  const mathml = page.locator('.katex-mathml math').first()
  await expect(mathml).toBeVisible()
  const innerHTML = await mathml.innerHTML()
  for (const tag of tags) {
    expect(innerHTML, `Expected MathML tag <${tag}> in KaTeX output`).toContain(`<${tag}`)
  }
}

/**
 * Assert no .katex spans exist anywhere on the page.
 */
export async function assertNoKatex(page: Page): Promise<void> {
  await expect(page.locator('.katex')).toHaveCount(0)
}

/**
 * Assert that a KaTeX render error fell back to plain text.
 * Verifies: no .katex, but the expected text is still visible.
 */
export async function assertKatexFallback(page: Page, expectedText: string): Promise<void> {
  await expect(page.locator('.katex')).toHaveCount(0)
  await expect(page.getByText(expectedText)).toBeVisible()
}
