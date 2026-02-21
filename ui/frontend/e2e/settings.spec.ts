import { test, expect } from '@playwright/test';

test.describe('Settings', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/settings');
  });

  test('should render page with title and icon', async ({ page }) => {
    const title = page.locator('.page-title');
    await expect(title).toBeVisible();
    await expect(title).toContainText('Settings');
  });

  test('should render at least 4 tabs including Phases', async ({ page }) => {
    // Wait for tabs to render (settings loads config async before showing tabs)
    await expect(page.locator('.mat-mdc-tab').first()).toBeVisible({ timeout: 10_000 });
    const tabs = page.locator('.mat-mdc-tab');
    const count = await tabs.count();
    expect(count).toBeGreaterThanOrEqual(4);
    // Phases tab is always rendered (not conditional on env vars)
    await expect(page.locator('.mat-mdc-tab:has-text("Phases")')).toBeVisible();
  });

  test('should show form fields in General tab', async ({ page }) => {
    await expect(page.locator('.tab-body')).toBeVisible({ timeout: 10_000 });
    const fields = page.locator('mat-form-field');
    const count = await fields.count();
    expect(count).toBeGreaterThanOrEqual(1);
  });

  test('should show Save button in General tab', async ({ page }) => {
    await expect(page.locator('.tab-body')).toBeVisible({ timeout: 10_000 });
    await expect(page.locator('.tab-actions button:has-text("Save")')).toBeVisible();
  });

  test('should switch to LLM tab', async ({ page }) => {
    await page.locator('.mat-mdc-tab:has-text("LLM")').click();
    // Multiple .tab-description elements exist in DOM (one per tab) — filter to the LLM one
    await expect(page.locator('.tab-description').filter({ hasText: 'Language model' })).toContainText('Language model');
  });

  test('should switch to Phases tab and show phase toggles', async ({ page }) => {
    await page.locator('.mat-mdc-tab:has-text("Phases")').click();
    await expect(page.locator('.phase-toggle-grid')).toBeVisible({ timeout: 10_000 });
  });

  test('should be reachable from sidenav', async ({ page }) => {
    await page.goto('/dashboard');
    // Scope to mat-nav-list to avoid matching other Settings links on the page
    const navItem = page.locator('mat-nav-list a[href="/settings"]');
    await expect(navItem).toBeVisible();
    await navItem.click();
    await page.waitForURL('**/settings');
    expect(page.url()).toContain('/settings');
  });
});

// ─── Phase Enable/Disable Feature ────────────────────────────────────────────
// The Phases tab in Settings shows a mat-slide-toggle for each pipeline phase.
// DESIGN: Toggles are display-only — they reflect the enabled state loaded from
// GET /api/phases but there is no Save button and no API call persists changes.
// The source of truth is phases_config.yaml (read-only at runtime).
// ─────────────────────────────────────────────────────────────────────────────
test.describe('Settings - Phases Tab', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/settings');
    await page.locator('.mat-mdc-tab:has-text("Phases")').click();
    await expect(page.locator('.phase-toggle-grid')).toBeVisible({ timeout: 10_000 });
  });

  test('should show tab description mentioning phases enable/disable', async ({ page }) => {
    // Multiple .tab-description elements exist in DOM (one per tab) — filter to the Phases one
    await expect(page.locator('.tab-description').filter({ hasText: 'Enable or disable pipeline phases' }))
      .toContainText('Enable or disable pipeline phases');
  });

  test('should show "Phase Toggles" section label', async ({ page }) => {
    await expect(page.locator('.section-label:has-text("Phase Toggles")')).toBeVisible();
  });

  test('should render at least 8 phase toggle cards', async ({ page }) => {
    const cards = page.locator('.phase-toggle-card');
    const count = await cards.count();
    expect(count).toBeGreaterThanOrEqual(8);
  });

  test('should display phase name and phase ID in each toggle card', async ({ page }) => {
    const firstCard = page.locator('.phase-toggle-card').first();
    await expect(firstCard.locator('.phase-toggle-name')).toBeVisible();
    await expect(firstCard.locator('.phase-toggle-id')).toBeVisible();
    const name = await firstCard.locator('.phase-toggle-name').textContent();
    expect(name?.trim().length).toBeGreaterThan(0);
    const id = await firstCard.locator('.phase-toggle-id').textContent();
    expect(id?.trim().length).toBeGreaterThan(0);
  });

  test('should have a mat-slide-toggle in every card', async ({ page }) => {
    const cards = page.locator('.phase-toggle-card');
    const cardCount = await cards.count();
    const toggleCount = await page.locator('.phase-toggle-card mat-slide-toggle').count();
    expect(toggleCount).toBe(cardCount);
  });

  test('should visually change toggle state when clicked', async ({ page }) => {
    // First 3 phases (discover, extract, analyze) are required and disabled — use index 3 (document)
    const optionalToggle = page.locator('.phase-toggle-card mat-slide-toggle').nth(3);
    const toggleBtn = optionalToggle.locator('button[role="switch"]');
    const initialState = await toggleBtn.getAttribute('aria-checked');
    await optionalToggle.click();
    const newState = await toggleBtn.getAttribute('aria-checked');
    // State must have flipped (true→false or false→true)
    expect(newState).not.toBe(initialState);
  });

  test('should have a Save Phases button in the Phases tab', async ({ page }) => {
    // The Phases tab has a "Save Phases" button (unique text avoids matching other tabs' "Save" buttons)
    const saveBtn = page.locator('button:has-text("Save Phases")');
    await expect(saveBtn).toBeVisible();
  });

  test('should show discover phase toggle card with correct ID', async ({ page }) => {
    const discoverCard = page.locator('.phase-toggle-card').filter({
      has: page.locator('.phase-toggle-id:has-text("discover")'),
    });
    await expect(discoverCard).toBeVisible();
    await expect(discoverCard.locator('.phase-toggle-name')).toContainText('Discover');
  });

  test('should show implement phase toggle card', async ({ page }) => {
    const implementCard = page.locator('.phase-toggle-card').filter({
      has: page.locator('.phase-toggle-id:has-text("implement")'),
    });
    await expect(implementCard).toBeVisible();
    await expect(implementCard.locator('mat-slide-toggle')).toBeVisible();
  });

  test('should show "Presets" section label', async ({ page }) => {
    await expect(page.locator('.section-label:has-text("Presets")')).toBeVisible();
  });

  test('should show preset cards with icon, name, and description', async ({ page }) => {
    const presetCards = page.locator('.preset-card');
    const count = await presetCards.count();
    expect(count).toBeGreaterThanOrEqual(1);
    const firstPreset = presetCards.first();
    await expect(firstPreset.locator('mat-icon.preset-icon')).toBeVisible();
    await expect(firstPreset.locator('.preset-name')).toBeVisible();
    const presetName = await firstPreset.locator('.preset-name').textContent();
    expect(presetName?.trim().length).toBeGreaterThan(0);
  });

  test('should show preset phases list in each preset card', async ({ page }) => {
    const firstPreset = page.locator('.preset-card').first();
    await expect(firstPreset.locator('.preset-phases')).toBeVisible();
    const phases = await firstPreset.locator('.preset-phases').textContent();
    expect(phases?.trim().length).toBeGreaterThan(0);
  });

  test('should toggle multiple phases independently', async ({ page }) => {
    const toggleBtns = page.locator('.phase-toggle-card mat-slide-toggle button[role="switch"]');
    const count = await toggleBtns.count();
    expect(count).toBeGreaterThanOrEqual(5);

    // First 3 phases (discover, extract, analyze) are required/disabled — use indices 3 and 4
    const state3Before = await toggleBtns.nth(3).getAttribute('aria-checked');
    const state4Before = await toggleBtns.nth(4).getAttribute('aria-checked');

    // Toggle only index 3 (document phase)
    await page.locator('.phase-toggle-card mat-slide-toggle').nth(3).click();

    const state3After = await toggleBtns.nth(3).getAttribute('aria-checked');
    const state4After = await toggleBtns.nth(4).getAttribute('aria-checked');

    // Index 3 should have flipped, index 4 should remain unchanged
    expect(state3After).not.toBe(state3Before);
    expect(state4After).toBe(state4Before);
  });
});
