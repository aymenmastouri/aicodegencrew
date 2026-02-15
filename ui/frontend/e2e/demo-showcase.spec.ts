import { test, expect, Page } from '@playwright/test';

/**
 * Demo Showcase — one continuous flow through the entire SDLC Pilot UI.
 * Designed to produce a single long video for AI Challenge presentations.
 *
 * Run:  npx playwright test --project=demo e2e/demo-showcase.spec.ts
 * Video output: test-results/demo-showcase-Demo-Showcase-.../video.webm
 */

const PAUSE = 1200; // ms between visual steps — gives viewers time to read

async function pause(page: Page, ms = PAUSE) {
  await page.waitForTimeout(ms);
}

async function navigateTo(page: Page, label: string, url: string) {
  await page.locator(`a[mat-list-item]:has-text("${label}")`).click();
  await page.waitForURL(`**${url}`);
  await pause(page);
}

test.describe('Demo Showcase', () => {
  test('Full app walkthrough', async ({ page }) => {
    // Generous timeout — pipeline run can take minutes
    test.setTimeout(360_000);

    // ──────────────────────────────────────────────
    // 1. DASHBOARD
    // ──────────────────────────────────────────────
    await page.goto('/dashboard');
    await expect(page.locator('.hero')).toBeVisible({ timeout: 15_000 });
    await pause(page);

    // Phase grid — 8 cards
    await expect(page.locator('.phase-grid')).toBeVisible({ timeout: 10_000 });
    await expect(page.locator('.phase-card')).toHaveCount(8);
    await pause(page);

    // Quick actions
    await expect(page.locator('.action-card').first()).toBeVisible();
    await pause(page, 800);

    // Health / stat pills
    const statPill = page.locator('.stat-pill').first();
    if (await statPill.isVisible().catch(() => false)) {
      await pause(page, 600);
    }

    // Run Pipeline button
    await expect(page.locator('button:has-text("Run Pipeline")')).toBeVisible();
    await pause(page, 800);

    // ──────────────────────────────────────────────
    // 2. SIDENAV — show all 11 nav items
    // ──────────────────────────────────────────────
    const navItems = page.locator('mat-nav-list a[mat-list-item]');
    await expect(navItems).toHaveCount(11);
    await pause(page);

    // ──────────────────────────────────────────────
    // 3. RUN PIPELINE — LIVE EXECUTION (core scene)
    // ──────────────────────────────────────────────
    await navigateTo(page, 'Run Pipeline', '/run');

    // Config card visible
    await expect(page.locator('.config-card')).toBeVisible({ timeout: 10_000 });
    await pause(page, 800);

    // Open preset dropdown, choose "Facts Extraction"
    await page.locator('mat-select').first().click();
    await expect(page.locator('mat-option').first()).toBeVisible({ timeout: 10_000 });
    await pause(page, 600);

    const factsOption = page.locator('mat-option:has-text("Facts Extraction")');
    const hasFactsPreset = await factsOption.isVisible().catch(() => false);
    if (hasFactsPreset) {
      await factsOption.click();
    } else {
      // Fallback: pick the first preset
      await page.locator('mat-option').first().click();
    }
    await pause(page);

    // Phase chips should appear
    const chips = page.locator('.phase-chips mat-chip');
    await expect(chips.first()).toBeVisible({ timeout: 5_000 });
    await pause(page, 800);

    // Click "Run Pipeline"
    const runBtn = page.locator('.config-card button:has-text("Run Pipeline")');
    await expect(runBtn).toBeEnabled({ timeout: 5_000 });
    await runBtn.click();
    await pause(page, 1500);

    // --- Observe live pipeline execution ---

    // Progress bar
    const progressBar = page.locator('mat-progress-bar.run-progress');
    const hasProgress = await progressBar.isVisible({ timeout: 10_000 }).catch(() => false);
    if (hasProgress) {
      await pause(page);
    }

    // Stepper — running phase
    const stepRunning = page.locator('.stepper-step.step-running');
    const hasStep = await stepRunning.first().isVisible({ timeout: 10_000 }).catch(() => false);
    if (hasStep) {
      await pause(page);
    }

    // Status card — running state
    const statusRunning = page.locator('.status-card.state-running');
    const hasRunning = await statusRunning.isVisible({ timeout: 10_000 }).catch(() => false);
    if (hasRunning) {
      await pause(page, 1500);
    }

    // Live log stream
    const logViewport = page.locator('.log-viewport');
    const hasLogs = await logViewport.isVisible({ timeout: 15_000 }).catch(() => false);
    if (hasLogs) {
      // Wait for first log line
      await expect(page.locator('.log-viewport .log-line').first()).toBeVisible({ timeout: 15_000 });
      await pause(page, 2000);

      // Scroll log viewport down to show new lines flowing in
      await logViewport.evaluate((el) => el.scrollTo(0, el.scrollHeight));
      await pause(page, 1500);
      await logViewport.evaluate((el) => el.scrollTo(0, el.scrollHeight));
      await pause(page, 1500);
    }

    // Metrics bar (tokens, ETA)
    const metricsBar = page.locator('.metrics-bar, .run-metrics');
    if (await metricsBar.isVisible().catch(() => false)) {
      await pause(page, 1000);
    }

    // Wait for pipeline completion (up to 5 minutes)
    const completed = page.locator('.status-card.state-completed');
    const failed = page.locator('.status-card.state-failed');
    try {
      await expect(completed.or(failed)).toBeVisible({ timeout: 300_000 });
      await pause(page, 2000);
    } catch {
      // Pipeline still running after 5 min — continue demo anyway
      await pause(page, 2000);
    }

    // Celebration banner
    const banner = page.locator('.celebration-banner');
    if (await banner.isVisible().catch(() => false)) {
      await pause(page, 2000);
    }

    // ──────────────────────────────────────────────
    // 4. INPUT FILES
    // ──────────────────────────────────────────────
    await navigateTo(page, 'Input Files', '/inputs');

    await expect(page.locator('.category-card')).toHaveCount(4, { timeout: 10_000 });
    await pause(page);

    // Show drop zones
    await expect(page.locator('.drop-zone').first()).toBeVisible();
    await pause(page, 800);

    // Show accepted format chips
    await expect(page.locator('.ext-chip').first()).toBeVisible();
    await pause(page, 800);

    // ──────────────────────────────────────────────
    // 5. COLLECTORS
    // ──────────────────────────────────────────────
    await navigateTo(page, 'Collectors', '/collectors');

    await expect(page.locator('.collectors-table')).toBeVisible({ timeout: 10_000 });
    await pause(page);

    // Stats bar
    await expect(page.locator('.stats-bar')).toBeVisible();
    await pause(page, 600);

    // 15 rows
    await expect(page.locator('.collectors-table tbody tr')).toHaveCount(15);
    await pause(page, 800);

    // Toggle switches
    await expect(page.locator('mat-slide-toggle').first()).toBeVisible();
    await pause(page, 600);

    // Output preview (if data exists)
    const viewBtns = page.locator('.collectors-table button[mat-icon-button]');
    if ((await viewBtns.count()) > 0) {
      await viewBtns.first().click();
      const outputCard = page.locator('.output-card');
      if (await outputCard.isVisible({ timeout: 5_000 }).catch(() => false)) {
        await pause(page, 1200);
        await page.locator('.output-card button:has-text("Close")').click();
        await pause(page, 400);
      }
    }

    // ──────────────────────────────────────────────
    // 6. SETTINGS
    // ──────────────────────────────────────────────
    await navigateTo(page, 'Settings', '/settings');

    // 5 tabs
    await expect(page.locator('.mat-mdc-tab')).toHaveCount(5);
    await pause(page, 800);

    // Cycle through all 5 tabs
    const tabNames = ['General', 'LLM', 'Indexing', 'Phases', 'Advanced'];
    for (const name of tabNames) {
      await page.locator(`.mat-mdc-tab:has-text("${name}")`).click();
      await pause(page, 800);
    }

    // Back to General — show Save/Reset
    await page.locator('.mat-mdc-tab:has-text("General")').click();
    await expect(page.locator('button:has-text("Save")')).toBeVisible();
    await expect(page.locator('button:has-text("Reset to defaults")')).toBeVisible();
    await pause(page, 800);

    // ──────────────────────────────────────────────
    // 7. PHASES
    // ──────────────────────────────────────────────
    await navigateTo(page, 'Phases', '/phases');

    await expect(page.locator('.phase-table')).toBeVisible({ timeout: 10_000 });
    await expect(page.locator('.phase-table tbody tr')).toHaveCount(8);
    await pause(page);

    // Play + reset buttons
    await expect(page.locator('.phase-table button[mat-icon-button]')).toHaveCount(16);
    await pause(page, 800);

    // Presets — expand first panel
    const presetPanels = page.locator('mat-accordion mat-expansion-panel');
    await expect(presetPanels.first()).toBeVisible({ timeout: 10_000 });
    await presetPanels.first().locator('mat-expansion-panel-header').click();
    await pause(page, 1000);

    // Collapse it back
    await presetPanels.first().locator('mat-expansion-panel-header').click();
    await pause(page, 600);

    // ──────────────────────────────────────────────
    // 8. KNOWLEDGE
    // ──────────────────────────────────────────────
    await navigateTo(page, 'Knowledge', '/knowledge');

    const tabGroup = page.locator('mat-tab-group');
    await expect(tabGroup).toBeVisible({ timeout: 10_000 });
    await pause(page);

    // 3 tabs: Arc42, C4, KB
    const arc42Tab = page.getByRole('tab', { name: /Arc42/i });
    const c4Tab = page.getByRole('tab', { name: /C4/i });
    const kbTab = page.getByRole('tab', { name: /Knowledge Base/i });

    // Arc42 — file cards
    await expect(page.locator('.file-card').first()).toBeVisible({ timeout: 10_000 });
    await pause(page, 800);

    // Open a file viewer
    await page.locator('.file-card').first().click();
    const viewer = page.locator('.viewer-panel');
    if (await viewer.isVisible({ timeout: 5_000 }).catch(() => false)) {
      await pause(page, 1500);
      // Close viewer
      const closeBtn = page.locator('.viewer-actions button:has(mat-icon:has-text("close"))');
      if (await closeBtn.isVisible().catch(() => false)) {
        await closeBtn.click();
        await pause(page, 400);
      }
    }

    // Switch to C4
    if (await c4Tab.isVisible().catch(() => false)) {
      await c4Tab.click();
      await pause(page, 1000);
    }

    // Switch to Knowledge Base
    if (await kbTab.isVisible().catch(() => false)) {
      await kbTab.click();
      await pause(page, 1000);
    }

    // ──────────────────────────────────────────────
    // 9. REPORTS
    // ──────────────────────────────────────────────
    await navigateTo(page, 'Reports', '/reports');

    await expect(page.locator('mat-tab-group')).toBeVisible({ timeout: 10_000 });
    await pause(page, 800);

    // 4 tabs
    const reportTabs = [
      /Architecture/i,
      /Development Plans/i,
      /Code Generation/i,
      /Git Branches/i,
    ];
    for (const name of reportTabs) {
      const tab = page.getByRole('tab', { name });
      if (await tab.isVisible().catch(() => false)) {
        await tab.click();
        await pause(page, 1000);
      }
    }

    // Expand a doc preview if available
    const docCard = page.locator('.doc-file-card').first();
    if (await docCard.isVisible().catch(() => false)) {
      await docCard.click();
      await pause(page, 1200);
    }

    // ──────────────────────────────────────────────
    // 10. METRICS
    // ──────────────────────────────────────────────
    await navigateTo(page, 'Metrics', '/metrics');

    const metricsContent = page.locator('.stats-bar, .empty-state');
    await expect(metricsContent.first()).toBeVisible({ timeout: 10_000 });
    await pause(page);

    // Filter dropdown
    const filterSelect = page.locator('.filter-item mat-select');
    if (await filterSelect.isVisible().catch(() => false)) {
      await pause(page, 800);
    }

    // Table
    const metricsTable = page.locator('.metrics-table');
    if (await metricsTable.isVisible().catch(() => false)) {
      await pause(page, 800);
    }

    // ──────────────────────────────────────────────
    // 11. LOGS
    // ──────────────────────────────────────────────
    await navigateTo(page, 'Logs', '/logs');

    await expect(page.locator('.toolbar-card')).toBeVisible();
    await pause(page, 600);

    // Open file selector
    await page.locator('mat-select').click();
    await expect(page.locator('mat-option').first()).toBeVisible({ timeout: 10_000 });
    await pause(page, 800);
    await page.keyboard.press('Escape');

    // Log viewer
    await expect(page.locator('.log-viewer')).toBeVisible({ timeout: 10_000 });
    await pause(page, 800);

    // Refresh
    await page.locator('button:has-text("Refresh")').click();
    await pause(page, 800);

    // ──────────────────────────────────────────────
    // 12. HISTORY
    // ──────────────────────────────────────────────
    await navigateTo(page, 'History', '/history');

    // Filter chips
    const filterBar = page.locator('.filter-bar');
    await expect(filterBar).toBeVisible();
    await expect(filterBar.locator('.filter-chip')).toHaveCount(4);
    await pause(page, 800);

    // Search input
    await expect(page.locator('.search-input')).toBeVisible();
    await pause(page, 600);

    // Table or empty state
    await page.waitForTimeout(2000);
    const historyTable = page.locator('.history-table');
    const emptyState = page.locator('.empty-state');
    const historyContent = page.locator('.history-table, .empty-state');
    if (await historyContent.first().isVisible().catch(() => false)) {
      await pause(page, 800);
    }

    // Click a filter chip
    const runsFilter = page.locator('.filter-chip:has-text("Runs")');
    if (await runsFilter.isVisible().catch(() => false)) {
      await runsFilter.click();
      await pause(page, 800);
    }

    // ──────────────────────────────────────────────
    // 13. RESPONSIVE — viewport transitions
    // ──────────────────────────────────────────────
    // Return to dashboard for visual effect
    await navigateTo(page, 'Dashboard', '/dashboard');

    // Desktop full (1500px)
    await page.setViewportSize({ width: 1500, height: 900 });
    await pause(page, 1200);

    // Tablet rail (1200px)
    await page.setViewportSize({ width: 1200, height: 900 });
    await pause(page, 1200);

    // Mobile overlay (900px)
    await page.setViewportSize({ width: 900, height: 900 });
    await pause(page, 1200);

    // Open overlay sidenav
    const menuBtn = page.locator('mat-toolbar button[mat-icon-button]');
    if (await menuBtn.isVisible().catch(() => false)) {
      await menuBtn.click();
      await pause(page, 1000);
    }

    // Back to desktop
    await page.setViewportSize({ width: 1440, height: 900 });
    await pause(page, 1200);

    // ──────────────────────────────────────────────
    // FIN — back to dashboard hero for closing shot
    // ──────────────────────────────────────────────
    await page.goto('/dashboard');
    await expect(page.locator('.hero')).toBeVisible({ timeout: 10_000 });
    await pause(page, 2000);
  });
});
