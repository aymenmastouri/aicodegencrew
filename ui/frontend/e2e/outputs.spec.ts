import { test, expect } from '@playwright/test';

test.describe('Outputs', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/outputs');
  });

  test('should render page with title and icon', async ({ page }) => {
    const title = page.locator('.page-title');
    await expect(title).toBeVisible();
    await expect(title).toContainText('Outputs');
  });

  test('should show filter bar with phase dropdown and search', async ({ page }) => {
    await expect(page.locator('.filter-bar')).toBeVisible();
    await expect(page.locator('mat-select')).toBeVisible();
    await expect(page.locator('input[matInput]')).toBeVisible();
  });

  test('should show split layout with file list and viewer', async ({ page }) => {
    await expect(page.locator('.split-layout')).toBeVisible({ timeout: 10_000 });
    await expect(page.locator('.file-list')).toBeVisible();
    await expect(page.locator('.content-viewer')).toBeVisible();
  });

  test('should show empty viewer message when no file selected', async ({ page }) => {
    await expect(page.locator('.viewer-empty')).toBeVisible({ timeout: 10_000 });
    await expect(page.locator('.viewer-empty')).toContainText('Select a file');
  });

  test('should select a file and show content', async ({ page }) => {
    await expect(page.locator('.split-layout')).toBeVisible({ timeout: 10_000 });
    const fileItems = page.locator('.file-item');
    const count = await fileItems.count();
    if (count > 0) {
      await fileItems.first().click();
      await expect(page.locator('.viewer-header')).toBeVisible({ timeout: 10_000 });
      await expect(page.locator('.viewer-body')).toBeVisible();
    }
  });

  test('should show copy and download buttons when file is selected', async ({ page }) => {
    await expect(page.locator('.split-layout')).toBeVisible({ timeout: 10_000 });
    const fileItems = page.locator('.file-item');
    const count = await fileItems.count();
    if (count > 0) {
      await fileItems.first().click();
      await expect(page.locator('button[matTooltip="Copy to clipboard"]')).toBeVisible({ timeout: 10_000 });
      await expect(page.locator('button[matTooltip="Download file"]')).toBeVisible();
    }
  });

  test('should be reachable from sidenav', async ({ page }) => {
    await page.goto('/dashboard');
    const navItem = page.locator('a[href="/outputs"]');
    await expect(navItem).toBeVisible();
    await navItem.click();
    await page.waitForURL('**/outputs');
    expect(page.url()).toContain('/outputs');
  });
});
