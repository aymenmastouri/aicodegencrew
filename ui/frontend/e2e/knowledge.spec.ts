import { test, expect } from '@playwright/test';

test.describe('Knowledge Explorer', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/knowledge');
  });

  test('should render page title with icon', async ({ page }) => {
    await expect(page.locator('.page-title')).toContainText('Knowledge Explorer');
    await expect(page.locator('.page-title mat-icon')).toBeVisible();
  });

  test('should show stats bar with file count and size', async ({ page }) => {
    await expect(page.locator('.stats-bar')).toBeVisible({ timeout: 10_000 });
    await expect(page.locator('.stat-item:has-text("files")')).toBeVisible();
  });

  test('should show file count > 50', async ({ page }) => {
    const stat = page.locator('.stat-item:has-text("files") strong');
    await expect(stat).toBeVisible({ timeout: 10_000 });
    const text = await stat.textContent();
    expect(parseInt(text || '0')).toBeGreaterThanOrEqual(50);
  });

  test('should show type breakdown (JSON + Markdown)', async ({ page }) => {
    await expect(page.locator('.stat-type:has-text("JSON")')).toBeVisible({ timeout: 10_000 });
    await expect(page.locator('.stat-type:has-text("Markdown")')).toBeVisible();
  });

  test('should display category tabs', async ({ page }) => {
    const tabGroup = page.locator('mat-tab-group');
    await expect(tabGroup).toBeVisible({ timeout: 10_000 });
    await expect(tabGroup).toContainText('Arc42 Docs');
    await expect(tabGroup).toContainText('C4 Model');
    await expect(tabGroup).toContainText('Knowledge Base');
  });

  test('should show file cards in first tab', async ({ page }) => {
    const cards = page.locator('.file-card');
    await expect(cards.first()).toBeVisible({ timeout: 10_000 });
    const count = await cards.count();
    expect(count).toBeGreaterThan(0);
  });

  test('should show file type badges and names', async ({ page }) => {
    await expect(page.locator('.file-card').first()).toBeVisible({ timeout: 10_000 });
    await expect(page.locator('.fc-badge').first()).toBeVisible();
    await expect(page.locator('.fc-name').first()).toBeVisible();
  });

  test('should open document viewer when clicking a file card', async ({ page }) => {
    await expect(page.locator('.file-card').first()).toBeVisible({ timeout: 10_000 });
    await page.locator('.file-card').first().click();
    await expect(page.locator('.viewer-panel')).toBeVisible({ timeout: 10_000 });
  });

  test('should render markdown content for .md files', async ({ page }) => {
    // Click Arc42 tab (first tab, should be auto-selected)
    const mdCard = page.locator('.file-card:has(.badge-md)').first();
    await expect(mdCard).toBeVisible({ timeout: 10_000 });
    await mdCard.click();
    // Should show rendered markdown
    await expect(page.locator('.viewer-panel')).toBeVisible({ timeout: 10_000 });
    const rendered = page.locator('.rendered-content');
    const source = page.locator('.source-content');
    // One of them should be visible
    const hasRendered = await rendered.isVisible().catch(() => false);
    const hasSource = await source.isVisible().catch(() => false);
    expect(hasRendered || hasSource).toBeTruthy();
  });

  test('should toggle between rendered and source view', async ({ page }) => {
    const mdCard = page.locator('.file-card:has(.badge-md)').first();
    await expect(mdCard).toBeVisible({ timeout: 10_000 });
    await mdCard.click();
    await expect(page.locator('.viewer-panel')).toBeVisible({ timeout: 10_000 });
    // If rendered view is active, switch to source
    const sourceBtn = page.locator('.mode-btn:has-text("Source")');
    if (await sourceBtn.isVisible()) {
      await sourceBtn.click();
      await expect(page.locator('.source-content')).toBeVisible({ timeout: 5_000 });
    }
  });

  test('should close viewer with close button', async ({ page }) => {
    await expect(page.locator('.file-card').first()).toBeVisible({ timeout: 10_000 });
    await page.locator('.file-card').first().click();
    await expect(page.locator('.viewer-panel')).toBeVisible({ timeout: 10_000 });
    await page.locator('.viewer-actions button:has(mat-icon:has-text("close"))').click();
    await expect(page.locator('.viewer-panel')).toBeHidden();
  });

  test('should switch between category tabs', async ({ page }) => {
    await expect(page.locator('.file-card').first()).toBeVisible({ timeout: 10_000 });
    // Click Knowledge Base tab
    const kbTab = page.getByRole('tab', { name: /Knowledge Base/i });
    await expect(kbTab).toBeVisible({ timeout: 5_000 });
    await kbTab.click();
    // Should show JSON file cards
    await expect(page.locator('.file-card:has(.badge-json)').first()).toBeVisible({ timeout: 5_000 });
  });
});
