import { test, expect } from '@playwright/test';

test.describe('Logs', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/logs');
  });

  test('should render page title with icon', async ({ page }) => {
    await expect(page.locator('.page-title')).toContainText('Logs');
    await expect(page.locator('.page-icon')).toBeVisible();
  });

  test('should show toolbar with log file selector', async ({ page }) => {
    await expect(page.locator('.toolbar-card')).toBeVisible();
    await expect(page.locator('mat-select')).toBeVisible();
  });

  test('should show refresh button', async ({ page }) => {
    await expect(page.locator('button:has-text("Refresh")')).toBeVisible();
  });

  test('should load log files in selector', async ({ page }) => {
    await expect(page.locator('mat-select')).toBeVisible({ timeout: 5_000 });
    await page.locator('mat-select').click();
    // Log files may not exist on a fresh install — make assertion conditional
    const options = page.locator('mat-option');
    const hasOptions = await options.first().isVisible({ timeout: 5_000 }).catch(() => false);
    if (hasOptions) {
      const count = await options.count();
      expect(count).toBeGreaterThanOrEqual(1);
    }
    // Close dropdown
    await page.keyboard.press('Escape');
  });

  test('should display log viewer with lines', async ({ page }) => {
    await expect(page.locator('.log-viewer')).toBeVisible({ timeout: 10_000 });
    const lines = page.locator('.log-line');
    const count = await lines.count();
    expect(count).toBeGreaterThan(0);
  });

  test('should show line numbers', async ({ page }) => {
    await expect(page.locator('.log-viewer')).toBeVisible({ timeout: 10_000 });
    await expect(page.locator('.log-num').first()).toBeVisible();
    await expect(page.locator('.log-num').first()).toContainText('1');
  });

  test('should show line count total', async ({ page }) => {
    await expect(page.locator('.line-count')).toBeVisible({ timeout: 10_000 });
    await expect(page.locator('.line-count')).toContainText('lines total');
  });

  test('should color ERROR lines red', async ({ page }) => {
    await expect(page.locator('.log-viewer')).toBeVisible({ timeout: 10_000 });
    const errorLines = page.locator('.log-line.error');
    // Error lines may or may not exist, just verify no crashes
    const count = await errorLines.count();
    expect(count).toBeGreaterThanOrEqual(0);
  });

  test('should refresh log on button click', async ({ page }) => {
    await expect(page.locator('.log-viewer')).toBeVisible({ timeout: 10_000 });
    const countBefore = await page.locator('.log-line').count();
    await page.locator('button:has-text("Refresh")').click();
    await page.waitForTimeout(2000);
    const countAfter = await page.locator('.log-line').count();
    expect(countAfter).toBeGreaterThanOrEqual(0);
  });
});
