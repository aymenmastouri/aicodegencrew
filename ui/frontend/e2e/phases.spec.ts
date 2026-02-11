import { test, expect } from '@playwright/test';

test.describe('Phases', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/phases');
  });

  test('should render page title with icon', async ({ page }) => {
    await expect(page.locator('.page-title')).toContainText('Phases');
    await expect(page.locator('.page-title mat-icon')).toBeVisible();
  });

  test('should show phase configuration table', async ({ page }) => {
    await expect(page.locator('.phase-table')).toBeVisible({ timeout: 10_000 });
  });

  test('should display 8 phases in table', async ({ page }) => {
    await expect(page.locator('.phase-table')).toBeVisible({ timeout: 10_000 });
    const rows = page.locator('.phase-table tbody tr');
    await expect(rows).toHaveCount(8);
  });

  test('should show phase numbers, IDs, names, and status', async ({ page }) => {
    await expect(page.locator('.phase-table')).toBeVisible({ timeout: 10_000 });
    await expect(page.locator('.phase-num').first()).toBeVisible();
    await expect(page.locator('td.mono:has-text("phase0_indexing")')).toBeVisible();
    await expect(page.locator('td:has-text("Repository Indexing")')).toBeVisible();
    await expect(page.locator('.status-chip').first()).toBeVisible();
  });

  test('should show play button for each phase', async ({ page }) => {
    await expect(page.locator('.phase-table')).toBeVisible({ timeout: 10_000 });
    const playButtons = page.locator('.phase-table button[mat-icon-button]');
    await expect(playButtons).toHaveCount(8);
  });

  test('should navigate to run page on play button click', async ({ page }) => {
    await expect(page.locator('.phase-table')).toBeVisible({ timeout: 10_000 });
    await page.locator('.phase-table button[mat-icon-button]').first().click();
    await page.waitForURL('**/run?phase=*');
    expect(page.url()).toContain('/run?phase=');
  });

  test('should show Presets section', async ({ page }) => {
    await expect(page.locator('.section-title:has-text("Presets")')).toBeVisible({ timeout: 10_000 });
  });

  test('should list preset expansion panels', async ({ page }) => {
    const presets = page.locator('mat-accordion mat-expansion-panel');
    await expect(presets.first()).toBeVisible({ timeout: 10_000 });
    const count = await presets.count();
    expect(count).toBeGreaterThanOrEqual(8);
  });

  test('should expand preset and show phases + run button', async ({ page }) => {
    const panels = page.locator('mat-accordion mat-expansion-panel');
    await expect(panels.first()).toBeVisible({ timeout: 10_000 });
    // Click the first preset panel
    await panels.first().locator('mat-expansion-panel-header').click();
    await expect(page.locator('mat-chip-set mat-chip').first()).toBeVisible({ timeout: 5_000 });
    await expect(page.locator('.preset-action button').first()).toBeVisible();
  });

  test('should navigate to run page on preset run button', async ({ page }) => {
    const panels = page.locator('mat-accordion mat-expansion-panel');
    await expect(panels.first()).toBeVisible({ timeout: 10_000 });
    await panels.first().locator('mat-expansion-panel-header').click();
    await page.locator('.preset-action button').first().click();
    await page.waitForURL('**/run?preset=*');
    expect(page.url()).toContain('/run?preset=');
  });
});
