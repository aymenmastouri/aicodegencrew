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

  // --- Reset & History Tests ---

  test('should show Reset All button in pipeline phases header', async ({ page }) => {
    await expect(page.locator('.phase-grid')).toBeVisible({ timeout: 10_000 });
    const resetAllBtn = page.locator('button:has-text("Reset All")');
    await expect(resetAllBtn).toBeVisible();
  });

  test('should show reset mini-buttons on completed phase cards', async ({ page }) => {
    await expect(page.locator('.phase-grid')).toBeVisible({ timeout: 10_000 });
    const completedCards = page.locator('.phase-completed');
    const count = await completedCards.count();
    if (count > 0) {
      // Each completed card should have a reset mini-button
      const resetBtns = page.locator('.phase-completed .reset-mini');
      await expect(resetBtns).toHaveCount(count);
    }
  });

  test('should show Recent Activity section with history entries', async ({ page }) => {
    const activitySection = page.locator('.activity-list');
    // May or may not have entries depending on state
    const visible = await activitySection.isVisible().catch(() => false);
    if (visible) {
      const rows = page.locator('.activity-row');
      const count = await rows.count();
      expect(count).toBeGreaterThan(0);
      expect(count).toBeLessThanOrEqual(5);
    }
  });

  test('should show trigger chips in recent activity', async ({ page }) => {
    const activitySection = page.locator('.activity-list');
    const visible = await activitySection.isVisible().catch(() => false);
    if (visible) {
      const triggerChips = page.locator('.activity-row .trigger-chip');
      if ((await triggerChips.count()) > 0) {
        const text = await triggerChips.first().textContent();
        expect(text?.trim()).toMatch(/Run|Reset/);
      }
    }
  });

  test('should show "View all history" link pointing to /history', async ({ page }) => {
    const activitySection = page.locator('.activity-list');
    const visible = await activitySection.isVisible().catch(() => false);
    if (visible) {
      const link = page.locator('.activity-more');
      await expect(link).toBeVisible();
      await expect(link).toContainText('View all history');
      const href = await link.getAttribute('href');
      expect(href).toContain('/history');
    }
  });

  test('should show hero section', async ({ page }) => {
    const hero = page.locator('.hero');
    await expect(hero).toBeVisible();
  });
});
