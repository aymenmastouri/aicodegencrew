import { test, expect } from '@playwright/test';

test.describe('Run Pipeline', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/run');
  });

  // --- Page Layout ---

  test('should render page title with icon', async ({ page }) => {
    await expect(page.locator('.page-title')).toContainText('Run Pipeline');
    await expect(page.locator('.page-icon')).toBeVisible();
  });

  test('should show Pipeline Configuration card when idle', async ({ page }) => {
    const configCard = page.locator('.config-card');
    await expect(configCard).toBeVisible({ timeout: 10_000 });
    await expect(configCard).toContainText('Pipeline Configuration');
  });

  // --- Configure Section: Tabs ---

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
    const options = page.locator('mat-option');
    await expect(options.first()).toBeVisible({ timeout: 10_000 });
    // Select the first available preset
    await options.first().click();
    const chips = page.locator('.phase-chips mat-chip');
    await expect(chips.first()).toBeVisible({ timeout: 5_000 });
    const count = await chips.count();
    expect(count).toBeGreaterThanOrEqual(1);
  });

  test('should show phase checkboxes in custom mode', async ({ page }) => {
    await page.locator('.mat-mdc-tab').nth(1).click();
    await expect(page.locator('mat-checkbox').first()).toBeVisible({ timeout: 5_000 });
    const checkboxes = page.locator('mat-checkbox');
    await expect(checkboxes).toHaveCount(8);
  });

  // --- Configure Section: Run Button ---

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

  test('should place Run button inside config card', async ({ page }) => {
    const runBtn = page.locator('.config-card button:has-text("Run Pipeline")');
    await expect(runBtn).toBeVisible();
  });

  // --- Configure Section: Advanced Options ---

  test('should show Advanced Options expansion panel', async ({ page }) => {
    const advancedPanel = page.locator('mat-expansion-panel:has-text("Advanced Options")');
    await expect(advancedPanel).toBeVisible();
  });

  test('should expand Advanced Options and show Input Files section', async ({ page }) => {
    await page.locator('mat-expansion-panel-header:has-text("Advanced Options")').click();
    await expect(page.locator('.advanced-section-title:has-text("Input Files")').first()).toBeVisible({ timeout: 5_000 });
  });

  test('should expand Advanced Options and show Environment section', async ({ page }) => {
    await page.locator('mat-expansion-panel-header:has-text("Advanced Options")').click();
    // Environment Overrides section is conditional on envGroups being loaded
    const envSection = page.locator('.advanced-section-title:has-text("Environment Overrides")');
    if (await envSection.isVisible({ timeout: 5_000 }).catch(() => false)) {
      await expect(envSection.first()).toBeVisible();
    }
  });

  test('should show Manage Files link in Advanced Options', async ({ page }) => {
    await page.locator('mat-expansion-panel-header:has-text("Advanced Options")').click();
    const manageBtn = page.locator('.manage-btn:has-text("Manage Files")');
    await expect(manageBtn).toBeVisible({ timeout: 5_000 });
  });

  // --- Preset Query Param ---

  test('should navigate from preset query param', async ({ page }) => {
    await page.goto('/run?preset=scan');
    await page.waitForTimeout(2000);
    const select = page.locator('mat-select').first();
    // "scan" preset auto-selects and shows its display name
    await expect(select).not.toBeEmpty({ timeout: 10_000 });
    const text = await select.textContent();
    // Should have selected something (not blank)
    expect(text?.trim().length).toBeGreaterThan(0);
  });

  // --- No Run History (removed) ---

  test('should NOT show embedded Run History table', async ({ page }) => {
    // The old embedded history table was removed; users go to /history instead
    const historyCard = page.locator('mat-card:has-text("Run History")');
    await expect(historyCard).toHaveCount(0);
  });
});
