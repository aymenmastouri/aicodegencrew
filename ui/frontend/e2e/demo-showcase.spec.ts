import { test, expect, Page } from '@playwright/test';

/**
 * Demo Showcase — FULL SCENARIO for AI Challenge presentation.
 *
 * Flow: Reset All → Empty App Tour → Fill Settings → Upload Task XML →
 *       Run Discover→Implement → Review ALL artifacts → History → Logs → Metrics
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
    test.setTimeout(7_200_000); // 2h

    // ════════════════════════════════════════════════
    // PROLOGUE: RESET EVERYTHING — clean slate
    // ════════════════════════════════════════════════

    // Open dashboard first so the reset is visible on-screen
    await page.goto('/dashboard');
    await expect(page.locator('.hero, mat-toolbar').first()).toBeVisible({ timeout: 15_000 });
    await pause(page, LONG_PAUSE);

    // Call reset API — clears all phase knowledge + pipeline state
    // Retry up to 3 times (409 = pipeline still running from a previous test)
    for (let attempt = 0; attempt < 3; attempt++) {
      const resetResp = await page.request.post('http://localhost:4200/api/reset/all');
      if (resetResp.ok()) break;
      if (resetResp.status() === 409 && attempt < 2) {
        await pause(page, 10_000);
        continue;
      }
      break; // non-409 or last attempt — continue anyway
    }
    await pause(page, LONG_PAUSE);

    // Also clear Discover phase state for a fully clean slate
    await page
      .request.post('http://localhost:4200/api/reset/clear-state', {
        data: { phase_ids: ['discover'], cascade: false },
      })
      .catch(() => {});

    // Reload the page so Angular reflects the clean state visually
    await page.reload();
    await expect(page.locator('.hero, mat-toolbar').first()).toBeVisible({ timeout: 15_000 });
    await pause(page, LONG_PAUSE);

    // ════════════════════════════════════════════════
    // ACT 1: SHOW THE EMPTY APP
    // ════════════════════════════════════════════════

    // ── 1. DASHBOARD — all phases pending ──
    // Clear onboarding-dismissed flag so the "Getting Started" card is visible
    await page.evaluate(() => localStorage.removeItem('onboarding_dismissed'));
    await page.goto('/dashboard');
    await expect(page.locator('.hero')).toBeVisible({ timeout: 15_000 });

    // Slow down on hero so first-time viewers can read "AI-Powered Development Lifecycle Automation"
    await pause(page, READ_PAUSE);
    await page.evaluate(() => window.scrollTo(0, 300));
    await pause(page, LONG_PAUSE);
    await page.evaluate(() => window.scrollTo(0, 0));
    await pause(page, LONG_PAUSE);

    // ── GETTING STARTED card — 4 setup steps for first-time viewers ──
    // Shows: Configure repository → Configure LLM → Upload task files → Run first pipeline
    const onboardingCard = page.locator('.onboarding-card');
    if (await onboardingCard.isVisible({ timeout: 5_000 }).catch(() => false)) {
      await onboardingCard.scrollIntoViewIfNeeded();
      await pause(page, READ_PAUSE);
      // Scroll slowly through all 4 steps
      const steps = onboardingCard.locator('.onboarding-step');
      const stepCount = await steps.count();
      for (let s = 0; s < stepCount; s++) {
        await steps.nth(s).scrollIntoViewIfNeeded();
        await pause(page, PAUSE);
      }
      await pause(page, LONG_PAUSE);
      await page.evaluate(() => window.scrollTo(0, 0));
      await pause(page);
    }

    // Phase grid — 8 cards, all should be pending/idle (clean slate)
    await expect(page.locator('.phase-grid')).toBeVisible({ timeout: 10_000 });
    await expect(page.locator('.phase-card')).toHaveCount(8);
    // Scroll slowly through the phase cards so audience sees all 8 phases
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight / 2));
    await pause(page, LONG_PAUSE);
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await pause(page, READ_PAUSE);
    await page.evaluate(() => window.scrollTo(0, 0));
    await pause(page);

    // Quick actions
    await expect(page.locator('.action-card').first()).toBeVisible();
    await pause(page);

    // Health pills
    const statPill = page.locator('.stat-pill').first();
    if (await statPill.isVisible().catch(() => false)) {
      await pause(page);
    }

    // ── 2. SIDENAV — 12 items (incl. MCP Servers) ──
    const navItems = page.locator('mat-nav-list a[mat-list-item]');
    await expect(navItems).toHaveCount(12);
    await pause(page, LONG_PAUSE);

    // ── 3. KNOWLEDGE — empty state (emphasise: nothing here YET) ──
    await navigateTo(page, 'Knowledge', '/knowledge');
    const kbEmpty = page.locator('.empty-state');
    const kbStats = page.locator('.stats-bar');
    await expect(kbEmpty.or(kbStats).first()).toBeVisible({ timeout: 10_000 });
    // Pause long enough for the audience to register: knowledge base is empty right now.
    // After the pipeline run this page will be filled with AI-generated documentation.
    await pause(page, READ_PAUSE);
    await pause(page, LONG_PAUSE);

    // ── 4. REPORTS — empty state ──
    await navigateTo(page, 'Reports', '/reports');
    await expect(page.locator('mat-tab-group, .empty-state').first()).toBeVisible({ timeout: 10_000 });
    await pause(page, LONG_PAUSE);

    // ── 5. SETTINGS — browse all tabs (read-only, do not modify) ──
    await navigateTo(page, 'Settings', '/settings');
    const settingsTabs = page.locator('.mat-mdc-tab');
    await expect(settingsTabs.first()).toBeVisible({ timeout: 10_000 });
    await pause(page, LONG_PAUSE);

    // Cycle through all tabs so the audience sees every settings category
    const settingsTabCount = await settingsTabs.count();
    for (let i = 0; i < settingsTabCount; i++) {
      await settingsTabs.nth(i).click();
      await pause(page, LONG_PAUSE);
      // Scroll tab content so all fields are visible
      await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight / 2));
      await pause(page, PAUSE);
      await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
      await pause(page, PAUSE);
      await page.evaluate(() => window.scrollTo(0, 0));
      await pause(page, 400);
    }
    // Return to first tab
    await settingsTabs.first().click();
    await pause(page);

    // ════════════════════════════════════════════════
    // ACT 2: INPUT FILES — upload task XML via "click to browse"
    // ════════════════════════════════════════════════

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
      await card.scrollIntoViewIfNeeded();
      await pause(page);

      const fileItems = card.locator('.file-item, .file-row, .file-entry');
      if ((await fileItems.count()) > 0) {
        await pause(page, LONG_PAUSE);
      }
    }
    await page.evaluate(() => window.scrollTo(0, 0));
    await pause(page);

    // ── 6b. UPLOAD JIRA TASK FILE via "click to browse" ──
    const taskCard = page.locator('.category-card:has-text("Task Files")');
    await taskCard.scrollIntoViewIfNeeded();
    await pause(page, LONG_PAUSE);

    // Clean up any leftover BNUVZ files from previous runs
    const existingFiles = taskCard.locator('.file-row:has-text("BNUVZ-12529")');
    let leftoverCount = await existingFiles.count();
    while (leftoverCount > 0) {
      await existingFiles.first().locator('button').click();
      await pause(page, PAUSE);
      leftoverCount = await existingFiles.count();
    }

    // VISUAL UPLOAD: click on "click to browse" in the drop zone
    // This triggers the native file chooser (visible in demo recording)
    const dropZone = taskCard.locator('.drop-zone');
    await dropZone.scrollIntoViewIfNeeded();
    await pause(page, LONG_PAUSE);

    const [fileChooser] = await Promise.all([
      page.waitForEvent('filechooser'),
      dropZone.click(),
    ]);
    await fileChooser.setFiles('C:\\projects\\BNUVZ-12529.xml');

    // Wait for upload success snackbar
    const uploadSnackbar = page.locator('.mat-mdc-snack-bar-container');
    await expect(uploadSnackbar).toBeVisible({ timeout: 10_000 });
    await pause(page, READ_PAUSE);

    // Show uploaded file in the list
    const uploadedFile = taskCard.locator('.file-name:has-text("BNUVZ-12529.xml")');
    await expect(uploadedFile).toBeVisible({ timeout: 5_000 });
    await pause(page, LONG_PAUSE);

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

    // ── 8. PHASES — 8 phases + types (pipeline/crew/hybrid) + presets ──
    await navigateTo(page, 'Phases', '/phases');
    await expect(page.locator('.phase-table')).toBeVisible({ timeout: 10_000 });
    // Pause so viewers can read the phase table (type badges: pipeline / crew / hybrid)
    await pause(page, READ_PAUSE);
    // Scroll slowly through the full table
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight / 2));
    await pause(page, LONG_PAUSE);
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await pause(page, LONG_PAUSE);
    await page.evaluate(() => window.scrollTo(0, 0));
    await pause(page, LONG_PAUSE);

    // Expand all presets to show them
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

    // ── 8b. MCP SERVERS ──
    await navigateTo(page, 'MCP Servers', '/mcps');
    const mcpGrid = page.locator('.grid');
    if (await mcpGrid.isVisible({ timeout: 10_000 }).catch(() => false)) {
      await pause(page, LONG_PAUSE);
      await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight / 2));
      await pause(page, LONG_PAUSE);
      await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
      await pause(page, LONG_PAUSE);
      await page.evaluate(() => window.scrollTo(0, 0));
      await pause(page);
    }

    // ════════════════════════════════════════════════
    // ACT 4: RUN FULL PIPELINE (Discover → Implement)
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

      const inputSection = page.locator('.advanced-section-title:has-text("Input Files")');
      if (await inputSection.isVisible().catch(() => false)) {
        await pause(page, LONG_PAUSE);
      }

      const envSection = page.locator('.advanced-section-title:has-text("Environment")');
      if (await envSection.isVisible().catch(() => false)) {
        await pause(page, LONG_PAUSE);
      }

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

    // ── LIVE DASHBOARD: navigate there to show phases switching to "running" / "completed" ──
    // This is the most visually impressive moment for first-time viewers.
    await navigateTo(page, 'Dashboard', '/dashboard');
    await expect(page.locator('.phase-grid')).toBeVisible({ timeout: 10_000 });
    await pause(page, READ_PAUSE);
    // Scroll through phase cards to show live status
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight / 2));
    await pause(page, LONG_PAUSE);
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await pause(page, LONG_PAUSE);
    await page.evaluate(() => window.scrollTo(0, 0));
    await pause(page, LONG_PAUSE);
    // Wait up to 20s for at least one phase to show "running" or "completed" on the grid
    // Dashboard uses class="phase-card phase-{status}" pattern
    const livePhase = page.locator('.phase-card.phase-running, .phase-card.phase-completed');
    await livePhase.first().isVisible({ timeout: 20_000 }).catch(() => {});
    await pause(page, READ_PAUSE);
    // Navigate back to Run Pipeline to monitor the log stream
    await navigateTo(page, 'Run Pipeline', '/run');
    await pause(page, LONG_PAUSE);

    // Live log stream
    const logViewport = page.locator('.log-viewport');
    const hasLogs = await logViewport.isVisible({ timeout: 20_000 }).catch(() => false);
    if (hasLogs) {
      await expect(page.locator('.log-viewport .log-line').first()).toBeVisible({ timeout: 20_000 });
      await pause(page, READ_PAUSE);

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

    // WAIT FOR COMPLETION — poll backend API directly (survives page navigation)
    const maxWaitMs = 7_200_000; // 2h
    const pollMs = 30_000;
    const startTime = Date.now();
    let pipelineDone = false;

    while (Date.now() - startTime < maxWaitMs) {
      // Check pipeline state via API — reliable regardless of which page is shown
      const resp = await page.request.get('http://localhost:4200/api/pipeline/status').catch(() => null);
      if (resp && resp.ok()) {
        const data = await resp.json().catch(() => ({}));
        const terminalStates = ['completed', 'failed', 'cancelled'];
        if (terminalStates.includes(data.state)) {
          pipelineDone = data.state === 'completed';
          break;
        }
      }
      // Also scroll log if still visible
      const lv = page.locator('.log-viewport');
      if (await lv.isVisible().catch(() => false)) {
        await lv.evaluate((el) => el.scrollTo(0, el.scrollHeight));
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

    // Final log scroll — use a fresh locator (navigated away and back, old ref is stale)
    const freshLogViewport = page.locator('.log-viewport');
    if (await freshLogViewport.isVisible().catch(() => false)) {
      await freshLogViewport.evaluate((el) => el.scrollTo(0, el.scrollHeight));
      await pause(page, LONG_PAUSE);
    }

    // ════════════════════════════════════════════════
    // ACT 5: REVIEW ALL GENERATED ARTIFACTS
    // ════════════════════════════════════════════════

    // ── 9. DASHBOARD — show completed phases (green) ──
    await navigateTo(page, 'Dashboard', '/dashboard');
    await expect(page.locator('.phase-grid')).toBeVisible({ timeout: 10_000 });
    await pause(page, READ_PAUSE);

    const completedPhases = page.locator('.phase-completed');
    if ((await completedPhases.count()) > 0) {
      await pause(page, READ_PAUSE);
    }

    // ── 10. KNOWLEDGE — open EVERY architecture document ──
    await navigateTo(page, 'Knowledge', '/knowledge');

    if (await page.locator('.stats-bar').isVisible({ timeout: 10_000 }).catch(() => false)) {
      await pause(page, LONG_PAUSE);
    }

    // ARCHITECTURE DOCS — cycle ALL groups, open EVERY document
    const groupChips = page.locator('.group-chip');
    if (await groupChips.first().isVisible({ timeout: 10_000 }).catch(() => false)) {
      const gCount = await groupChips.count();
      for (let g = 0; g < gCount; g++) {
        await groupChips.nth(g).click();
        await pause(page);

        const docRows = page.locator('.doc-row');
        const docCount = await docRows.count();
        // Open max 4 documents per group (enough to demonstrate, keeps demo length sane)
        for (let d = 0; d < Math.min(docCount, 4); d++) {
          await docRows.nth(d).click();
          const viewer = page.locator('.viewer-panel');
          if (await viewer.isVisible({ timeout: 5_000 }).catch(() => false)) {
            const viewerSel =
              '.viewer-panel .viewer-body, .viewer-panel .rendered-content, .viewer-panel .source-content';
            // First doc per group: slow scroll; rest: fast
            if (d === 0) {
              await scrollThrough(page, viewerSel);
            } else {
              await scrollThrough(page, viewerSel, true);
            }

            const closeBtn = page.locator(
              '.viewer-panel button:has(mat-icon:has-text("close"))',
            );
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
          await scrollThrough(
            page,
            '.viewer-panel .viewer-body, .viewer-panel .rendered-content, .viewer-panel .source-content',
            true,
          );
          const closeBtn = page.locator(
            '.viewer-panel button:has(mat-icon:has-text("close"))',
          );
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
    // After a long pipeline run, the backend reads 30+ files — give it 30s
    await expect(page.locator('mat-tab-group')).toBeVisible({ timeout: 30_000 });
    await pause(page, LONG_PAUSE);

    // Architecture tab — expand doc groups, preview ALL files
    const archTab = page.getByRole('tab', { name: /Architecture/i });
    if (await archTab.isVisible().catch(() => false)) {
      await archTab.click();
      await pause(page);

      const docGroupHeaders = page.locator('.doc-group-header');
      const groupCount = await docGroupHeaders.count();
      for (let g = 0; g < groupCount; g++) {
        await docGroupHeaders.nth(g).click();
        await pause(page);

        const docFileCards = page.locator('.doc-group-files:visible .doc-file-card');
        const cardCount = await docFileCards.count();
        // Show max 4 documents per group (representative sample)
        for (let i = 0; i < Math.min(cardCount, 4); i++) {
          await docFileCards.nth(i).click();
          const preview = page.locator('.doc-preview').first();
          if (await preview.isVisible({ timeout: 5_000 }).catch(() => false)) {
            await pause(page, g === 0 && i === 0 ? READ_PAUSE : PAUSE);
            await preview.evaluate((el) => el.scrollTo(0, el.scrollHeight / 2));
            await pause(page, LONG_PAUSE);
          }
        }

        // Collapse group before opening next
        await docGroupHeaders.nth(g).click();
        await pause(page, 400);
      }
    }

    // Development Plans tab — expand and scroll through EVERY plan completely
    const plansTab = page.getByRole('tab', { name: /Development Plans/i });
    if (await plansTab.isVisible().catch(() => false)) {
      await plansTab.click();
      await pause(page, LONG_PAUSE);

      const planPanels = page.locator('mat-expansion-panel');
      const planCount = await planPanels.count();
      // Show max 3 plans (representative sample)
      for (let i = 0; i < Math.min(planCount, 3); i++) {
        const header = planPanels.nth(i).locator('mat-expansion-panel-header');
        if (await header.isVisible().catch(() => false)) {
          await header.click();
          await pause(page, READ_PAUSE);

          // Scroll the full plan body so every step is visible
          const planBody = page.locator('.plan-body, .plan-content, mat-expansion-panel-body').nth(i);
          if (await planBody.isVisible({ timeout: 3_000 }).catch(() => false)) {
            await planBody.evaluate((el) => el.scrollTo(0, 0));
            await pause(page, PAUSE);
            await planBody.evaluate((el) => el.scrollTo(0, el.scrollHeight / 3));
            await pause(page, PAUSE);
            await planBody.evaluate((el) => el.scrollTo(0, (el.scrollHeight * 2) / 3));
            await pause(page, PAUSE);
            await planBody.evaluate((el) => el.scrollTo(0, el.scrollHeight));
            await pause(page, READ_PAUSE);
          } else {
            // plan content may not be scrollable — just wait for audience to read
            await pause(page, READ_PAUSE);
          }

          // Collapse before opening the next one (keeps layout clean)
          await header.click();
          await pause(page, 600);
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

    // ── 11b. MCP SERVERS (post-run) ──
    await navigateTo(page, 'MCP Servers', '/mcps');
    if (await page.locator('.grid').isVisible({ timeout: 10_000 }).catch(() => false)) {
      await pause(page, LONG_PAUSE);
    }

    // ════════════════════════════════════════════════
    // ACT 6: FINALE — HISTORY → LOGS → METRICS
    // ════════════════════════════════════════════════

    // ── 12. HISTORY — show the completed run with ALL phase details ──
    await navigateTo(page, 'History', '/history');
    const filterBar = page.locator('.filter-bar, .history-filters');
    await expect(filterBar.first()).toBeVisible({ timeout: 10_000 });
    await pause(page, LONG_PAUSE);

    // Wait for history table to load
    await page.waitForTimeout(2000);
    const historyContent = page.locator('.history-table, .run-card, .run-row, .empty-state');
    if (await historyContent.first().isVisible({ timeout: 5_000 }).catch(() => false)) {
      await pause(page, LONG_PAUSE);
    }

    // Expand the first (most recent) run entry
    const historyRows = page.locator('.table-row');
    if ((await historyRows.count()) > 0) {
      await historyRows.first().click();
      await pause(page, READ_PAUSE);

      // Scroll slowly through ALL phase details in the detail-panel
      const detailPanel = page.locator('.detail-panel');
      if (await detailPanel.isVisible({ timeout: 5_000 }).catch(() => false)) {
        await detailPanel.evaluate((el) => el.scrollTo(0, 0));
        await pause(page, LONG_PAUSE);
        await detailPanel.evaluate((el) => el.scrollTo(0, el.scrollHeight / 3));
        await pause(page, LONG_PAUSE);
        await detailPanel.evaluate((el) => el.scrollTo(0, (el.scrollHeight * 2) / 3));
        await pause(page, LONG_PAUSE);
        await detailPanel.evaluate((el) => el.scrollTo(0, el.scrollHeight));
        await pause(page, READ_PAUSE);
      } else {
        // Fallback: scroll the page
        await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight / 2));
        await pause(page, LONG_PAUSE);
        await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
        await pause(page, READ_PAUSE);
        await page.evaluate(() => window.scrollTo(0, 0));
        await pause(page);
      }
    }

    // ── 13. LOGS — show multiple log files ──
    await navigateTo(page, 'Logs', '/logs');
    await expect(page.locator('.toolbar-card')).toBeVisible();

    // Open file selector
    await page.locator('mat-select').click();
    const logOptions = page.locator('mat-option');
    await expect(logOptions.first()).toBeVisible({ timeout: 10_000 });
    await pause(page, LONG_PAUSE);

    // Cycle through log files (show all, max 3 for demo)
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

    // ── 14. METRICS — final stats view ──
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

    // ════════════════════════════════════════════════
    // EPILOGUE: CLEANUP — delete inputs + reset all
    // ════════════════════════════════════════════════

    // Delete uploaded BNUVZ file(s) from Task Files
    await page.goto('/inputs');
    await expect(page.locator('.category-card')).toHaveCount(4, { timeout: 10_000 });
    await pause(page);

    const cleanupTaskCard = page.locator('.category-card:has-text("Task Files")');
    const cleanupFiles = cleanupTaskCard.locator('.file-row:has-text("BNUVZ-12529")');
    let cleanupCount = await cleanupFiles.count();
    while (cleanupCount > 0) {
      await cleanupFiles.first().locator('button').click();
      await pause(page, PAUSE);
      cleanupCount = await cleanupFiles.count();
    }
    await pause(page);

    // Reset all phase data
    await page.request.post('http://localhost:4200/api/reset/all').catch(() => {});
    await pause(page, LONG_PAUSE);

    // ════════════════════════════════════════════════
    // FIN — closing shot on Dashboard
    // ════════════════════════════════════════════════
    await page.goto('/dashboard');
    await expect(page.locator('.hero')).toBeVisible({ timeout: 10_000 });
    await pause(page, READ_PAUSE);
  });
});
