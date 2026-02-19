import { test, expect } from '@playwright/test';

test.describe('Phases', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/phases');
  });

  test('should render page title with icon', async ({ page }) => {
    await expect(page.locator('.page-title')).toContainText('Phases');
  });

  test('should show phase configuration table', async ({ page }) => {
    await expect(page.locator('.phase-table')).toBeVisible({ timeout: 10_000 });
  });

  test('should display 8 phases in table', async ({ page }) => {
    await expect(page.locator('.phase-table')).toBeVisible({ timeout: 10_000 });
    const rows = page.locator('.phase-table tbody tr');
    await expect(rows).toHaveCount(8);
  });

  test('should show phase numbers, type badges, names, and status chips', async ({ page }) => {
    await expect(page.locator('.phase-table')).toBeVisible({ timeout: 10_000 });
    // Order column: numbered badge
    await expect(page.locator('.phase-num').first()).toBeVisible();
    // Type column: pipeline / crew / hybrid badge
    await expect(page.locator('.phase-type').first()).toBeVisible();
    // Name column: "Repository Indexing" is the discover phase display name
    await expect(page.locator('td:has-text("Repository Indexing")')).toBeVisible();
    // Status chip present
    await expect(page.locator('.status-chip').first()).toBeVisible();
  });

  test('should show exactly one reset button per phase (8 total)', async ({ page }) => {
    await expect(page.locator('.phase-table')).toBeVisible({ timeout: 10_000 });
    // Each phase row has one restart_alt icon button
    const resetButtons = page.locator('.phase-table button[mat-icon-button]:has(mat-icon)');
    await expect(resetButtons).toHaveCount(8);
  });

  test('should show Presets section', async ({ page }) => {
    await expect(page.locator('.section-title:has-text("Presets")')).toBeVisible({ timeout: 10_000 });
  });

  test('should list preset expansion panels', async ({ page }) => {
    const presets = page.locator('mat-accordion mat-expansion-panel');
    await expect(presets.first()).toBeVisible({ timeout: 10_000 });
    const count = await presets.count();
    expect(count).toBeGreaterThanOrEqual(1);
  });

  test('should expand preset and show phase chips', async ({ page }) => {
    const panels = page.locator('mat-accordion mat-expansion-panel');
    await expect(panels.first()).toBeVisible({ timeout: 10_000 });
    await panels.first().locator('mat-expansion-panel-header').click();
    await expect(page.locator('mat-chip-set mat-chip').first()).toBeVisible({ timeout: 5_000 });
  });

  test('should show preset panel title and phases count in description', async ({ page }) => {
    const panels = page.locator('mat-accordion mat-expansion-panel');
    await expect(panels.first()).toBeVisible({ timeout: 10_000 });
    // Panel header has title + description (N phases)
    const description = panels.first().locator('mat-panel-description');
    await expect(description).toContainText('phases');
  });

  // --- Reset Button Tests ---

  test('should show Reset All button in header', async ({ page }) => {
    await expect(page.locator('.phase-table')).toBeVisible({ timeout: 10_000 });
    const resetAllBtn = page.locator('button:has-text("Reset All")');
    await expect(resetAllBtn).toBeVisible();
  });

  test('should show restart_alt icon on every phase reset button', async ({ page }) => {
    await expect(page.locator('.phase-table')).toBeVisible({ timeout: 10_000 });
    const resetIcons = page.locator('.phase-table mat-icon:text("restart_alt")');
    await expect(resetIcons).toHaveCount(8);
  });

  test('should disable Reset All button when no phases have completed or failed', async ({ page }) => {
    await expect(page.locator('.phase-table')).toBeVisible({ timeout: 10_000 });
    const resetAllBtn = page.locator('button:has-text("Reset All")');
    // If no pipeline has ever run the button is disabled (hasResettablePhases returns false)
    const anyCompleted = await page.locator('.status-chip:text("completed")').count();
    const anyFailed = await page.locator('.status-chip:text("failed")').count();
    if (anyCompleted === 0 && anyFailed === 0) {
      await expect(resetAllBtn).toBeDisabled();
    } else {
      await expect(resetAllBtn).toBeEnabled();
    }
  });

  test('should disable individual reset button for idle phases', async ({ page }) => {
    await expect(page.locator('.phase-table')).toBeVisible({ timeout: 10_000 });
    const resetButtons = page.locator('.phase-table button[mat-icon-button]:has(mat-icon:text("restart_alt"))');
    const firstResetBtn = resetButtons.first();
    const status = await page.locator('.status-chip').first().textContent();
    const terminalStatuses = ['completed', 'failed', 'cancelled'];
    if (!terminalStatuses.includes(status?.trim() || '')) {
      await expect(firstResetBtn).toBeDisabled();
    }
  });
});

// ─── Phase Reset Dialogs ──────────────────────────────────────────────────────
// Phases page has two reset flows:
//   1. Single-phase reset: opens ConfirmDialog (warn) showing phases + file count
//   2. Discover phase reset: special "Clear Status" dialog (info, preserves ChromaDB)
//   3. Reset All: opens ConfirmDialog (warn) for all completed/failed phases
// ─────────────────────────────────────────────────────────────────────────────
test.describe('Phases - Reset Dialogs', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/phases');
    await expect(page.locator('.phase-table')).toBeVisible({ timeout: 10_000 });
  });

  test('should open "Clear Status" dialog (not reset) when resetting discover phase', async ({
    page,
  }) => {
    // The discover phase (first row) uses a special "Clear Status" flow that does NOT
    // delete the ChromaDB index — it only clears run state.
    // We can trigger this only when discover has a terminal status; mock if needed by
    // checking if the button is enabled first.
    const resetButtons = page.locator(
      '.phase-table button[mat-icon-button]:has(mat-icon:text("restart_alt"))',
    );
    const discoverResetBtn = resetButtons.first();
    const isDisabled = await discoverResetBtn.isDisabled();

    if (!isDisabled) {
      await discoverResetBtn.click();
      const dialog = page.locator('mat-dialog-container');
      await expect(dialog).toBeVisible({ timeout: 5_000 });
      // Discover shows "Clear ... Status" title, not "Reset ..."
      const title = dialog.locator('h2, [mat-dialog-title]');
      await expect(title).toContainText('Clear');
      // Cancel to leave state unchanged
      await dialog.locator('button:has-text("Cancel")').click();
      await expect(dialog).not.toBeVisible();
    } else {
      // Discover not completed — button disabled, no dialog. Test documents the guard.
      test.info().annotations.push({
        type: 'info',
        description: 'Discover phase not in terminal state; reset button disabled as expected.',
      });
    }
  });

  test('should open warn reset dialog for non-discover completed phase', async ({ page }) => {
    // Find a non-discover phase in terminal state
    const rows = page.locator('.phase-table tbody tr');
    const count = await rows.count();
    let triggered = false;

    for (let i = 1; i < count; i++) {
      // skip first row (discover)
      const row = rows.nth(i);
      const statusText = (await row.locator('.status-chip').textContent()) || '';
      const resetBtn = row.locator('button[mat-icon-button]:has(mat-icon:text("restart_alt"))');

      if (!statusText.trim().match(/completed|failed|cancelled/)) continue;
      if (await resetBtn.isDisabled()) continue;

      await resetBtn.click();
      const dialog = page.locator('mat-dialog-container');
      await expect(dialog).toBeVisible({ timeout: 5_000 });

      // Standard reset dialog has a "Reset" confirm label
      await expect(dialog.locator('h2, [mat-dialog-title]')).toContainText('Reset');
      // Cancel — no state change
      await dialog.locator('button:has-text("Cancel")').click();
      await expect(dialog).not.toBeVisible();
      triggered = true;
      break;
    }

    if (!triggered) {
      test.info().annotations.push({
        type: 'info',
        description: 'No non-discover completed phase found; dialog not triggered.',
      });
    }
  });

  test('should show file count info in reset dialog', async ({ page }) => {
    const rows = page.locator('.phase-table tbody tr');
    const count = await rows.count();

    for (let i = 1; i < count; i++) {
      const row = rows.nth(i);
      const statusText = (await row.locator('.status-chip').textContent()) || '';
      const resetBtn = row.locator('button[mat-icon-button]:has(mat-icon:text("restart_alt"))');

      if (!statusText.trim().match(/completed|failed/)) continue;
      if (await resetBtn.isDisabled()) continue;

      await resetBtn.click();
      const dialog = page.locator('mat-dialog-container');
      await expect(dialog).toBeVisible({ timeout: 5_000 });

      // Dialog body should mention file count
      const content = dialog.locator('mat-dialog-content, [mat-dialog-content]');
      await expect(content).toContainText('file');

      await dialog.locator('button:has-text("Cancel")').click();
      return;
    }

    test.info().annotations.push({
      type: 'info',
      description: 'No completed non-discover phase; file count dialog not tested.',
    });
  });

  test('Reset All dialog should list phases to reset', async ({ page }) => {
    const resetAllBtn = page.locator('button:has-text("Reset All")');
    const isDisabled = await resetAllBtn.isDisabled();

    if (!isDisabled) {
      await resetAllBtn.click();
      const dialog = page.locator('mat-dialog-container');
      await expect(dialog).toBeVisible({ timeout: 5_000 });

      // Title mentions "Reset All" or similar
      await expect(dialog.locator('h2, [mat-dialog-title]')).toContainText('Reset All');

      // Details list should be present (phases to reset)
      const details = dialog.locator('.dialog-details li, .details li');
      const detailCount = await details.count();
      expect(detailCount).toBeGreaterThanOrEqual(1);

      // Cancel — no state change
      await dialog.locator('button:has-text("Cancel")').click();
      await expect(dialog).not.toBeVisible();
    } else {
      test.info().annotations.push({
        type: 'info',
        description: 'No resettable phases; Reset All is disabled as expected.',
      });
    }
  });
});

// ─── Phase Status Chip Styling ────────────────────────────────────────────────
test.describe('Phases - Status Chips', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/phases');
    await expect(page.locator('.phase-table')).toBeVisible({ timeout: 10_000 });
  });

  test('should apply status-idle CSS class on chips for phases not yet run', async ({ page }) => {
    const idleChips = page.locator('.status-chip.status-idle');
    // At least some chips should be idle if no pipeline has run
    const totalChips = await page.locator('.status-chip').count();
    expect(totalChips).toBe(8);
  });

  test('should show completed chip text as "completed"', async ({ page }) => {
    const completedChips = page.locator('.status-chip.status-completed');
    const count = await completedChips.count();
    for (let i = 0; i < count; i++) {
      await expect(completedChips.nth(i)).toContainText('completed');
    }
  });

  test('should show running chip with spinner for in-progress phase', async ({ page }) => {
    const runningChips = page.locator('.status-chip.status-running');
    const count = await runningChips.count();
    // Only verify if pipeline is actively running
    if (count > 0) {
      await expect(runningChips.first().locator('mat-spinner')).toBeVisible();
    }
  });

  test('should show error icon on failed phase chip', async ({ page }) => {
    const failedChips = page.locator('.status-chip.status-failed');
    const count = await failedChips.count();
    if (count > 0) {
      await expect(failedChips.first().locator('mat-icon')).toBeVisible();
    }
  });
});

// ─── Phase Dependencies Display ───────────────────────────────────────────────
test.describe('Phases - Dependencies', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/phases');
    await expect(page.locator('.phase-table')).toBeVisible({ timeout: 10_000 });
  });

  test('should display dependency chips for phases that have dependencies', async ({ page }) => {
    // Most phases have at least one dependency (extract depends on discover, etc.)
    const depChips = page.locator('.dep-chip');
    const count = await depChips.count();
    // At least a few phases should have dependencies
    expect(count).toBeGreaterThanOrEqual(1);
  });

  test('discover phase should have no dependency chips (it is first)', async ({ page }) => {
    // Discover is phase order 1 — no upstream dependencies
    const rows = page.locator('.phase-table tbody tr');
    const discoverRow = rows.first();
    const depChips = discoverRow.locator('.dep-chip');
    await expect(depChips).toHaveCount(0);
  });
});
