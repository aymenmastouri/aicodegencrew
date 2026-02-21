import { test, expect } from '@playwright/test';

test.describe('Input Files', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/inputs');
  });

  test('should render page with title and icon', async ({ page }) => {
    const title = page.locator('.page-title');
    await expect(title).toBeVisible();
    await expect(title).toContainText('Input Files');
  });

  test('should show stats bar', async ({ page }) => {
    const statsBar = page.locator('.stats-bar');
    await expect(statsBar).toBeVisible({ timeout: 10_000 });
    await expect(statsBar).toContainText('Total Files');
    await expect(statsBar).toContainText('Total Size');
  });

  test('should show 4 category cards', async ({ page }) => {
    const cards = page.locator('.category-card');
    await expect(cards).toHaveCount(4, { timeout: 10_000 });
  });

  test('should show Task Files category', async ({ page }) => {
    const taskCard = page.locator('.category-card:has-text("Task Files")');
    await expect(taskCard).toBeVisible({ timeout: 10_000 });
    await expect(taskCard).toContainText('.xml');
    await expect(taskCard).toContainText('.json');
  });

  test('should show Requirements category', async ({ page }) => {
    const reqCard = page.locator('.category-card:has-text("Requirements")');
    await expect(reqCard).toBeVisible({ timeout: 10_000 });
    await expect(reqCard).toContainText('.xlsx');
    await expect(reqCard).toContainText('.csv');
  });

  test('should show Application Logs category', async ({ page }) => {
    const logCard = page.locator('.category-card:has-text("Application Logs")');
    await expect(logCard).toBeVisible({ timeout: 10_000 });
    await expect(logCard).toContainText('.log');
  });

  test('should show Reference Materials category', async ({ page }) => {
    const refCard = page.locator('.category-card:has-text("Reference Materials")');
    await expect(refCard).toBeVisible({ timeout: 10_000 });
    await expect(refCard).toContainText('.png');
    await expect(refCard).toContainText('.drawio');
  });

  test('each card should show drop zone', async ({ page }) => {
    const dropZones = page.locator('.drop-zone');
    await expect(dropZones).toHaveCount(4, { timeout: 10_000 });
    await expect(dropZones.first()).toContainText('Drag & drop or click to browse');
  });

  test('should show accepted format chips in each card', async ({ page }) => {
    const cards = page.locator('.category-card');
    await expect(cards).toHaveCount(4, { timeout: 10_000 });
    for (let i = 0; i < 4; i++) {
      const chips = cards.nth(i).locator('.ext-chip');
      const count = await chips.count();
      expect(count).toBeGreaterThan(0);
    }
  });

  test('should be reachable from sidenav', async ({ page }) => {
    await page.goto('/dashboard');
    // Scope to mat-nav-list to avoid matching onboarding card link
    const navItem = page.locator('mat-nav-list a[href="/inputs"]');
    await expect(navItem).toBeVisible();
    await navItem.click();
    await page.waitForURL('**/inputs');
    expect(page.url()).toContain('/inputs');
  });
});
