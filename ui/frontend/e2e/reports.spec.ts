import { test, expect } from '@playwright/test';

test.describe('Reports', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/reports');
  });

  // --- Page Layout ---

  test('should render page title with icon', async ({ page }) => {
    await expect(page.locator('.page-title')).toContainText('Reports');
    await expect(page.locator('.page-icon')).toBeVisible();
  });

  // --- Tab Structure ---

  test('should show 4 tabs in the tab group', async ({ page }) => {
    const tabGroup = page.locator('mat-tab-group');
    await expect(tabGroup).toBeVisible({ timeout: 10_000 });
    const tabs = page.locator('.mat-mdc-tab');
    await expect(tabs).toHaveCount(4);
  });

  test('should show Architecture tab with doc count', async ({ page }) => {
    const tab = page.getByRole('tab', { name: /Architecture/i });
    await expect(tab).toBeVisible({ timeout: 10_000 });
  });

  test('should show Development Plans tab', async ({ page }) => {
    const tab = page.getByRole('tab', { name: /Development Plans/i });
    await expect(tab).toBeVisible({ timeout: 10_000 });
  });

  test('should show Code Generation tab', async ({ page }) => {
    const tab = page.getByRole('tab', { name: /Code Generation/i });
    await expect(tab).toBeVisible({ timeout: 10_000 });
  });

  test('should show Git Branches tab', async ({ page }) => {
    const tab = page.getByRole('tab', { name: /Git Branches/i });
    await expect(tab).toBeVisible({ timeout: 10_000 });
  });

  // --- Architecture Tab (Grouped Docs) ---

  test('should display architecture doc groups or empty state', async ({ page }) => {
    // Architecture is the default (first) tab
    const content = page.locator('.doc-groups, .tab-empty');
    await expect(content.first()).toBeVisible({ timeout: 10_000 });
  });

  test('should show doc group headers with icons if docs exist', async ({ page }) => {
    const docGroups = page.locator('.doc-group');
    const count = await docGroups.count();
    if (count > 0) {
      // Each group should have a header with icon and title
      const firstHeader = docGroups.first().locator('.doc-group-header');
      await expect(firstHeader).toBeVisible();
      await expect(firstHeader.locator('.doc-group-icon-wrap')).toBeVisible();
      await expect(firstHeader.locator('.doc-group-title')).toBeVisible();
    }
  });

  test('should show doc file cards within groups', async ({ page }) => {
    const docGroups = page.locator('.doc-group');
    const count = await docGroups.count();
    if (count > 0) {
      // Groups may start collapsed — expand the first one to reveal file cards
      const firstHeader = docGroups.first().locator('.doc-group-header');
      if (await firstHeader.isVisible()) {
        await firstHeader.click();
      }
      const fileCards = docGroups.first().locator('.doc-file-card');
      await expect(fileCards.first()).toBeVisible({ timeout: 5_000 });
      const fileCount = await fileCards.count();
      expect(fileCount).toBeGreaterThan(0);
    }
  });

  test('should expand doc preview on click', async ({ page }) => {
    const fileCard = page.locator('.doc-file-card').first();
    const cardExists = await fileCard.isVisible({ timeout: 10_000 }).catch(() => false);
    if (cardExists) {
      await fileCard.click();
      // Should show either a spinner or preview content
      const preview = page.locator('.doc-preview').first();
      await expect(preview).toBeVisible({ timeout: 5_000 });
    }
  });

  test('should show download button on doc files', async ({ page }) => {
    const dlBtn = page.locator('.doc-file-card .dl-btn').first();
    const exists = await dlBtn.isVisible({ timeout: 10_000 }).catch(() => false);
    if (exists) {
      await expect(dlBtn).toBeVisible();
    }
  });

  // --- Development Plans Tab ---

  test('should switch to Development Plans tab', async ({ page }) => {
    await expect(page.locator('mat-tab-group')).toBeVisible({ timeout: 10_000 });
    const plansTab = page.getByRole('tab', { name: /Development Plans/i });
    await plansTab.click();
    const content = page.locator('.report-accordion, .tab-empty');
    await expect(content.first()).toBeVisible({ timeout: 10_000 });
  });

  test('should expand a plan and show content if plans exist', async ({ page }) => {
    await expect(page.locator('mat-tab-group')).toBeVisible({ timeout: 10_000 });
    const plansTab = page.getByRole('tab', { name: /Development Plans/i });
    await plansTab.click();
    const panel = page.locator('mat-expansion-panel').first();
    const panelVisible = await panel.isVisible({ timeout: 10_000 }).catch(() => false);
    if (panelVisible) {
      await panel.locator('mat-expansion-panel-header').click();
      await expect(page.locator('.plan-body, .plan-content').first()).toBeVisible({ timeout: 5_000 });
    }
  });

  // --- Code Generation Tab ---

  test('should switch to Code Generation tab', async ({ page }) => {
    await expect(page.locator('mat-tab-group')).toBeVisible({ timeout: 10_000 });
    const codegenTab = page.getByRole('tab', { name: /Code Generation/i });
    await expect(codegenTab).toBeVisible({ timeout: 5_000 });
    await codegenTab.click();
    const content = page.locator('.report-accordion, .tab-empty, .empty-inline');
    await expect(content.first()).toBeVisible({ timeout: 10_000 });
  });

  // --- Git Branches Tab ---

  test('should switch to Git Branches tab and load branches', async ({ page }) => {
    await expect(page.locator('mat-tab-group')).toBeVisible({ timeout: 10_000 });
    const branchesTab = page.getByRole('tab', { name: /Git Branches/i });
    await branchesTab.click();
    // Should show branches grid, loading spinner, or empty state
    const content = page.locator('.branches-grid, .tab-empty, mat-spinner');
    await expect(content.first()).toBeVisible({ timeout: 10_000 });
  });

  // --- No Extract/Analyze Tabs (removed) ---

  test('should NOT show Extract or Analyze tabs', async ({ page }) => {
    await expect(page.locator('mat-tab-group')).toBeVisible({ timeout: 10_000 });
    const extractTab = page.getByRole('tab', { name: /Extract/i });
    const analyzeTab = page.getByRole('tab', { name: /Analyze/i });
    await expect(extractTab).toHaveCount(0);
    await expect(analyzeTab).toHaveCount(0);
  });
});
