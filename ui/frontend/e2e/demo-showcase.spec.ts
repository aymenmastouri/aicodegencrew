import { test, expect, Page } from '@playwright/test';

/**
 * Demo Showcase — MANAGER EDITION
 *
 * Optimised for non-technical audience: shows business value & outcomes only.
 * No Settings, Collectors, Phases-config, MCP, Logs, Metrics, Pipeline-Data.
 *
 * Story:  Empty Tool → Dark Mode → Upload Task → One-Click Run → Live Progress →
 *         Knowledge Search → Architecture Diagram → Export ZIP →
 *         Development Plans → Generated Code → Git Branches →
 *         Run Comparison → Audit History → Dark Mode Finale!
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

/** Show a subtitle overlay at the bottom of the screen (visible in video recording) */
async function showSubtitle(page: Page, text: string, durationMs = READ_PAUSE) {
  await page.evaluate((t) => {
    // Remove previous subtitle if any
    document.getElementById('demo-subtitle')?.remove();
    const el = document.createElement('div');
    el.id = 'demo-subtitle';
    el.textContent = t;
    Object.assign(el.style, {
      position: 'fixed', bottom: '32px', left: '50%', transform: 'translateX(-50%)',
      background: 'rgba(0,0,0,0.82)', color: '#fff', padding: '14px 32px',
      borderRadius: '10px', fontSize: '20px', fontFamily: 'system-ui, sans-serif',
      fontWeight: '500', zIndex: '99999', maxWidth: '80%', textAlign: 'center',
      boxShadow: '0 4px 24px rgba(0,0,0,0.3)', letterSpacing: '0.02em',
      lineHeight: '1.5', pointerEvents: 'none',
    });
    document.body.appendChild(el);
  }, text);
  await pause(page, durationMs);
}

/** Remove the subtitle overlay */
async function hideSubtitle(page: Page) {
  await page.evaluate(() => document.getElementById('demo-subtitle')?.remove());
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
    // Step 1: Cancel any running/stale pipeline (fixes 409 on reset)
    await page.request.post('http://localhost:4200/api/pipeline/cancel').catch(() => {});
    await pause(page, 2000);

    // Step 2: Reset all phases (retry on 409 in case cancel takes a moment)
    for (let attempt = 0; attempt < 3; attempt++) {
      const resp = await page.request.post('http://localhost:4200/api/reset/all');
      if (resp.ok()) break;
      if (resp.status() === 409 && attempt < 2) { await pause(page, 5_000); continue; }
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
    await showSubtitle(page, 'AI-Powered SDLC Automation — from Jira task to generated code');

    // ── 1b. Getting Started card — 4 simple steps ──
    await hideSubtitle(page);
    const onboardingCard = page.locator('.onboarding-card');
    if (await onboardingCard.isVisible({ timeout: 5_000 }).catch(() => false)) {
      await onboardingCard.scrollIntoViewIfNeeded();
      await showSubtitle(page, 'Getting Started — 4 simple steps to automate your development lifecycle');
    }

    // ── 1c. Dark Mode toggle — visual wow moment ──
    await hideSubtitle(page);
    const darkModeBtn = page.locator('mat-toolbar button:has(mat-icon:has-text("dark_mode"))');
    if (await darkModeBtn.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await darkModeBtn.click();
      await showSubtitle(page, 'Built-in dark mode — one click to switch themes');
      // Switch back to light for the rest of the demo
      const lightModeBtn = page.locator('mat-toolbar button:has(mat-icon:has-text("light_mode"))');
      if (await lightModeBtn.isVisible({ timeout: 3_000 }).catch(() => false)) {
        await lightModeBtn.click();
        await pause(page, LONG_PAUSE);
      }
    }

    // ── 1d. Phase grid — 8 phases, all pending ──
    await hideSubtitle(page);
    await expect(page.locator('.phase-grid')).toBeVisible({ timeout: 10_000 });
    await showSubtitle(page, '8 phases — from repository indexing to code generation and delivery', LONG_PAUSE);
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight / 2));
    await pause(page, LONG_PAUSE);
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await pause(page, LONG_PAUSE);
    await hideSubtitle(page);
    await page.evaluate(() => window.scrollTo(0, 0));
    await pause(page);

    // ── 1d. Knowledge — empty (before vs. after) ──
    await navigateTo(page, 'Knowledge', '/knowledge');
    await expect(page.locator('.empty-state').or(page.locator('.stats-bar')).first())
      .toBeVisible({ timeout: 10_000 });
    await showSubtitle(page, 'Knowledge base is empty — no documentation generated yet');

    // ════════════════════════════════════════════════════════════════
    //  ACT 2 — UPLOAD A JIRA TASK  (≈20 s)
    //  Goal: "Just drag-and-drop a task file — that's the only input."
    // ════════════════════════════════════════════════════════════════

    await hideSubtitle(page);
    await navigateTo(page, 'Input Files', '/inputs');
    await expect(page.locator('.category-card')).toHaveCount(4, { timeout: 10_000 });
    await showSubtitle(page, 'Upload a Jira task — the only manual input needed', LONG_PAUSE);

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
    await hideSubtitle(page);
    const snackbar = page.locator('.mat-mdc-snack-bar-container');
    await expect(snackbar).toBeVisible({ timeout: 10_000 });
    await showSubtitle(page, 'Task file uploaded successfully — ready to run the pipeline');

    // Confirm file appears in list
    await expect(taskCard.locator('.file-name:has-text("BNUVZ-12529.xml")'))
      .toBeVisible({ timeout: 5_000 });
    await pause(page, LONG_PAUSE);

    // ════════════════════════════════════════════════════════════════
    //  ACT 3 — ONE-CLICK PIPELINE START  (≈15 s)
    //  Goal: "Select a preset, click Run — that's it."
    // ════════════════════════════════════════════════════════════════

    await hideSubtitle(page);
    await navigateTo(page, 'Run Pipeline', '/run');
    await expect(page.locator('.config-card')).toBeVisible({ timeout: 10_000 });
    await showSubtitle(page, 'Select a preset and click Run — one-click automation', LONG_PAUSE);

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
    await hideSubtitle(page);
    const runBtn = page.locator('.config-card button:has-text("Run Pipeline")');
    await expect(runBtn).toBeEnabled({ timeout: 5_000 });
    await runBtn.click();
    await showSubtitle(page, 'Pipeline started — AI is now analyzing your codebase', LONG_PAUSE);

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
    await hideSubtitle(page);
    await navigateTo(page, 'Dashboard', '/dashboard');
    await expect(page.locator('.phase-grid')).toBeVisible({ timeout: 10_000 });
    await showSubtitle(page, 'Live dashboard — watch phases turn green in real-time', READ_PAUSE);
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await pause(page, LONG_PAUSE);
    await page.evaluate(() => window.scrollTo(0, 0));
    await pause(page, LONG_PAUSE);

    // Wait for at least one phase to turn running/completed
    const livePhase = page.locator('.phase-card.phase-running, .phase-card.phase-completed');
    await livePhase.first().isVisible({ timeout: 20_000 }).catch(() => {});
    await pause(page, READ_PAUSE);

    // ── Brief log stream (show "it's working", 1 scroll) ──
    await hideSubtitle(page);
    await navigateTo(page, 'Run Pipeline', '/run');
    await showSubtitle(page, 'Live log stream — full transparency into what the AI is doing', LONG_PAUSE);

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
    await hideSubtitle(page);
    const maxWaitMs = 7_200_000;
    const pollMs = 30_000;
    const startTime = Date.now();
    let pipelineDone = false;
    const phaseLabels: Record<string, string> = {
      discover: 'Indexing repository (25,000+ code chunks)',
      extract:  'Extracting architecture facts from source code',
      analyze:  'AI analyzing code structure and dependencies',
      document: 'Generating C4 & arc42 architecture documentation',
      plan:     'Creating development plans from Jira task',
      implement:'AI writing code changes based on the plan',
      verify:   'Running tests and build verification',
      deliver:  'Generating final review and delivery report',
    };

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
        // Show current phase as subtitle
        const phases = data.phase_progress || [];
        const running = phases.find((p: { status: string }) => p.status === 'running');
        if (running) {
          const label = phaseLabels[running.phase_id] || running.phase_id;
          const pct = Math.round(data.progress_percent || 0);
          const skipped = phases.filter((p: { status: string }) => p.status === 'skipped');
          const skippedNote = skipped.length > 0
            ? `  [${skipped.map((s: { phase_id: string }) => s.phase_id).join(', ')} skipped — already cached]`
            : '';
          await showSubtitle(page, `${label}  (${pct}% complete)${skippedNote}`, 0);
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
    await hideSubtitle(page);
    await navigateTo(page, 'Dashboard', '/dashboard');
    await expect(page.locator('.phase-grid')).toBeVisible({ timeout: 10_000 });
    await showSubtitle(page, 'All phases completed — full SDLC pipeline done!', READ_PAUSE);

    // Scroll to show all completed phase cards
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight / 2));
    await pause(page, LONG_PAUSE);
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await pause(page, LONG_PAUSE);
    await page.evaluate(() => window.scrollTo(0, 0));
    await pause(page, LONG_PAUSE);

    // ── 5b. Knowledge — AI-generated architecture documentation ──
    await hideSubtitle(page);
    await navigateTo(page, 'Knowledge', '/knowledge');
    await showSubtitle(page, 'AI-generated architecture documentation — C4 models, arc42 chapters', LONG_PAUSE);

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

    // ── 5b-extra. Knowledge Search ──
    await hideSubtitle(page);
    const searchInput = page.locator('.search-input');
    if (await searchInput.isVisible({ timeout: 5_000 }).catch(() => false)) {
      await showSubtitle(page, 'Full-text search across all generated documentation', PAUSE);
      await searchInput.click();
      await searchInput.fill('Controller');
      await pause(page, LONG_PAUSE);
      const searchResults = page.locator('.search-result-row');
      if (await searchResults.first().isVisible({ timeout: 5_000 }).catch(() => false)) {
        await pause(page, READ_PAUSE);
        // Open a search result
        await searchResults.first().click();
        await pause(page, LONG_PAUSE);
        // Close viewer if open
        const closeBtn = page.locator('.viewer-panel button:has(mat-icon:has-text("close"))');
        if (await closeBtn.isVisible({ timeout: 3_000 }).catch(() => false)) {
          await closeBtn.click();
          await pause(page, 400);
        }
      }
      // Clear search
      const clearBtn = page.locator('.search-clear');
      if (await clearBtn.isVisible().catch(() => false)) {
        await clearBtn.click();
        await pause(page);
      }
    }

    // ── 5c. Reports — Architecture tab ──
    await hideSubtitle(page);
    await navigateTo(page, 'Reports', '/reports');
    await expect(page.locator('mat-tab-group')).toBeVisible({ timeout: 30_000 });
    await showSubtitle(page, 'Reports — architecture analysis, development plans, and code generation results', LONG_PAUSE);

    // Export ZIP button
    const exportBtn = page.locator('button:has-text("Export ZIP")');
    if (await exportBtn.isVisible({ timeout: 5_000 }).catch(() => false)) {
      await showSubtitle(page, 'One-click export — download all architecture docs as ZIP', LONG_PAUSE);
      await exportBtn.click();
      await pause(page, READ_PAUSE);
    }

    await hideSubtitle(page);
    const archTab = page.getByRole('tab', { name: /Architecture/i });
    if (await archTab.isVisible().catch(() => false)) {
      await archTab.click();
      await pause(page, LONG_PAUSE);

      // Mermaid container diagram
      const diagramCard = page.locator('.diagram-card');
      if (await diagramCard.isVisible({ timeout: 10_000 }).catch(() => false)) {
        await diagramCard.scrollIntoViewIfNeeded();
        await showSubtitle(page, 'Auto-generated architecture diagram — containers and their relationships', READ_PAUSE);
        const diagramSvg = page.locator('.diagram-container svg');
        if (await diagramSvg.isVisible({ timeout: 10_000 }).catch(() => false)) {
          await pause(page, READ_PAUSE);
        }
      }

      await hideSubtitle(page);
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
    await hideSubtitle(page);
    const plansTab = page.getByRole('tab', { name: /Development Plans/i });
    if (await plansTab.isVisible().catch(() => false)) {
      await plansTab.click();
      await showSubtitle(page, 'AI-generated development plan — step-by-step implementation guide', LONG_PAUSE);

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
    await hideSubtitle(page);
    const codegenTab = page.getByRole('tab', { name: /Code Generation/i });
    if (await codegenTab.isVisible().catch(() => false)) {
      await codegenTab.click();
      await showSubtitle(page, 'AI-generated code — ready to merge, with build verification', LONG_PAUSE);

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
    await hideSubtitle(page);
    const branchesTab = page.getByRole('tab', { name: /Git Branches/i });
    if (await branchesTab.isVisible().catch(() => false)) {
      await branchesTab.click();
      await showSubtitle(page, 'Git branches — each task gets its own feature branch with generated code', LONG_PAUSE);
      const branchGrid = page.locator('.branches-grid');
      if (await branchGrid.isVisible({ timeout: 5_000 }).catch(() => false)) {
        await pause(page, READ_PAUSE);
      }
    }

    // ════════════════════════════════════════════════════════════════
    //  ACT 6 — AUDIT TRAIL  (≈15 s)
    //  Goal: "Every run is tracked — full traceability."
    // ════════════════════════════════════════════════════════════════

    await hideSubtitle(page);
    await navigateTo(page, 'History', '/history');
    const filterBar = page.locator('.filter-bar, .history-filters');
    await expect(filterBar.first()).toBeVisible({ timeout: 10_000 });
    await showSubtitle(page, 'Complete audit trail — every pipeline run is tracked and reproducible', LONG_PAUSE);

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

      // ── Run Comparison (if 2+ runs exist) ──
      const compareCheckboxes = page.locator('.compare-col mat-checkbox');
      if ((await compareCheckboxes.count()) >= 2) {
        await hideSubtitle(page);
        await showSubtitle(page, 'Run comparison — select two runs and compare phase-by-phase', PAUSE);
        // Click first two checkboxes
        await compareCheckboxes.nth(0).click();
        await pause(page, PAUSE);
        await compareCheckboxes.nth(1).click();
        await pause(page, LONG_PAUSE);

        // Click Compare button
        const compareBtn = page.locator('button:has-text("Compare")');
        if (await compareBtn.isVisible({ timeout: 3_000 }).catch(() => false)) {
          await compareBtn.click();
          await pause(page, LONG_PAUSE);

          const comparePanel = page.locator('.compare-panel');
          if (await comparePanel.isVisible({ timeout: 5_000 }).catch(() => false)) {
            await comparePanel.scrollIntoViewIfNeeded();
            await pause(page, READ_PAUSE);
            await scrollThrough(page, '.compare-panel', 'slow');
          }
        }
      }
    }

    // ════════════════════════════════════════════════════════════════
    //  FINALE — Dashboard closing shot  (≈10 s)
    // ════════════════════════════════════════════════════════════════

    await hideSubtitle(page);
    await page.goto('/dashboard');
    await expect(page.locator('.hero')).toBeVisible({ timeout: 10_000 });

    // Dramatic dark mode finale
    const finalDarkBtn = page.locator('mat-toolbar button:has(mat-icon:has-text("dark_mode"))');
    if (await finalDarkBtn.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await finalDarkBtn.click();
      await pause(page, LONG_PAUSE);
    }

    await showSubtitle(page, 'SDLC Pilot — from Jira task to generated code, fully automated');
    // Scroll through the completed phase grid one last time
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await pause(page, READ_PAUSE);
    await page.evaluate(() => window.scrollTo(0, 0));
    await pause(page, READ_PAUSE);
    await hideSubtitle(page);
  });
});
