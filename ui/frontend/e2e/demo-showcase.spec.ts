import { test, expect, Page } from '@playwright/test';

/**
 * Demo Showcase — MANAGER EDITION
 *
 * Optimised for non-technical audience: shows business value & outcomes only.
 * No Settings, Collectors, Phases-config, MCP, Logs, Metrics, Pipeline-Data.
 *
 * Story:  Empty Tool → Upload Task → One-Click Run → Live Progress →
 *         Generated Architecture Docs → Development Plans → Generated Code →
 *         Git Branches → Audit History → Done!
 *
 * Run:    npx playwright test --project=demo e2e/demo-showcase.spec.ts
 * Video:  test-results/demo-showcase-Demo-Showcase-.../video.webm
 */

// ── Timing constants ──
const PAUSE      = 1200;   // normal beat
const LONG_PAUSE = 2000;   // let the eye settle
const READ_PAUSE = 3000;   // audience reads a heading / key content

async function pause(page: Page, ms = PAUSE) {
  await page.waitForTimeout(ms);
}

async function navigateTo(page: Page, label: string, url: string) {
  await page.locator(`a[mat-list-item]:has-text("${label}")`).click();
  await page.waitForURL(`**${url}`);
  await pause(page);
}

/** Scroll an element top → middle → bottom so the audience sees everything */
async function scrollThrough(page: Page, selector: string, speed: 'slow' | 'fast' = 'slow') {
  const el = page.locator(selector).first();
  if (await el.isVisible().catch(() => false)) {
    const ms = speed === 'fast' ? 600 : PAUSE;
    await el.evaluate((e) => e.scrollTo(0, e.scrollHeight / 2));
    await pause(page, ms);
    await el.evaluate((e) => e.scrollTo(0, e.scrollHeight));
    await pause(page, ms);
  }
}


test.describe('Demo Showcase', () => {
  test('Full app walkthrough', async ({ page }) => {
    test.setTimeout(7_200_000); // 2 h (pipeline can run long)

    // ════════════════════════════════════════════════════════════════
    //  PROLOGUE — silent reset (audience just sees the dashboard load)
    // ════════════════════════════════════════════════════════════════

    await page.goto('/dashboard');
    await expect(page.locator('.hero, mat-toolbar').first()).toBeVisible({ timeout: 15_000 });

    // Reset via API — invisible to the viewer
    for (let attempt = 0; attempt < 3; attempt++) {
      const resp = await page.request.post('http://localhost:4200/api/reset/all');
      if (resp.ok()) break;
      if (resp.status() === 409 && attempt < 2) { await pause(page, 10_000); continue; }
      break;
    }
    await page.request.post('http://localhost:4200/api/reset/clear-state', {
      data: { phase_ids: ['discover'], cascade: false },
    }).catch(() => {});

    await page.evaluate(() => localStorage.removeItem('onboarding_dismissed'));
    await page.reload();
    await expect(page.locator('.hero, mat-toolbar').first()).toBeVisible({ timeout: 15_000 });
    await pause(page, LONG_PAUSE);

    // ════════════════════════════════════════════════════════════════
    //  ACT 1 — THE EMPTY TOOL  (≈30 s)
    //  Goal: "This is what the tool looks like — nothing generated yet."
    // ════════════════════════════════════════════════════════════════

    // ── 1a. Hero — "AI-Powered Development Lifecycle Automation" ──
    await page.goto('/dashboard');
    await expect(page.locator('.hero')).toBeVisible({ timeout: 15_000 });
    await pause(page, READ_PAUSE);

    // ── 1b. Getting Started card — 4 simple steps ──
    const onboardingCard = page.locator('.onboarding-card');
    if (await onboardingCard.isVisible({ timeout: 5_000 }).catch(() => false)) {
      await onboardingCard.scrollIntoViewIfNeeded();
      await pause(page, READ_PAUSE);
    }

    // ── 1c. Phase grid — 8 phases, all pending ──
    await expect(page.locator('.phase-grid')).toBeVisible({ timeout: 10_000 });
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight / 2));
    await pause(page, LONG_PAUSE);
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await pause(page, LONG_PAUSE);
    await page.evaluate(() => window.scrollTo(0, 0));
    await pause(page);

    // ── 1d. Knowledge — empty (before vs. after) ──
    await navigateTo(page, 'Knowledge', '/knowledge');
    await expect(page.locator('.empty-state').or(page.locator('.stats-bar')).first())
      .toBeVisible({ timeout: 10_000 });
    await pause(page, READ_PAUSE);

    // ════════════════════════════════════════════════════════════════
    //  ACT 2 — UPLOAD A JIRA TASK  (≈20 s)
    //  Goal: "Just drag-and-drop a task file — that's the only input."
    // ════════════════════════════════════════════════════════════════

    await navigateTo(page, 'Input Files', '/inputs');
    await expect(page.locator('.category-card')).toHaveCount(4, { timeout: 10_000 });
    await pause(page, LONG_PAUSE);

    // Find the Task Files card
    const taskCard = page.locator('.category-card:has-text("Task Files")');
    await taskCard.scrollIntoViewIfNeeded();
    await pause(page, LONG_PAUSE);

    // Clean up leftovers silently
    const leftoverFiles = taskCard.locator('.file-row:has-text("BNUVZ-12529")');
    let leftoverCount = await leftoverFiles.count();
    while (leftoverCount > 0) {
      await leftoverFiles.first().locator('button').click();
      await pause(page, 600);
      leftoverCount = await leftoverFiles.count();
    }

    // Upload via file chooser
    const dropZone = taskCard.locator('.drop-zone');
    await dropZone.scrollIntoViewIfNeeded();
    await pause(page, LONG_PAUSE);

    const [fileChooser] = await Promise.all([
      page.waitForEvent('filechooser'),
      dropZone.click(),
    ]);
    await fileChooser.setFiles('C:\\projects\\BNUVZ-12529.xml');

    // Success feedback
    const snackbar = page.locator('.mat-mdc-snack-bar-container');
    await expect(snackbar).toBeVisible({ timeout: 10_000 });
    await pause(page, READ_PAUSE);

    // Confirm file appears in list
    await expect(taskCard.locator('.file-name:has-text("BNUVZ-12529.xml")'))
      .toBeVisible({ timeout: 5_000 });
    await pause(page, LONG_PAUSE);

    // ════════════════════════════════════════════════════════════════
    //  ACT 3 — ONE-CLICK PIPELINE START  (≈15 s)
    //  Goal: "Select a preset, click Run — that's it."
    // ════════════════════════════════════════════════════════════════

    await navigateTo(page, 'Run Pipeline', '/run');
    await expect(page.locator('.config-card')).toBeVisible({ timeout: 10_000 });
    await pause(page, LONG_PAUSE);

    // Open preset dropdown
    await page.locator('mat-select').first().click();
    await expect(page.locator('mat-option').first()).toBeVisible({ timeout: 10_000 });
    await pause(page, LONG_PAUSE);

    // Select "Discover → Implement"
    const implementOption = page.locator('mat-option:has-text("Implement")');
    if (await implementOption.first().isVisible().catch(() => false)) {
      await implementOption.first().click();
    } else {
      const fullOption = page.locator('mat-option:has-text("Full Pipeline")');
      if (await fullOption.isVisible().catch(() => false)) {
        await fullOption.click();
      } else {
        await page.locator('mat-option').last().click();
      }
    }
    await pause(page, LONG_PAUSE);

    // Show selected phase chips
    const chips = page.locator('.phase-chips mat-chip');
    await expect(chips.first()).toBeVisible({ timeout: 5_000 });
    await pause(page, LONG_PAUSE);

    // HIT THE BUTTON
    const runBtn = page.locator('.config-card button:has-text("Run Pipeline")');
    await expect(runBtn).toBeEnabled({ timeout: 5_000 });
    await runBtn.click();
    await pause(page, LONG_PAUSE);

    // ════════════════════════════════════════════════════════════════
    //  ACT 4 — LIVE EXECUTION  (≈60–90 s visible, then wait)
    //  Goal: "Watch the AI work — phases go green in real-time."
    // ════════════════════════════════════════════════════════════════

    // Status card + progress bar
    const statusRunning = page.locator('.status-card.state-running');
    if (await statusRunning.isVisible({ timeout: 15_000 }).catch(() => false)) {
      await pause(page, LONG_PAUSE);
    }

    const progressBar = page.locator('mat-progress-bar.run-progress');
    if (await progressBar.isVisible({ timeout: 10_000 }).catch(() => false)) {
      await pause(page, LONG_PAUSE);
    }

    // Stepper
    const stepRunning = page.locator('.stepper-step.step-running');
    if (await stepRunning.first().isVisible({ timeout: 10_000 }).catch(() => false)) {
      await pause(page, LONG_PAUSE);
    }

    // ── Live Dashboard — phases switching green ──
    await navigateTo(page, 'Dashboard', '/dashboard');
    await expect(page.locator('.phase-grid')).toBeVisible({ timeout: 10_000 });
    await pause(page, READ_PAUSE);
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await pause(page, LONG_PAUSE);
    await page.evaluate(() => window.scrollTo(0, 0));
    await pause(page, LONG_PAUSE);

    // Wait for at least one phase to turn running/completed
    const livePhase = page.locator('.phase-card.phase-running, .phase-card.phase-completed');
    await livePhase.first().isVisible({ timeout: 20_000 }).catch(() => {});
    await pause(page, READ_PAUSE);

    // ── Brief log stream (show "it's working", 1 scroll) ──
    await navigateTo(page, 'Run Pipeline', '/run');
    await pause(page, LONG_PAUSE);

    const logViewport = page.locator('.log-viewport');
    if (await logViewport.isVisible({ timeout: 20_000 }).catch(() => false)) {
      await expect(page.locator('.log-viewport .log-line').first())
        .toBeVisible({ timeout: 20_000 });
      await pause(page, READ_PAUSE);
      // Single scroll to bottom — enough to prove it's alive
      await logViewport.evaluate((el) => el.scrollTo(0, el.scrollHeight));
      await pause(page, READ_PAUSE);
    }

    // ── WAIT FOR COMPLETION — poll API ──
    const maxWaitMs = 7_200_000;
    const pollMs = 30_000;
    const startTime = Date.now();
    let pipelineDone = false;

    while (Date.now() - startTime < maxWaitMs) {
      const resp = await page.request
        .get('http://localhost:4200/api/pipeline/status')
        .catch(() => null);
      if (resp && resp.ok()) {
        const data = await resp.json().catch(() => ({}));
        if (['completed', 'failed', 'cancelled'].includes(data.state)) {
          pipelineDone = data.state === 'completed';
          break;
        }
      }
      // Keep log tailing while waiting
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

    // ════════════════════════════════════════════════════════════════
    //  ACT 5 — THE RESULTS  (the star of the show, ≈3 min)
    //  Goal: "Look what the AI generated — real architecture docs,
    //         development plans, code, and git branches."
    // ════════════════════════════════════════════════════════════════

    // ── 5a. Dashboard — all phases GREEN ──
    await navigateTo(page, 'Dashboard', '/dashboard');
    await expect(page.locator('.phase-grid')).toBeVisible({ timeout: 10_000 });
    await pause(page, READ_PAUSE);

    // Scroll to show all completed phase cards
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight / 2));
    await pause(page, LONG_PAUSE);
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await pause(page, LONG_PAUSE);
    await page.evaluate(() => window.scrollTo(0, 0));
    await pause(page, LONG_PAUSE);

    // ── 5b. Knowledge — AI-generated architecture documentation ──
    await navigateTo(page, 'Knowledge', '/knowledge');

    if (await page.locator('.stats-bar').isVisible({ timeout: 10_000 }).catch(() => false)) {
      await pause(page, LONG_PAUSE);
    }

    // Cycle through doc groups, open key documents
    const groupChips = page.locator('.group-chip');
    if (await groupChips.first().isVisible({ timeout: 10_000 }).catch(() => false)) {
      const gCount = await groupChips.count();
      for (let g = 0; g < gCount; g++) {
        await groupChips.nth(g).click();
        await pause(page);

        const docRows = page.locator('.doc-row');
        const docCount = await docRows.count();
        // Open max 3 docs per group — enough to impress, keeps video tight
        for (let d = 0; d < Math.min(docCount, 3); d++) {
          await docRows.nth(d).click();
          const viewer = page.locator('.viewer-panel');
          if (await viewer.isVisible({ timeout: 5_000 }).catch(() => false)) {
            const viewerSel =
              '.viewer-panel .viewer-body, .viewer-panel .rendered-content, .viewer-panel .source-content';
            await scrollThrough(page, viewerSel, d === 0 ? 'slow' : 'fast');

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

    // ── 5c. Reports — Architecture tab ──
    await navigateTo(page, 'Reports', '/reports');
    await expect(page.locator('mat-tab-group')).toBeVisible({ timeout: 30_000 });
    await pause(page, LONG_PAUSE);

    const archTab = page.getByRole('tab', { name: /Architecture/i });
    if (await archTab.isVisible().catch(() => false)) {
      await archTab.click();
      await pause(page, LONG_PAUSE);

      const docGroupHeaders = page.locator('.doc-group-header');
      const groupCount = await docGroupHeaders.count();
      for (let g = 0; g < groupCount; g++) {
        await docGroupHeaders.nth(g).click();
        await pause(page);

        const docFileCards = page.locator('.doc-group-files:visible .doc-file-card');
        const cardCount = await docFileCards.count();
        // Show max 3 documents per group
        for (let i = 0; i < Math.min(cardCount, 3); i++) {
          await docFileCards.nth(i).click();
          const preview = page.locator('.doc-preview').first();
          if (await preview.isVisible({ timeout: 5_000 }).catch(() => false)) {
            await pause(page, g === 0 && i === 0 ? READ_PAUSE : PAUSE);
            await preview.evaluate((el) => el.scrollTo(0, el.scrollHeight / 2));
            await pause(page, LONG_PAUSE);
          }
        }

        // Collapse before next group
        await docGroupHeaders.nth(g).click();
        await pause(page, 400);
      }
    }

    // ── 5d. Reports — Development Plans ──
    const plansTab = page.getByRole('tab', { name: /Development Plans/i });
    if (await plansTab.isVisible().catch(() => false)) {
      await plansTab.click();
      await pause(page, LONG_PAUSE);

      const planPanels = page.locator('mat-expansion-panel');
      const planCount = await planPanels.count();
      // Show max 2 plans in detail
      for (let i = 0; i < Math.min(planCount, 2); i++) {
        const header = planPanels.nth(i).locator('mat-expansion-panel-header');
        if (await header.isVisible().catch(() => false)) {
          await header.click();
          await pause(page, READ_PAUSE);

          // Scroll through the plan body
          const planBody = page.locator('.plan-body, .plan-content, mat-expansion-panel-body').nth(i);
          if (await planBody.isVisible({ timeout: 3_000 }).catch(() => false)) {
            await planBody.evaluate((el) => el.scrollTo(0, el.scrollHeight / 2));
            await pause(page, PAUSE);
            await planBody.evaluate((el) => el.scrollTo(0, el.scrollHeight));
            await pause(page, READ_PAUSE);
          } else {
            await pause(page, READ_PAUSE);
          }

          await header.click();
          await pause(page, 600);
        }
      }
    }

    // ── 5e. Reports — Code Generation ──
    const codegenTab = page.getByRole('tab', { name: /Code Generation/i });
    if (await codegenTab.isVisible().catch(() => false)) {
      await codegenTab.click();
      await pause(page, LONG_PAUSE);

      const codegenPanels = page.locator('mat-expansion-panel');
      const codegenCount = await codegenPanels.count();
      for (let i = 0; i < Math.min(codegenCount, 2); i++) {
        const header = codegenPanels.nth(i).locator('mat-expansion-panel-header');
        if (await header.isVisible().catch(() => false)) {
          await header.click();
          await pause(page, READ_PAUSE);
        }
      }
      await pause(page, LONG_PAUSE);
    }

    // ── 5f. Reports — Git Branches ──
    const branchesTab = page.getByRole('tab', { name: /Git Branches/i });
    if (await branchesTab.isVisible().catch(() => false)) {
      await branchesTab.click();
      await pause(page, LONG_PAUSE);
      const branchGrid = page.locator('.branches-grid');
      if (await branchGrid.isVisible({ timeout: 5_000 }).catch(() => false)) {
        await pause(page, READ_PAUSE);
      }
    }

    // ════════════════════════════════════════════════════════════════
    //  ACT 6 — AUDIT TRAIL  (≈15 s)
    //  Goal: "Every run is tracked — full traceability."
    // ════════════════════════════════════════════════════════════════

    await navigateTo(page, 'History', '/history');
    const filterBar = page.locator('.filter-bar, .history-filters');
    await expect(filterBar.first()).toBeVisible({ timeout: 10_000 });
    await pause(page, LONG_PAUSE);

    // Wait for table
    await page.waitForTimeout(2000);
    const historyContent = page.locator('.history-table, .run-card, .run-row, .empty-state');
    if (await historyContent.first().isVisible({ timeout: 5_000 }).catch(() => false)) {
      await pause(page, LONG_PAUSE);
    }

    // Expand the most recent run
    const historyRows = page.locator('.table-row');
    if ((await historyRows.count()) > 0) {
      await historyRows.first().click();
      await pause(page, READ_PAUSE);

      const detailPanel = page.locator('.detail-panel');
      if (await detailPanel.isVisible({ timeout: 5_000 }).catch(() => false)) {
        await detailPanel.evaluate((el) => el.scrollTo(0, el.scrollHeight / 2));
        await pause(page, LONG_PAUSE);
        await detailPanel.evaluate((el) => el.scrollTo(0, el.scrollHeight));
        await pause(page, LONG_PAUSE);
      }
    }

    // ════════════════════════════════════════════════════════════════
    //  FINALE — Dashboard closing shot  (≈10 s)
    // ════════════════════════════════════════════════════════════════

    await page.goto('/dashboard');
    await expect(page.locator('.hero')).toBeVisible({ timeout: 10_000 });
    await pause(page, READ_PAUSE);
    // Scroll through the completed phase grid one last time
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await pause(page, READ_PAUSE);
    await page.evaluate(() => window.scrollTo(0, 0));
    await pause(page, READ_PAUSE);
  });
});
