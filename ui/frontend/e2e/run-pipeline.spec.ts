import { test, expect } from '@playwright/test';

test.describe('Run Pipeline', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/run');
  });

  test('should render page title with icon', async ({ page }) => {
    await expect(page.locator('.page-title')).toContainText('Run Pipeline');
    await expect(page.locator('.page-title mat-icon')).toBeVisible();
  });

  test('should display two tabs: Run Preset and Run Custom Phases', async ({ page }) => {
    await expect(page.locator('.mat-mdc-tab')).toHaveCount(2);
    await expect(page.locator('.mat-mdc-tab').first()).toContainText('Run Preset');
    await expect(page.locator('.mat-mdc-tab').nth(1)).toContainText('Run Custom Phases');
  });

  test('should load presets in dropdown', async ({ page }) => {
    await page.locator('mat-select').first().click();
    const options = page.locator('mat-option');
    await expect(options.first()).toBeVisible({ timeout: 10_000 });
    const count = await options.count();
    expect(count).toBeGreaterThanOrEqual(8);
  });

  test('should show phase chips when preset is selected', async ({ page }) => {
    await page.locator('mat-select').first().click();
    // Presets now show display names, select "Full SDLC Pipeline"
    await page.locator('mat-option:has-text("Full SDLC Pipeline")').click();
    const chips = page.locator('.phase-chips mat-chip');
    await expect(chips.first()).toBeVisible({ timeout: 5_000 });
    const count = await chips.count();
    expect(count).toBeGreaterThanOrEqual(4);
  });

  test('should show phase checkboxes in custom mode', async ({ page }) => {
    await page.locator('.mat-mdc-tab').nth(1).click();
    await expect(page.locator('mat-checkbox').first()).toBeVisible({ timeout: 5_000 });
    const checkboxes = page.locator('mat-checkbox');
    await expect(checkboxes).toHaveCount(8);
  });

  test('should disable Run button when nothing selected', async ({ page }) => {
    const runButton = page.locator('button:has-text("Run Pipeline")').first();
    await expect(runButton).toBeDisabled();
  });

  test('should enable Run button when preset is selected', async ({ page }) => {
    await page.locator('mat-select').first().click();
    await expect(page.locator('mat-option').first()).toBeVisible({ timeout: 10_000 });
    await page.locator('mat-option').first().click();
    const runButton = page.locator('button:has-text("Run Pipeline")').first();
    await expect(runButton).toBeEnabled({ timeout: 5_000 });
  });

  test('should disable Cancel button when not running', async ({ page }) => {
    const cancelButton = page.locator('button:has-text("Cancel")');
    await expect(cancelButton).toBeDisabled();
  });

  test('should show Environment Configuration expansion panel', async ({ page }) => {
    const envPanel = page.locator('mat-expansion-panel:has-text("Environment Configuration")');
    await expect(envPanel).toBeVisible();
  });

  test('should expand env config and show fields', async ({ page }) => {
    await page.locator('mat-expansion-panel-header:has-text("Environment Configuration")').click();
    await expect(page.locator('.env-fields').first()).toBeVisible({ timeout: 5_000 });
  });

  test('should show Run History section', async ({ page }) => {
    await expect(page.locator('mat-card:has-text("Run History")')).toBeVisible();
  });

  test('should show empty history message when no runs', async ({ page }) => {
    const emptyOrTable = page.locator('.empty-inline, .history-table');
    await expect(emptyOrTable.first()).toBeVisible({ timeout: 5_000 });
  });

  test('should navigate from preset query param', async ({ page }) => {
    await page.goto('/run?preset=facts_only');
    // Wait for presets to load and select to be populated
    await page.waitForTimeout(2000);
    const select = page.locator('mat-select').first();
    // Display name is "Facts Extraction" now
    await expect(select).toContainText('Facts Extraction', { timeout: 10_000 });
  });
});
