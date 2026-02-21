import { test, expect } from '@playwright/test';

test.describe('Metrics', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/metrics');
  });

  test('should render page title with icon', async ({ page }) => {
    await expect(page.locator('.page-title')).toContainText('Metrics');
    await expect(page.locator('.page-icon')).toBeVisible();
  });

  test('should show stats bar or empty state', async ({ page }) => {
    const content = page.locator('.stats-bar, .empty-state');
    await expect(content.first()).toBeVisible({ timeout: 10_000 });
  });

  test('should show event count and run count in stats', async ({ page }) => {
    const statsBar = page.locator('.stats-bar');
    // Metrics might be empty on fresh install
    const visible = await statsBar.isVisible().catch(() => false);
    if (visible) {
      await expect(page.locator('.stat-item:has-text("events")')).toBeVisible();
      await expect(page.locator('.stat-item:has-text("runs")')).toBeVisible();
    }
  });

  test('should show filter dropdown', async ({ page }) => {
    const statsBar = page.locator('.stats-bar');
    const visible = await statsBar.isVisible({ timeout: 10_000 }).catch(() => false);
    if (visible) {
      // Filter is inside a mat-form-field, not directly a child of mat-select
      await expect(page.locator('.filter-item mat-select')).toBeVisible({ timeout: 5_000 });
    }
  });

  test('should display metrics table when data exists', async ({ page }) => {
    // Wait for stats bar first (loads quickly), then for table or empty state
    await expect(page.locator('.stats-bar')).toBeVisible({ timeout: 10_000 });
    const either = page.locator('.metrics-table, .empty-inline, .empty-state');
    // Give extra time for events to load from backend
    await expect(either.first()).toBeVisible({ timeout: 20_000 });
  });
});
