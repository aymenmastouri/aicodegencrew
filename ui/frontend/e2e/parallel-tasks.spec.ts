import { test, expect, Page } from '@playwright/test';

/**
 * Helper: switch to Custom Phases tab and check the given phases.
 * Uses getByText inside .phase-checkboxes to reliably click Angular Material checkboxes.
 */
async function selectCustomPhases(page: Page, phaseNames: string[]): Promise<void> {
  await page.locator('.mat-mdc-tab').nth(1).click();
  await expect(page.locator('.phase-checkboxes')).toBeVisible({ timeout: 5_000 });

  for (const name of phaseNames) {
    // Click the phase name TEXT inside the checkboxes container —
    // this reliably toggles Angular Material checkboxes.
    await page.locator('.phase-checkboxes').getByText(name, { exact: false }).click();
  }
}

/** Helper: select triage, wait for parallel section, and enable it. */
async function enableParallel(page: Page): Promise<void> {
  await selectCustomPhases(page, ['Triage']);
  await expect(page.locator('.parallel-section')).toBeVisible({ timeout: 5_000 });
  await page.locator('.parallel-header').click();
  await expect(page.locator('.parallel-body')).toBeVisible({ timeout: 5_000 });
}

test.describe('Parallel Task Processing', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/run');
    await expect(page.locator('.config-card')).toBeVisible({ timeout: 10_000 });
  });

  // =========================================================================
  // Visibility
  // =========================================================================

  test.describe('Section Visibility', () => {
    test('should NOT show parallel section by default', async ({ page }) => {
      await expect(page.locator('.parallel-section')).toHaveCount(0);
    });

    test('should show parallel section when triage is checked', async ({ page }) => {
      await selectCustomPhases(page, ['Triage']);
      await expect(page.locator('.parallel-section')).toBeVisible({ timeout: 5_000 });
    });

    test('should show parallel section when plan is checked', async ({ page }) => {
      await selectCustomPhases(page, ['Plan']);
      await expect(page.locator('.parallel-section')).toBeVisible({ timeout: 5_000 });
    });

    test('should show parallel section when both triage and plan checked', async ({ page }) => {
      await selectCustomPhases(page, ['Triage', 'Plan']);
      await expect(page.locator('.parallel-section')).toBeVisible({ timeout: 5_000 });
    });

    test('should hide parallel section when only non-task phases selected', async ({ page }) => {
      await selectCustomPhases(page, ['Discover']);
      await expect(page.locator('.parallel-section')).toHaveCount(0);
    });

    test('should show parallel section when preset with triage/plan is selected', async ({ page }) => {
      await page.locator('mat-select').first().click();
      const options = page.locator('mat-option');
      await expect(options.first()).toBeVisible({ timeout: 10_000 });

      const count = await options.count();
      let found = false;
      for (let i = 0; i < count; i++) {
        const text = (await options.nth(i).textContent()) || '';
        if (text.toLowerCase().includes('triage') || text.toLowerCase().includes('plan')) {
          await options.nth(i).click();
          found = true;
          break;
        }
      }

      if (found) {
        await expect(page.locator('.parallel-section')).toBeVisible({ timeout: 5_000 });
      }
    });
  });

  // =========================================================================
  // Header
  // =========================================================================

  test.describe('Parallel Header', () => {
    test.beforeEach(async ({ page }) => {
      await selectCustomPhases(page, ['Triage']);
      await expect(page.locator('.parallel-section')).toBeVisible({ timeout: 5_000 });
    });

    test('should show title and subtitle', async ({ page }) => {
      await expect(page.locator('.parallel-title')).toContainText('Parallel Processing');
      await expect(page.locator('.parallel-subtitle')).toContainText('Run each task as its own subprocess');
    });

    test('should show inactive icon wrap when disabled', async ({ page }) => {
      const iconWrap = page.locator('.parallel-icon-wrap');
      await expect(iconWrap).toBeVisible();
      await expect(iconWrap).not.toHaveClass(/active/);
    });

    test('should activate icon wrap when toggled on', async ({ page }) => {
      await page.locator('.parallel-header').click();
      await expect(page.locator('.parallel-icon-wrap')).toHaveClass(/active/);
    });

    test('should show slide toggle', async ({ page }) => {
      await expect(page.locator('.parallel-header mat-slide-toggle')).toBeVisible();
    });

    test('should toggle parallel-active class', async ({ page }) => {
      const section = page.locator('.parallel-section');
      await expect(section).not.toHaveClass(/parallel-active/);

      await page.locator('.parallel-header').click();
      await expect(section).toHaveClass(/parallel-active/);

      await page.locator('.parallel-header').click();
      await expect(section).not.toHaveClass(/parallel-active/);
    });
  });

  // =========================================================================
  // Body — Concurrency & Task Selection
  // =========================================================================

  test.describe('Parallel Body', () => {
    test.beforeEach(async ({ page }) => {
      await enableParallel(page);
    });

    test('should show four concurrency chips', async ({ page }) => {
      const chips = page.locator('.concurrency-chip');
      await expect(chips).toHaveCount(4);
      await expect(chips.nth(0)).toContainText('1x');
      await expect(chips.nth(1)).toContainText('2x');
      await expect(chips.nth(2)).toContainText('4x');
      await expect(chips.nth(3)).toContainText('8x');
    });

    test('should have 4x selected by default', async ({ page }) => {
      await expect(page.locator('.concurrency-chip:has-text("4x")')).toHaveClass(/selected/);
    });

    test('should switch concurrency on chip click', async ({ page }) => {
      const chip2x = page.locator('.concurrency-chip:has-text("2x")');
      await chip2x.click();
      await expect(chip2x).toHaveClass(/selected/);
      await expect(page.locator('.concurrency-chip:has-text("4x")')).not.toHaveClass(/selected/);
    });

    test('should show concurrency label', async ({ page }) => {
      await expect(page.locator('.concurrency-label')).toContainText('Concurrency');
    });

    test('should show task picker or empty state', async ({ page }) => {
      const hasTasks = await page.locator('.task-picker').isVisible().catch(() => false);
      const hasEmpty = await page.locator('.no-tasks-empty').isVisible().catch(() => false);
      expect(hasTasks || hasEmpty).toBe(true);
    });

    test('should show task chips with check icon and ID', async ({ page }) => {
      const chips = page.locator('.task-chip');
      if ((await chips.count()) > 0) {
        const first = chips.first();
        await expect(first.locator('.task-chip-check')).toBeVisible();
        await expect(first.locator('.task-chip-id')).toBeVisible();
        const id = await first.locator('.task-chip-id').textContent();
        expect(id?.trim().length).toBeGreaterThan(0);
      }
    });

    test('should auto-select all tasks on enable', async ({ page }) => {
      const chips = page.locator('.task-chip');
      const count = await chips.count();
      for (let i = 0; i < count; i++) {
        await expect(chips.nth(i)).toHaveClass(/selected/);
      }
    });

    test('should toggle task on chip click', async ({ page }) => {
      const chips = page.locator('.task-chip');
      if ((await chips.count()) > 0) {
        const first = chips.first();
        await expect(first).toHaveClass(/selected/);

        await first.click();
        await expect(first).not.toHaveClass(/selected/);

        await first.click();
        await expect(first).toHaveClass(/selected/);
      }
    });

    test('should have Clear all / Select all toggle', async ({ page }) => {
      if ((await page.locator('.task-chip').count()) > 0) {
        const toggle = page.locator('.task-picker-toggle');
        await expect(toggle).toContainText('Clear all');

        await toggle.click();
        await expect(toggle).toContainText('Select all');

        await toggle.click();
        await expect(toggle).toContainText('Clear all');
      }
    });

    test('should show reset button on hover', async ({ page }) => {
      const chips = page.locator('.task-chip');
      if ((await chips.count()) > 0) {
        const first = chips.first();
        await first.hover();
        await expect(first.locator('.task-chip-reset')).toBeVisible();
      }
    });

    test('should show empty state when no tasks', async ({ page }) => {
      if ((await page.locator('.task-chip').count()) === 0) {
        await expect(page.locator('.no-tasks-empty')).toContainText('inputs/tasks/');
      }
    });
  });

  // =========================================================================
  // Dynamic Subtitle
  // =========================================================================

  test.describe('Dynamic Subtitle', () => {
    test('should show task count in subtitle when enabled', async ({ page }) => {
      await enableParallel(page);
      if ((await page.locator('.task-chip').count()) > 0) {
        await expect(page.locator('.parallel-subtitle')).toContainText('tasks');
        await expect(page.locator('.parallel-subtitle')).toContainText('concurrency');
      }
    });

    test('should update subtitle on concurrency change', async ({ page }) => {
      await enableParallel(page);
      if ((await page.locator('.task-chip').count()) > 0) {
        await page.locator('.concurrency-chip:has-text("2x")').click();
        await expect(page.locator('.parallel-subtitle')).toContainText('2x concurrency');
      }
    });
  });

  // =========================================================================
  // Execution Preview
  // =========================================================================

  test.describe('Execution Preview', () => {
    test('should show parallel info in preview when enabled', async ({ page }) => {
      await enableParallel(page);
      if ((await page.locator('.task-chip').count()) > 0) {
        const preview = page.locator('.preview-tasks');
        if (await preview.isVisible().catch(() => false)) {
          await expect(preview).toContainText('task');
        }
      }
    });
  });
});
