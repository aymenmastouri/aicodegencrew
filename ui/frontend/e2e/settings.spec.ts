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

  test('should render 5 tabs', async ({ page }) => {
    const tabs = page.locator('.mat-mdc-tab');
    await expect(tabs).toHaveCount(5);
    await expect(tabs.nth(0)).toContainText('General');
    await expect(tabs.nth(1)).toContainText('LLM');
    await expect(tabs.nth(2)).toContainText('Indexing');
    await expect(tabs.nth(3)).toContainText('Phases');
    await expect(tabs.nth(4)).toContainText('Advanced');
  });

  test('should show form fields in General tab', async ({ page }) => {
    await expect(page.locator('.tab-content')).toBeVisible({ timeout: 10_000 });
    const fields = page.locator('mat-form-field');
    const count = await fields.count();
    expect(count).toBeGreaterThanOrEqual(1);
  });

  test('should show save and reset buttons', async ({ page }) => {
    await expect(page.locator('.tab-content')).toBeVisible({ timeout: 10_000 });
    await expect(page.locator('button:has-text("Save")')).toBeVisible();
    await expect(page.locator('button:has-text("Reset to defaults")')).toBeVisible();
  });

  test('should switch to LLM tab', async ({ page }) => {
    await page.locator('.mat-mdc-tab:has-text("LLM")').click();
    await expect(page.locator('.tab-description')).toContainText('Language model');
  });

  test('should switch to Phases tab and show phase toggles', async ({ page }) => {
    await page.locator('.mat-mdc-tab:has-text("Phases")').click();
    await expect(page.locator('.phase-toggle-grid')).toBeVisible({ timeout: 10_000 });
  });

  test('should be reachable from sidenav', async ({ page }) => {
    await page.goto('/dashboard');
    const navItem = page.locator('a[href="/settings"]');
    await expect(navItem).toBeVisible();
    await navItem.click();
    await page.waitForURL('**/settings');
    expect(page.url()).toContain('/settings');
  });
});
