import { test, expect } from '@playwright/test';

test.describe('Reports', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/reports');
  });

  test('should render page title with icon', async ({ page }) => {
    await expect(page.locator('.page-title')).toContainText('Reports');
    await expect(page.locator('.page-title mat-icon')).toBeVisible();
  });

  test('should show tab group with Development Plans and Codegen tabs', async ({ page }) => {
    const tabGroup = page.locator('mat-tab-group');
    await expect(tabGroup).toBeVisible({ timeout: 10_000 });
    await expect(tabGroup).toContainText('Development Plans');
    await expect(tabGroup).toContainText('Codegen Reports');
  });

  test('should display development plans or empty state', async ({ page }) => {
    const content = page.locator('.report-accordion, .tab-empty');
    await expect(content.first()).toBeVisible({ timeout: 10_000 });
  });

  test('should expand a plan and show JSON content if plans exist', async ({ page }) => {
    const panel = page.locator('mat-expansion-panel').first();
    const panelVisible = await panel.isVisible({ timeout: 10_000 }).catch(() => false);
    if (panelVisible) {
      await panel.locator('mat-expansion-panel-header').click();
      await expect(page.locator('.plan-content').first()).toBeVisible({ timeout: 5_000 });
    }
  });

  test('should switch to Codegen Reports tab', async ({ page }) => {
    // Wait for tabs to render
    await expect(page.locator('mat-tab-group')).toBeVisible({ timeout: 10_000 });
    // Use role-based selector for tab
    const codegenTab = page.getByRole('tab', { name: /Codegen/i });
    await expect(codegenTab).toBeVisible({ timeout: 5_000 });
    await codegenTab.click();
    // Either shows reports or empty state
    const content = page.locator('.report-accordion, .tab-empty, .empty-inline');
    await expect(content.first()).toBeVisible({ timeout: 10_000 });
  });
});
