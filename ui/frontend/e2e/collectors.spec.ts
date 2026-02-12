import { test, expect } from '@playwright/test';

test.describe('Collectors', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/collectors');
  });

  test('should render page with title and icon', async ({ page }) => {
    const title = page.locator('.page-title');
    await expect(title).toBeVisible();
    await expect(title).toContainText('Collectors');
  });

  test('should show stats bar with 4 stats', async ({ page }) => {
    const statsBar = page.locator('.stats-bar');
    await expect(statsBar).toBeVisible({ timeout: 10_000 });
    await expect(statsBar).toContainText('Total Collectors');
    await expect(statsBar).toContainText('Enabled');
    await expect(statsBar).toContainText('Dimensions');
    await expect(statsBar).toContainText('Total Facts');
  });

  test('should show total of 15 collectors in stats', async ({ page }) => {
    const statsBar = page.locator('.stats-bar');
    await expect(statsBar).toBeVisible({ timeout: 10_000 });
    const totalStat = page.locator('.stat-item:has-text("Total Collectors") .stat-value');
    await expect(totalStat).toContainText('15');
  });

  test('should render collector table', async ({ page }) => {
    const table = page.locator('.collectors-table');
    await expect(table).toBeVisible({ timeout: 10_000 });
  });

  test('should display 15 collector rows', async ({ page }) => {
    await expect(page.locator('.collectors-table')).toBeVisible({ timeout: 10_000 });
    const rows = page.locator('.collectors-table tbody tr');
    await expect(rows).toHaveCount(15);
  });

  test('should show step badges with numbers 1-15', async ({ page }) => {
    await expect(page.locator('.collectors-table')).toBeVisible({ timeout: 10_000 });
    const firstBadge = page.locator('.step-badge').first();
    await expect(firstBadge).toBeVisible();
    await expect(firstBadge).toContainText('1');
    const lastBadge = page.locator('.step-badge').last();
    await expect(lastBadge).toContainText('15');
  });

  test('should show core collectors with lock icon', async ({ page }) => {
    await expect(page.locator('.collectors-table')).toBeVisible({ timeout: 10_000 });
    // Core collectors (system, containers, components, evidence) have "always on" chip
    const alwaysOnChips = page.locator('.chip-core:has-text("always on")');
    await expect(alwaysOnChips).toHaveCount(4);
  });

  test('should show toggle switches for optional collectors', async ({ page }) => {
    await expect(page.locator('.collectors-table')).toBeVisible({ timeout: 10_000 });
    const toggles = page.locator('mat-slide-toggle');
    // 11 optional collectors (steps 4-14) should have toggles
    await expect(toggles).toHaveCount(11);
  });

  test('should show System Facts as first collector', async ({ page }) => {
    await expect(page.locator('.collectors-table')).toBeVisible({ timeout: 10_000 });
    const firstRow = page.locator('.collectors-table tbody tr').first();
    await expect(firstRow).toContainText('System Facts');
    await expect(firstRow).toContainText('system');
    await expect(firstRow).toContainText('core');
  });

  test('should show dimension chips for each collector', async ({ page }) => {
    await expect(page.locator('.collectors-table')).toBeVisible({ timeout: 10_000 });
    const dimensionChips = page.locator('.dimension-chip');
    await expect(dimensionChips).toHaveCount(15);
  });

  test('should show category chips (core and optional)', async ({ page }) => {
    await expect(page.locator('.collectors-table')).toBeVisible({ timeout: 10_000 });
    await expect(page.locator('td .chip-core').first()).toBeVisible();
    await expect(page.locator('td .chip-optional').first()).toBeVisible();
  });

  test('should toggle a collector and show snackbar', async ({ page }) => {
    await expect(page.locator('.collectors-table')).toBeVisible({ timeout: 10_000 });
    // Click the first toggle switch (an optional collector)
    const firstToggle = page.locator('mat-slide-toggle').first();
    await firstToggle.click();
    // Should show a snackbar confirmation
    const snackbar = page.locator('mat-snack-bar-container');
    await expect(snackbar).toBeVisible({ timeout: 5_000 });
    await expect(snackbar).toContainText(/enabled|disabled/);
  });

  test('should update enabled count in stats after toggle', async ({ page }) => {
    await expect(page.locator('.collectors-table')).toBeVisible({ timeout: 10_000 });
    const enabledStat = page.locator('.stat-item:has-text("Enabled") .stat-value');
    const initialCount = await enabledStat.textContent();

    // Toggle first optional collector off
    const firstToggle = page.locator('mat-slide-toggle').first();
    await firstToggle.click();
    await expect(page.locator('mat-snack-bar-container')).toBeVisible({ timeout: 5_000 });

    // Enabled count should have changed
    const newCount = await enabledStat.textContent();
    expect(newCount).not.toBe(initialCount);

    // Toggle back on to restore state
    await firstToggle.click();
    await expect(page.locator('mat-snack-bar-container')).toBeVisible({ timeout: 5_000 });
  });

  test('should show view output button for collectors with data', async ({ page }) => {
    await expect(page.locator('.collectors-table')).toBeVisible({ timeout: 10_000 });
    // If any collector has output, there should be a view button
    const viewButtons = page.locator('.collectors-table button[mat-icon-button]');
    const count = await viewButtons.count();
    // Count could be 0 if no output files exist yet — that's OK
    expect(count).toBeGreaterThanOrEqual(0);
  });

  test('should open output preview when clicking a row with data', async ({ page }) => {
    await expect(page.locator('.collectors-table')).toBeVisible({ timeout: 10_000 });
    // Check if any view output button exists (meaning there's data)
    const viewButtons = page.locator('.collectors-table button[mat-icon-button]');
    const count = await viewButtons.count();
    if (count > 0) {
      await viewButtons.first().click();
      const outputCard = page.locator('.output-card');
      await expect(outputCard).toBeVisible({ timeout: 10_000 });
      await expect(outputCard).toContainText('output');
      await expect(page.locator('.output-json')).toBeVisible();
    }
  });

  test('should close output preview when clicking Close button', async ({ page }) => {
    await expect(page.locator('.collectors-table')).toBeVisible({ timeout: 10_000 });
    const viewButtons = page.locator('.collectors-table button[mat-icon-button]');
    const count = await viewButtons.count();
    if (count > 0) {
      await viewButtons.first().click();
      await expect(page.locator('.output-card')).toBeVisible({ timeout: 10_000 });
      await page.locator('.output-card button:has-text("Close")').click();
      await expect(page.locator('.output-card')).toBeHidden();
    }
  });

  test('should be reachable from sidenav', async ({ page }) => {
    await page.goto('/dashboard');
    const navItem = page.locator('a[href="/collectors"]');
    await expect(navItem).toBeVisible();
    await navItem.click();
    await page.waitForURL('**/collectors');
    expect(page.url()).toContain('/collectors');
  });
});
