import { test, expect, Page } from '@playwright/test';

/**
 * Demo Showcase — FULL SCENARIO for AI Challenge presentation.
 *
 * Flow: Reset All → Show empty app → Run Discover→Implement → Show ALL artifacts
 *
 * Run:  npx playwright test --project=demo e2e/demo-showcase.spec.ts
 * Video: test-results/demo-showcase-Demo-Showcase-.../video.webm
 */

const PAUSE = 1200;
const LONG_PAUSE = 2000;
const READ_PAUSE = 3000;

async function pause(page: Page, ms = PAUSE) {
  await page.waitForTimeout(ms);
}

async function navigateTo(page: Page, label: string, url: string) {
  await page.locator(`a[mat-list-item]:has-text("${label}")`).click();
  await page.waitForURL(`**${url}`);
  await pause(page);
}

/** Safely scroll an element if it exists and has overflow */
async function scrollThrough(page: Page, selector: string, fast = false) {
  const el = page.locator(selector).first();
  if (await el.isVisible().catch(() => false)) {
    const ms = fast ? 600 : PAUSE;
    await el.evaluate((e) => e.scrollTo(0, e.scrollHeight / 2));
    await pause(page, ms);
    await el.evaluate((e) => e.scrollTo(0, e.scrollHeight));
    await pause(page, ms);
  }
}

test.describe('Demo Showcase', () => {
  test('Full app walkthrough', async ({ page }) => {
    test.setTimeout(3_600_000); // 60 min

    // ════════════════════════════════════════════════
    // PROLOGUE: RESET EVERYTHING
    // ════════════════════════════════════════════════
    // Call reset API — clears all phases except Discover's ChromaDB
    // Retry up to 3 times (409 = pipeline still running from previous test)
    for (let attempt = 0; attempt < 3; attempt++) {
      const resetResp = await page.request.post('http://localhost:4200/api/reset/all');
      if (resetResp.ok()) break;
      // 409 = pipeline running — wait and retry
      if (resetResp.status() === 409 && attempt < 2) {
        await pause(page, 10_000);
        continue;
      }
      // Non-409 or last attempt — continue anyway (best effort)
      break;
    }
    await pause(page, LONG_PAUSE);

    // Also clear Discover phase state (for fully clean slate)
    await page.request.post('http://localhost:4200/api/reset/clear-state', {
      data: { phase_ids: ['discover'], cascade: false },
    }).catch(() => {});
    await pause(page);

    // ════════════════════════════════════════════════
    // ACT 1: SHOW THE EMPTY APP
    // ════════════════════════════════════════════════

    // ── 1. DASHBOARD — all phases pending ──
    await page.goto('/dashboard');
    await expect(page.locator('.hero')).toBeVisible({ timeout: 15_000 });
    await pause(page, LONG_PAUSE);

    // Phase grid — 8 cards, all should be pending/planned
    await expect(page.locator('.phase-grid')).toBeVisible({ timeout: 10_000 });
    await expect(page.locator('.phase-card')).toHaveCount(8);
    await pause(page, READ_PAUSE);

    // Quick actions
    await expect(page.locator('.action-card').first()).toBeVisible();
    await pause(page);

    // Health pills
    const statPill = page.locator('.stat-pill').first();
    if (await statPill.isVisible().catch(() => false)) {
      await pause(page);
    }

    // ── 2. SIDENAV — 11 items ──
    const navItems = page.locator('mat-nav-list a[mat-list-item]');
    await expect(navItems).toHaveCount(11);
    await pause(page, LONG_PAUSE);

    // ── 3. KNOWLEDGE — empty state ──
    await navigateTo(page, 'Knowledge', '/knowledge');
    // Should show empty state after reset
    const kbEmpty = page.locator('.empty-state');
    const kbStats = page.locator('.stats-bar');
    await expect(kbEmpty.or(kbStats).first()).toBeVisible({ timeout: 10_000 });
    await pause(page, LONG_PAUSE);

    // ── 4. REPORTS — empty state ──
    await navigateTo(page, 'Reports', '/reports');
    await expect(page.locator('mat-tab-group, .empty-state').first()).toBeVisible({ timeout: 10_000 });
    await pause(page, LONG_PAUSE);

    // ── 5. SETTINGS — show ALL config tabs with parameters ──
    await navigateTo(page, 'Settings', '/settings');
    const settingsTabs = page.locator('.mat-mdc-tab');
    await expect(settingsTabs.first()).toBeVisible({ timeout: 10_000 });
    const settingsTabCount = await settingsTabs.count();
    for (let i = 0; i < settingsTabCount; i++) {
      await settingsTabs.nth(i).click();
      await pause(page);

      // Scroll through tab content to show all fields/parameters
      const tabContent = page.locator('.tab-content, .settings-form, mat-tab-body .mat-mdc-tab-body-content').first();
      if (await tabContent.isVisible().catch(() => false)) {
        await tabContent.evaluate((el) => el.scrollTo(0, el.scrollHeight / 2));
        await pause(page, LONG_PAUSE);
        await tabContent.evaluate((el) => el.scrollTo(0, el.scrollHeight));
        await pause(page, LONG_PAUSE);
        await tabContent.evaluate((el) => el.scrollTo(0, 0));
        await pause(page, 600);
      }
    }
    await settingsTabs.first().click();
    await pause(page);

    // ── 6. INPUT FILES — show all categories + existing files ──
    await navigateTo(page, 'Input Files', '/inputs');

    // Stats bar
    const inputStats = page.locator('.stats-bar');
    if (await inputStats.isVisible({ timeout: 10_000 }).catch(() => false)) {
      await pause(page, LONG_PAUSE);
    }

    await expect(page.locator('.category-card')).toHaveCount(4, { timeout: 10_000 });
    await pause(page, LONG_PAUSE);

    // Show each category card: drop zone, accepted formats, existing files
    const categoryCards = page.locator('.category-card');
    for (let i = 0; i < 4; i++) {
      const card = categoryCards.nth(i);
      // Scroll card into view
      await card.scrollIntoViewIfNeeded();
      await pause(page);

      // Show file list if files exist in this category
      const fileItems = card.locator('.file-item, .file-row, .file-entry');
      if ((await fileItems.count()) > 0) {
        await pause(page, LONG_PAUSE);
      }
    }
    // Back to top
    await page.evaluate(() => window.scrollTo(0, 0));
    await pause(page);

    // ── 7. COLLECTORS ──
    await navigateTo(page, 'Collectors', '/collectors');
    await expect(page.locator('.collectors-table')).toBeVisible({ timeout: 10_000 });
    await expect(page.locator('.stats-bar')).toBeVisible();
    await pause(page, LONG_PAUSE);

    // Scroll through collectors
    const collectorTable = page.locator('.collectors-table');
    await collectorTable.evaluate((el) => el.scrollTo(0, el.scrollHeight));
    await pause(page);
    await collectorTable.evaluate((el) => el.scrollTo(0, 0));
    await pause(page);

    // ── 8. PHASES — 8 phases + presets ──
    await navigateTo(page, 'Phases', '/phases');
    await expect(page.locator('.phase-table')).toBeVisible({ timeout: 10_000 });
    await pause(page, LONG_PAUSE);

    // Expand a few presets
    const presetPanels = page.locator('mat-accordion mat-expansion-panel');
    await expect(presetPanels.first()).toBeVisible({ timeout: 10_000 });
    const presetCount = await presetPanels.count();
    for (let i = 0; i < Math.min(3, presetCount); i++) {
      await presetPanels.nth(i).locator('mat-expansion-panel-header').click();
      await pause(page);
    }
    for (let i = Math.min(3, presetCount) - 1; i >= 0; i--) {
      await presetPanels.nth(i).locator('mat-expansion-panel-header').click();
      await pause(page, 400);
    }

    // ════════════════════════════════════════════════
    // ACT 2: RUN FULL PIPELINE (Discover → Implement)
    // ════════════════════════════════════════════════

    await navigateTo(page, 'Run Pipeline', '/run');
    await expect(page.locator('.config-card')).toBeVisible({ timeout: 10_000 });
    await pause(page);

    // Show tabs: Run Preset + Run Custom Phases
    const runTabs = page.locator('.mat-mdc-tab');
    await expect(runTabs.first()).toBeVisible();
    await pause(page);

    // Show Custom Phases tab (8 checkboxes)
    if ((await runTabs.count()) >= 2) {
      await runTabs.nth(1).click();
      await pause(page, LONG_PAUSE);
      // Show checkboxes
      const checkboxes = page.locator('mat-checkbox');
      if (await checkboxes.first().isVisible({ timeout: 5_000 }).catch(() => false)) {
        await pause(page, LONG_PAUSE);
      }
      // Back to Preset tab
      await runTabs.first().click();
      await pause(page);
    }

    // Show Advanced Options (Input Files + Environment Overrides)
    const advancedPanel = page.locator('mat-expansion-panel-header:has-text("Advanced Options")');
    if (await advancedPanel.isVisible().catch(() => false)) {
      await advancedPanel.click();
      await pause(page, LONG_PAUSE);

      // Show Input Files section
      const inputSection = page.locator('.advanced-section-title:has-text("Input Files")');
      if (await inputSection.isVisible().catch(() => false)) {
        await pause(page, LONG_PAUSE);
      }

      // Show Environment Overrides
      const envSection = page.locator('.advanced-section-title:has-text("Environment")');
      if (await envSection.isVisible().catch(() => false)) {
        await pause(page, LONG_PAUSE);
      }

      // Collapse Advanced Options
      await advancedPanel.click();
      await pause(page, 600);
    }

    // Open preset dropdown
    await page.locator('mat-select').first().click();
    await expect(page.locator('mat-option').first()).toBeVisible({ timeout: 10_000 });
    await pause(page, LONG_PAUSE);

    // Select "Discover → Implement" preset
    const developOption = page.locator('mat-option:has-text("Implement")');
    const hasDevelop = await developOption.first().isVisible().catch(() => false);
    if (hasDevelop) {
      await developOption.first().click();
    } else {
      const fullOption = page.locator('mat-option:has-text("Full Pipeline")');
      if (await fullOption.isVisible().catch(() => false)) {
        await fullOption.click();
      } else {
        const allOptions = page.locator('mat-option');
        await allOptions.last().click();
      }
    }
    await pause(page, LONG_PAUSE);

    // Phase chips
    const chips = page.locator('.phase-chips mat-chip');
    await expect(chips.first()).toBeVisible({ timeout: 5_000 });
    await pause(page, LONG_PAUSE);

    // START THE PIPELINE
    const runBtn = page.locator('.config-card button:has-text("Run Pipeline")');
    await expect(runBtn).toBeEnabled({ timeout: 5_000 });
    await runBtn.click();
    await pause(page, LONG_PAUSE);

    // --- OBSERVE LIVE EXECUTION ---

    // Status card — running
    const statusRunning = page.locator('.status-card.state-running');
    if (await statusRunning.isVisible({ timeout: 15_000 }).catch(() => false)) {
      await pause(page, LONG_PAUSE);
    }

    // Progress bar
    const progressBar = page.locator('mat-progress-bar.run-progress');
    if (await progressBar.isVisible({ timeout: 10_000 }).catch(() => false)) {
      await pause(page, LONG_PAUSE);
    }

    // Stepper — active phase
    const stepRunning = page.locator('.stepper-step.step-running');
    if (await stepRunning.first().isVisible({ timeout: 10_000 }).catch(() => false)) {
      await pause(page, LONG_PAUSE);
    }

    // Live log stream
    const logViewport = page.locator('.log-viewport');
    const hasLogs = await logViewport.isVisible({ timeout: 20_000 }).catch(() => false);
    if (hasLogs) {
      await expect(page.locator('.log-viewport .log-line').first()).toBeVisible({ timeout: 20_000 });
      await pause(page, READ_PAUSE);

      // Show logs flowing in
      for (let i = 0; i < 5; i++) {
        await logViewport.evaluate((el) => el.scrollTo(0, el.scrollHeight));
        await pause(page, READ_PAUSE);
      }
    }

    // Metrics bar
    const metricsBarEl = page.locator('.metrics-bar, .run-metrics');
    if (await metricsBarEl.first().isVisible().catch(() => false)) {
      await pause(page, LONG_PAUSE);
    }

    // WAIT FOR COMPLETION (up to 30 min, poll every 30s with log scroll)
    const completed = page.locator('.status-card.state-completed');
    const failed = page.locator('.status-card.state-failed');
    const maxWaitMs = 1_800_000;
    const pollMs = 30_000;
    const startTime = Date.now();
    let pipelineDone = false;

    while (Date.now() - startTime < maxWaitMs) {
      const isDone =
        (await completed.isVisible().catch(() => false)) ||
        (await failed.isVisible().catch(() => false));
      if (isDone) {
        pipelineDone = true;
        break;
      }
      if (hasLogs) {
        await logViewport.evaluate((el) => el.scrollTo(0, el.scrollHeight));
      }
      await pause(page, pollMs);
    }

    if (pipelineDone) {
      await pause(page, READ_PAUSE);
    }

    // Celebration banner
    const banner = page.locator('.celebration-banner');
    if (await banner.isVisible().catch(() => false)) {
      await pause(page, READ_PAUSE);
    }

    // Final log scroll
    if (hasLogs) {
      await logViewport.evaluate((el) => el.scrollTo(0, el.scrollHeight));
      await pause(page, LONG_PAUSE);
    }

    // ════════════════════════════════════════════════
    // ACT 3: REVIEW ALL GENERATED ARTIFACTS
    // ════════════════════════════════════════════════

    // ── 9. DASHBOARD — show completed phases (green) ──
    await navigateTo(page, 'Dashboard', '/dashboard');
    await expect(page.locator('.phase-grid')).toBeVisible({ timeout: 10_000 });
    await pause(page, READ_PAUSE);

    const completedPhases = page.locator('.phase-completed');
    if ((await completedPhases.count()) > 0) {
      await pause(page, READ_PAUSE);
    }

    // ── 10. KNOWLEDGE — open ALL architecture docs ──
    await navigateTo(page, 'Knowledge', '/knowledge');

    // Stats bar
    if (await page.locator('.stats-bar').isVisible({ timeout: 10_000 }).catch(() => false)) {
      await pause(page, LONG_PAUSE);
    }

    // ARCHITECTURE DOCS — cycle ALL groups, open docs (max 5 per group, first one slow, rest fast)
    const groupChips = page.locator('.group-chip');
    if (await groupChips.first().isVisible({ timeout: 10_000 }).catch(() => false)) {
      const gCount = await groupChips.count();
      for (let g = 0; g < gCount; g++) {
        await groupChips.nth(g).click();
        await pause(page);

        const docRows = page.locator('.doc-row');
        const docCount = await docRows.count();
        const maxDocs = Math.min(docCount, 5);
        for (let d = 0; d < maxDocs; d++) {
          await docRows.nth(d).click();
          const viewer = page.locator('.viewer-panel');
          if (await viewer.isVisible({ timeout: 5_000 }).catch(() => false)) {
            // First doc per group: slow scroll; rest: fast
            const viewerSel = '.viewer-panel .viewer-body, .viewer-panel .rendered-content, .viewer-panel .source-content';
            if (d === 0) {
              await scrollThrough(page, viewerSel);
            } else {
              await scrollThrough(page, viewerSel, true);
            }

            const closeBtn = page.locator('.viewer-panel button:has(mat-icon:has-text("close"))');
            if (await closeBtn.isVisible().catch(() => false)) {
              await closeBtn.click();
              await pause(page, 400);
            }
          }
        }
      }
    }

    // PIPELINE DATA — expand ALL groups, open first 2 files each
    const dgHeaders = page.locator('.dg-header');
    const dgCount = await dgHeaders.count();
    for (let i = 0; i < dgCount; i++) {
      await dgHeaders.nth(i).click();
      await pause(page, 800);

      const dgFiles = page.locator('.dg-files:visible .dg-file');
      const fileCount = await dgFiles.count();
      for (let f = 0; f < Math.min(fileCount, 2); f++) {
        await dgFiles.nth(f).click();
        const viewer = page.locator('.viewer-panel');
        if (await viewer.isVisible({ timeout: 5_000 }).catch(() => false)) {
          await scrollThrough(page, '.viewer-panel .viewer-body, .viewer-panel .rendered-content, .viewer-panel .source-content', true);
          const closeBtn = page.locator('.viewer-panel button:has(mat-icon:has-text("close"))');
          if (await closeBtn.isVisible().catch(() => false)) {
            await closeBtn.click();
            await pause(page, 400);
          }
        }
      }

      // Collapse group
      await dgHeaders.nth(i).click();
      await pause(page, 300);
    }

    // ── 11. REPORTS — all tabs, expand everything ──
    await navigateTo(page, 'Reports', '/reports');
    await expect(page.locator('mat-tab-group')).toBeVisible({ timeout: 10_000 });
    await pause(page, LONG_PAUSE);

    // Architecture tab — expand doc groups, preview files
    const archTab = page.getByRole('tab', { name: /Architecture/i });
    if (await archTab.isVisible().catch(() => false)) {
      await archTab.click();
      await pause(page);

      const docFileCards = page.locator('.doc-file-card');
      const archCardCount = await docFileCards.count();
      for (let i = 0; i < Math.min(archCardCount, 5); i++) {
        await docFileCards.nth(i).click();
        const preview = page.locator('.doc-preview').first();
        if (await preview.isVisible({ timeout: 5_000 }).catch(() => false)) {
          await pause(page, READ_PAUSE);
          await preview.evaluate((el) => el.scrollTo(0, el.scrollHeight / 2));
          await pause(page, LONG_PAUSE);
        }
      }
    }

    // Development Plans tab
    const plansTab = page.getByRole('tab', { name: /Development Plans/i });
    if (await plansTab.isVisible().catch(() => false)) {
      await plansTab.click();
      await pause(page, LONG_PAUSE);

      const planPanels = page.locator('mat-expansion-panel');
      const planCount = await planPanels.count();
      for (let i = 0; i < Math.min(planCount, 3); i++) {
        const header = planPanels.nth(i).locator('mat-expansion-panel-header');
        if (await header.isVisible().catch(() => false)) {
          await header.click();
          await pause(page, READ_PAUSE);
          const planBody = page.locator('.plan-body, .plan-content').first();
          if (await planBody.isVisible().catch(() => false)) {
            await planBody.evaluate((el) => el.scrollTo(0, el.scrollHeight / 2));
            await pause(page, LONG_PAUSE);
          }
        }
      }
    }

    // Code Generation tab
    const codegenTab = page.getByRole('tab', { name: /Code Generation/i });
    if (await codegenTab.isVisible().catch(() => false)) {
      await codegenTab.click();
      await pause(page, LONG_PAUSE);

      const codegenPanels = page.locator('mat-expansion-panel');
      const codegenCount = await codegenPanels.count();
      for (let i = 0; i < Math.min(codegenCount, 3); i++) {
        const header = codegenPanels.nth(i).locator('mat-expansion-panel-header');
        if (await header.isVisible().catch(() => false)) {
          await header.click();
          await pause(page, READ_PAUSE);
        }
      }
    }

    // Git Branches tab
    const branchesTab = page.getByRole('tab', { name: /Git Branches/i });
    if (await branchesTab.isVisible().catch(() => false)) {
      await branchesTab.click();
      await pause(page, LONG_PAUSE);
      const branchGrid = page.locator('.branches-grid');
      if (await branchGrid.isVisible({ timeout: 5_000 }).catch(() => false)) {
        await pause(page, READ_PAUSE);
      }
    }

    // ── 12. METRICS ──
    await navigateTo(page, 'Metrics', '/metrics');
    const metricsContent = page.locator('.stats-bar, .empty-state');
    await expect(metricsContent.first()).toBeVisible({ timeout: 10_000 });
    await pause(page, LONG_PAUSE);

    const metricsTable = page.locator('.metrics-table');
    if (await metricsTable.isVisible().catch(() => false)) {
      await pause(page, LONG_PAUSE);
      await metricsTable.evaluate((el) => el.scrollTo(0, el.scrollHeight));
      await pause(page, LONG_PAUSE);
    }

    // ── 13. LOGS — show multiple log files ──
    await navigateTo(page, 'Logs', '/logs');
    await expect(page.locator('.toolbar-card')).toBeVisible();

    // Open file selector
    await page.locator('mat-select').click();
    const logOptions = page.locator('mat-option');
    await expect(logOptions.first()).toBeVisible({ timeout: 10_000 });
    await pause(page, LONG_PAUSE);

    // Cycle through log files
    const logFileCount = await logOptions.count();
    for (let i = 0; i < Math.min(logFileCount, 3); i++) {
      await logOptions.nth(i).click();
      await pause(page);

      const logViewer = page.locator('.log-viewer');
      if (await logViewer.isVisible({ timeout: 5_000 }).catch(() => false)) {
        await pause(page, LONG_PAUSE);
        await logViewer.evaluate((el) => el.scrollTo(0, el.scrollHeight));
        await pause(page, LONG_PAUSE);
      }

      if (i < Math.min(logFileCount, 3) - 1) {
        await page.locator('mat-select').click();
        await expect(logOptions.first()).toBeVisible({ timeout: 5_000 });
        await pause(page, 600);
      }
    }

    // ── 14. HISTORY — show the completed run ──
    await navigateTo(page, 'History', '/history');
    const filterBar = page.locator('.filter-bar');
    await expect(filterBar).toBeVisible();
    await pause(page, LONG_PAUSE);

    await page.waitForTimeout(2000);
    const historyContent = page.locator('.history-table, .empty-state');
    if (await historyContent.first().isVisible().catch(() => false)) {
      await pause(page, LONG_PAUSE);
    }

    // Cycle filter chips
    const filterChips = page.locator('.filter-chip');
    const chipFilterCount = await filterChips.count();
    for (let i = 0; i < chipFilterCount; i++) {
      await filterChips.nth(i).click();
      await pause(page);
    }

    // ════════════════════════════════════════════════
    // ACT 4: RESPONSIVE DESIGN
    // ════════════════════════════════════════════════
    await navigateTo(page, 'Dashboard', '/dashboard');

    // Desktop full
    await page.setViewportSize({ width: 1500, height: 900 });
    await pause(page, LONG_PAUSE);

    // Tablet rail
    await page.setViewportSize({ width: 1200, height: 900 });
    await pause(page, LONG_PAUSE);

    // Mobile overlay
    await page.setViewportSize({ width: 900, height: 900 });
    await pause(page, LONG_PAUSE);

    // Open overlay sidenav
    const menuBtn = page.locator('mat-toolbar button[mat-icon-button]');
    if (await menuBtn.isVisible().catch(() => false)) {
      await menuBtn.click();
      await pause(page, LONG_PAUSE);
    }

    // Back to desktop
    await page.setViewportSize({ width: 1920, height: 1080 });
    await pause(page, LONG_PAUSE);

    // ════════════════════════════════════════════════
    // FIN — closing shot
    // ════════════════════════════════════════════════
    await page.goto('/dashboard');
    await expect(page.locator('.hero')).toBeVisible({ timeout: 10_000 });
    await pause(page, READ_PAUSE);
  });
});
