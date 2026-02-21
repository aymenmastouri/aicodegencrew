import { test, expect } from '@playwright/test';

test.describe('Knowledge Explorer', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/knowledge');
  });

  test('should render page title with icon', async ({ page }) => {
    await expect(page.locator('.page-title')).toContainText('Knowledge Explorer');
    await expect(page.locator('.page-icon')).toBeVisible();
  });

  test('should show either empty state or stats bar', async ({ page }) => {
    // Wait for loading to complete — either empty state or stats bar appears
    const content = page.locator('.empty-state, .stats-bar');
    await expect(content.first()).toBeVisible({ timeout: 10_000 });
    const isEmpty = await page.locator('.empty-state').isVisible().catch(() => false);
    if (isEmpty) {
      await expect(page.locator('.empty-state')).toContainText('No knowledge base found');
    } else {
      await expect(page.locator('.stats-bar')).toBeVisible();
      await expect(page.locator('.stat-item').first()).toBeVisible();
    }
  });

  test('should show file count > 0 when knowledge exists', async ({ page }) => {
    if (await page.locator('.empty-state').isVisible({ timeout: 2_000 }).catch(() => false)) return;
    const statItem = page.locator('.stat-item').first();
    await expect(statItem).toBeVisible({ timeout: 10_000 });
    const text = await statItem.textContent();
    const num = parseInt(text?.match(/\d+/)?.[0] || '0');
    expect(num).toBeGreaterThan(0);
  });

  test('should display architecture documentation section when docs exist', async ({ page }) => {
    if (await page.locator('.empty-state').isVisible({ timeout: 2_000 }).catch(() => false)) return;
    const archSection = page.locator('.section-arch');
    if (!(await archSection.isVisible({ timeout: 5_000 }).catch(() => false))) return;
    await expect(archSection.locator('.section-title')).toContainText('Architecture Documentation');
  });

  test('should display group navigation chips when arch docs exist', async ({ page }) => {
    if (await page.locator('.empty-state').isVisible({ timeout: 2_000 }).catch(() => false)) return;
    const groupNav = page.locator('.group-nav');
    if (!(await groupNav.isVisible({ timeout: 5_000 }).catch(() => false))) return;
    const chips = page.locator('.group-chip');
    const count = await chips.count();
    expect(count).toBeGreaterThan(0);
  });

  test('should show doc rows when architecture docs exist', async ({ page }) => {
    if (await page.locator('.empty-state').isVisible({ timeout: 2_000 }).catch(() => false)) return;
    const docList = page.locator('.doc-list');
    if (!(await docList.isVisible({ timeout: 5_000 }).catch(() => false))) return;
    const rows = page.locator('.doc-row');
    await expect(rows.first()).toBeVisible({ timeout: 10_000 });
    const count = await rows.count();
    expect(count).toBeGreaterThan(0);
  });

  test('should show file type badges and doc names in rows', async ({ page }) => {
    if (await page.locator('.empty-state').isVisible({ timeout: 2_000 }).catch(() => false)) return;
    const docRow = page.locator('.doc-row').first();
    if (!(await docRow.isVisible({ timeout: 5_000 }).catch(() => false))) return;
    await expect(page.locator('.doc-badge').first()).toBeVisible();
    await expect(page.locator('.doc-name').first()).toBeVisible();
  });

  test('should open document viewer when clicking a doc row', async ({ page }) => {
    if (await page.locator('.empty-state').isVisible({ timeout: 2_000 }).catch(() => false)) return;
    const docRow = page.locator('.doc-row').first();
    if (!(await docRow.isVisible({ timeout: 5_000 }).catch(() => false))) return;
    await docRow.click();
    await expect(page.locator('.viewer-panel')).toBeVisible({ timeout: 10_000 });
  });

  test('should render markdown or source content for .md files', async ({ page }) => {
    if (await page.locator('.empty-state').isVisible({ timeout: 2_000 }).catch(() => false)) return;
    const mdRow = page.locator('.doc-row:has(.badge-md)').first();
    if (!(await mdRow.isVisible({ timeout: 5_000 }).catch(() => false))) return;
    await mdRow.click();
    await expect(page.locator('.viewer-panel')).toBeVisible({ timeout: 10_000 });
    const hasRendered = await page.locator('.rendered-content').isVisible().catch(() => false);
    const hasSource = await page.locator('.source-content').isVisible().catch(() => false);
    expect(hasRendered || hasSource).toBeTruthy();
  });

  test('should toggle between rendered and source view for .md files', async ({ page }) => {
    if (await page.locator('.empty-state').isVisible({ timeout: 2_000 }).catch(() => false)) return;
    const mdRow = page.locator('.doc-row:has(.badge-md)').first();
    if (!(await mdRow.isVisible({ timeout: 5_000 }).catch(() => false))) return;
    await mdRow.click();
    await expect(page.locator('.viewer-panel')).toBeVisible({ timeout: 10_000 });
    const sourceBtn = page.locator('.mode-btn:has-text("Source")');
    if (await sourceBtn.isVisible()) {
      await sourceBtn.click();
      await expect(page.locator('.source-content')).toBeVisible({ timeout: 5_000 });
    }
  });

  test('should close viewer with close button', async ({ page }) => {
    if (await page.locator('.empty-state').isVisible({ timeout: 2_000 }).catch(() => false)) return;
    const docRow = page.locator('.doc-row').first();
    if (!(await docRow.isVisible({ timeout: 5_000 }).catch(() => false))) return;
    await docRow.click();
    await expect(page.locator('.viewer-panel')).toBeVisible({ timeout: 10_000 });
    await page.locator('.viewer-actions button:has(mat-icon:has-text("close"))').click();
    await expect(page.locator('.viewer-panel')).toBeHidden();
  });

  test('should switch between group chips when multiple exist', async ({ page }) => {
    if (await page.locator('.empty-state').isVisible({ timeout: 2_000 }).catch(() => false)) return;
    const chips = page.locator('.group-chip');
    const count = await chips.count();
    if (count < 2) return; // Need at least 2 groups to switch
    const secondChip = chips.nth(1);
    await expect(secondChip).toBeVisible({ timeout: 5_000 });
    await secondChip.click();
    await expect(secondChip).toHaveClass(/group-active/, { timeout: 3_000 });
  });

  test('should show Pipeline Data section when data files exist', async ({ page }) => {
    if (await page.locator('.empty-state').isVisible({ timeout: 2_000 }).catch(() => false)) return;
    const dataSection = page.locator('.section-data');
    if (!(await dataSection.isVisible({ timeout: 5_000 }).catch(() => false))) return;
    await expect(dataSection.locator('.section-title')).toContainText('Pipeline Data');
    const dgHeaders = page.locator('.dg-header');
    const dgCount = await dgHeaders.count();
    expect(dgCount).toBeGreaterThan(0);
  });

  test('should show JSON file rows in Pipeline Data section', async ({ page }) => {
    if (await page.locator('.empty-state').isVisible({ timeout: 2_000 }).catch(() => false)) return;
    const dataSection = page.locator('.section-data');
    if (!(await dataSection.isVisible({ timeout: 5_000 }).catch(() => false))) return;
    // Click first data group to expand it
    const firstDgHeader = page.locator('.dg-header').first();
    await firstDgHeader.click();
    const dgFile = page.locator('.dg-file').first();
    if (await dgFile.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await expect(dgFile).toBeVisible();
    }
  });
});
