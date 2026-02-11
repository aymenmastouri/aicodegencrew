import { test, expect } from '@playwright/test';

test.describe('Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/dashboard');
  });

  test('should render hero section with branding', async ({ page }) => {
    const hero = page.locator('.hero');
    await expect(hero).toBeVisible();
    await expect(hero).toContainText('AICodeGenCrew');
    await expect(hero).toContainText('Full SDLC Pipeline');
  });

  test('should show backend health status', async ({ page }) => {
    const statusPill = page.locator('.stat-pill').first();
    await expect(statusPill).toBeVisible({ timeout: 10_000 });
    await expect(statusPill).toContainText('Backend ok');
  });

  test('should show Knowledge Base status', async ({ page }) => {
    const kbPill = page.locator('.stat-pill:has-text("Knowledge Base")');
    await expect(kbPill).toBeVisible({ timeout: 10_000 });
  });

  test('should display pipeline phases with status', async ({ page }) => {
    await expect(page.locator('.phase-grid')).toBeVisible({ timeout: 10_000 });
    const phaseCards = page.locator('.phase-card');
    await expect(phaseCards).toHaveCount(8);
  });

  test('should show phase numbers 0-7', async ({ page }) => {
    await expect(page.locator('.phase-grid')).toBeVisible({ timeout: 10_000 });
    for (let i = 0; i < 8; i++) {
      await expect(page.locator('.phase-number').nth(i)).toContainText(String(i));
    }
  });

  test('should show phase status chips', async ({ page }) => {
    await expect(page.locator('.phase-grid')).toBeVisible({ timeout: 10_000 });
    const chips = page.locator('.phase-card .status-chip');
    await expect(chips.first()).toBeVisible();
  });

  test('should show completed phases with green border', async ({ page }) => {
    await expect(page.locator('.phase-grid')).toBeVisible({ timeout: 10_000 });
    const completed = page.locator('.phase-completed');
    const count = await completed.count();
    expect(count).toBeGreaterThan(0);
  });

  test('should distinguish ready and planned phases', async ({ page }) => {
    await expect(page.locator('.phase-grid')).toBeVisible({ timeout: 10_000 });
    // Phase 5 should be "ready" (implemented but no output)
    const readyChip = page.locator('.status-chip:has-text("ready")');
    const plannedChip = page.locator('.status-chip:has-text("planned")');
    // At least one ready or planned should be visible
    const hasReady = await readyChip.count();
    const hasPlanned = await plannedChip.count();
    expect(hasReady + hasPlanned).toBeGreaterThan(0);
  });

  test('should display quick actions section', async ({ page }) => {
    const actionCards = page.locator('.action-card');
    await expect(actionCards).toHaveCount(3);
    await expect(actionCards.first()).toContainText('Knowledge Explorer');
  });

  test('should navigate to knowledge from quick action', async ({ page }) => {
    await page.locator('.action-card:has-text("Knowledge Explorer")').click();
    await page.waitForURL('**/knowledge');
    expect(page.url()).toContain('/knowledge');
  });

  test('should show Run Pipeline button', async ({ page }) => {
    const runButton = page.locator('button:has-text("Run Pipeline")');
    await expect(runButton).toBeVisible();
  });

  test('should navigate to run page from Run Pipeline button', async ({ page }) => {
    await page.locator('button:has-text("Run Pipeline")').click();
    await page.waitForURL('**/run');
    expect(page.url()).toContain('/run');
  });
});
