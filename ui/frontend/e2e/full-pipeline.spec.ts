import { test, expect } from '@playwright/test';

/**
 * Full Pipeline E2E Test
 *
 * Tests the complete user flow through the SDLC Dashboard:
 *   Dashboard → Input Files → Run Pipeline → Monitor → Results
 *
 * Indexing (Phase 0) is skipped by default because it takes 2-10 minutes.
 * To include indexing, set env INCLUDE_INDEXING=true.
 */

const SKIP_INDEXING = process.env['INCLUDE_INDEXING'] !== 'true';

test.describe('Full Pipeline Flow', () => {
  test.describe.configure({ timeout: 120_000 });

  // ── 1. Dashboard Health ──────────────────────────────────

  test('1 - Dashboard loads and backend is healthy', async ({ page }) => {
    await page.goto('/dashboard');
    const hero = page.locator('.hero');
    await expect(hero).toBeVisible();
    await expect(hero).toContainText('SDLC');

    // Backend health pill should be visible (status shown via CSS class, not text)
    const healthPill = page.locator('.stat-pill:has-text("Backend")');
    await expect(healthPill).toBeVisible({ timeout: 15_000 });
    await expect(healthPill).toHaveClass(/stat-ok/, { timeout: 5_000 });
  });

  // ── 2. Sidenav has all pages ─────────────────────────────

  test('2 - Sidenav shows all 12 navigation items', async ({ page }) => {
    await page.goto('/dashboard');
    const navItems = page.locator('mat-nav-list a[mat-list-item]');
    await expect(navItems).toHaveCount(12);

    // Verify key pages exist — scope to mat-nav-list to avoid onboarding card links
    await expect(page.locator('mat-nav-list a[href="/inputs"]')).toBeVisible();
    await expect(page.locator('mat-nav-list a[href="/run"]')).toBeVisible();
    await expect(page.locator('mat-nav-list a[href="/knowledge"]')).toBeVisible();
  });

  // ── 3. Input Files page ──────────────────────────────────

  test('3 - Input Files page renders 4 categories', async ({ page }) => {
    await page.goto('/inputs');
    const cards = page.locator('.category-card');
    await expect(cards).toHaveCount(4, { timeout: 10_000 });

    // Verify each category
    await expect(page.locator('.category-card:has-text("Task Files")')).toBeVisible();
    await expect(page.locator('.category-card:has-text("Requirements")')).toBeVisible();
    await expect(page.locator('.category-card:has-text("Application Logs")')).toBeVisible();
    await expect(page.locator('.category-card:has-text("Reference Materials")')).toBeVisible();

    // Drop zones present
    const dropZones = page.locator('.drop-zone');
    await expect(dropZones).toHaveCount(4);
  });

  test('4 - Input Files rejects invalid file extension', async ({ page }) => {
    await page.goto('/inputs');
    await expect(page.locator('.category-card').first()).toBeVisible({ timeout: 10_000 });

    // Create a fake .exe file and try to upload to Tasks
    const taskCard = page.locator('.category-card:has-text("Task Files")');
    const fileInput = taskCard.locator('input[type="file"]');

    // Set a .exe file (should be rejected by backend)
    await fileInput.setInputFiles({
      name: 'malware.exe',
      mimeType: 'application/octet-stream',
      buffer: Buffer.from('fake content'),
    });

    // Should show error snackbar or error message
    const errorIndicator = page.locator('.mat-mdc-snack-bar-container, .error-msg');
    await expect(errorIndicator.first()).toBeVisible({ timeout: 5_000 });
  });

  test('5 - Input Files accepts valid file upload', async ({ page }) => {
    await page.goto('/inputs');
    await expect(page.locator('.category-card').first()).toBeVisible({ timeout: 10_000 });

    const taskCard = page.locator('.category-card:has-text("Task Files")');
    const fileInput = taskCard.locator('input[type="file"]');

    // Upload a valid .txt file
    await fileInput.setInputFiles({
      name: 'test-task.txt',
      mimeType: 'text/plain',
      buffer: Buffer.from('Test task description for E2E testing'),
    });

    // Should show success snackbar
    const snackbar = page.locator('.mat-mdc-snack-bar-container');
    await expect(snackbar).toBeVisible({ timeout: 5_000 });
    await expect(snackbar).toContainText('Uploaded');

    // File should appear in file list
    await expect(taskCard.locator('.file-name:has-text("test-task.txt")')).toBeVisible({ timeout: 5_000 });
  });

  test('6 - Input Files can delete uploaded file', async ({ page }) => {
    await page.goto('/inputs');
    await expect(page.locator('.category-card').first()).toBeVisible({ timeout: 10_000 });

    const taskCard = page.locator('.category-card:has-text("Task Files")');

    // If test-task.txt exists from previous test, delete it
    const deleteBtn = taskCard.locator('.file-row:has-text("test-task") button');
    if (await deleteBtn.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await deleteBtn.click();
      const snackbar = page.locator('.mat-mdc-snack-bar-container');
      await expect(snackbar).toBeVisible({ timeout: 5_000 });
      await expect(snackbar).toContainText('Deleted');
    }
  });

  // ── 4. Run Pipeline page ─────────────────────────────────

  test('7 - Run Pipeline shows Input Files section in Advanced Options', async ({ page }) => {
    await page.goto('/run');
    // Input Files summary is inside the Advanced Options expansion panel
    await page.locator('mat-expansion-panel-header:has-text("Advanced Options")').click();
    await expect(page.locator('.advanced-section-title:has-text("Input Files")').first()).toBeVisible({ timeout: 10_000 });

    // Should have a Manage Files link
    const manageBtn = page.locator('a.manage-btn:has-text("Manage Files")');
    await expect(manageBtn).toBeVisible();
  });

  test('8 - Run Pipeline Manage Files link navigates to inputs', async ({ page }) => {
    await page.goto('/run');
    await page.locator('mat-expansion-panel-header:has-text("Advanced Options")').click();
    const manageBtn = page.locator('a.manage-btn:has-text("Manage Files")');
    await expect(manageBtn).toBeVisible({ timeout: 10_000 });
    await manageBtn.click();
    await page.waitForURL('**/inputs');
    expect(page.url()).toContain('/inputs');
  });

  test('9 - Run Pipeline can select preset', async ({ page }) => {
    await page.goto('/run');
    await page.locator('mat-select').first().click();
    const options = page.locator('mat-option');
    await expect(options.first()).toBeVisible({ timeout: 10_000 });

    // Select scan (no LLM needed, fast)
    const factsOption = page.locator('mat-option:has-text("Facts Extraction")');
    if (await factsOption.isVisible().catch(() => false)) {
      await factsOption.click();
    } else {
      await options.first().click();
    }

    const runButton = page.locator('button:has-text("Run Pipeline")').first();
    await expect(runButton).toBeEnabled({ timeout: 5_000 });
  });

  test('10 - Run Pipeline custom phases: can select and deselect', async ({ page }) => {
    await page.goto('/run');
    // Wait for config card before switching tabs
    await expect(page.locator('.config-card')).toBeVisible({ timeout: 10_000 });
    // Switch to custom phases tab
    await page.locator('.mat-mdc-tab').nth(1).click();

    // Wait for phase checkboxes to render
    const checkboxes = page.locator('.phase-checkboxes mat-checkbox');
    await expect(checkboxes.first()).toBeVisible({ timeout: 5_000 });

    // Click the label — visible & properly routed through Angular Material's change detection
    const phase1Label = checkboxes.first().locator('label');

    // Select first phase
    await phase1Label.click();
    const runButton = page.locator('button:has-text("Run Pipeline")').first();
    await expect(runButton).toBeEnabled({ timeout: 3_000 });

    // Deselect
    await phase1Label.click();
    await expect(runButton).toBeDisabled({ timeout: 5_000 });
  });

  // ── 5. Explore pages load ────────────────────────────────

  test('11 - Phases page loads with all phases', async ({ page }) => {
    await page.goto('/phases');
    await expect(page.locator('.page-title')).toContainText('Phases');
  });

  test('12 - Knowledge page loads', async ({ page }) => {
    await page.goto('/knowledge');
    await expect(page.locator('.page-title')).toContainText('Knowledge');
  });

  test('13 - Reports page loads', async ({ page }) => {
    await page.goto('/reports');
    await expect(page.locator('.page-title')).toContainText('Reports');
  });

  // ── 6. Monitor pages load ────────────────────────────────

  test('14 - Metrics page loads', async ({ page }) => {
    await page.goto('/metrics');
    await expect(page.locator('.page-title')).toContainText('Metrics');
  });

  test('15 - Logs page loads', async ({ page }) => {
    await page.goto('/logs');
    await expect(page.locator('.page-title')).toContainText('Logs');
  });

  // ── 7. Advanced Options panel ─────────────────────────────

  test('16 - Run Pipeline Advanced Options panel expands and shows sections', async ({ page }) => {
    await page.goto('/run');
    const header = page.locator('mat-expansion-panel-header:has-text("Advanced Options")');
    await expect(header).toBeVisible({ timeout: 10_000 });
    await header.click();

    // Input Files section is always present
    await expect(page.locator('.advanced-section-title:has-text("Input Files")').first()).toBeVisible({ timeout: 5_000 });

    // Environment Overrides section is conditional on env groups being configured
    const envFields = page.locator('.env-fields').first();
    if (await envFields.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await expect(page.locator('.env-group-title').first()).toBeVisible();
    }
  });

  // ── 8. Full run (skip indexing unless opted in) ──────────

  test('17 - Execute scan preset and monitor output', async ({ page }) => {
    // This test actually runs a pipeline - only meaningful with a backend
    // that has a configured PROJECT_PATH. Skip if backend is not fully set up.
    test.skip(SKIP_INDEXING, 'Skipped: indexing takes 2-10 min. Set INCLUDE_INDEXING=true to enable.');

    await page.goto('/run');

    // Select scan preset
    await page.locator('mat-select').first().click();
    const factsOption = page.locator('mat-option:has-text("Facts Extraction")');
    await expect(factsOption).toBeVisible({ timeout: 10_000 });
    await factsOption.click();

    // Run
    const runButton = page.locator('button:has-text("Run Pipeline")').first();
    await expect(runButton).toBeEnabled({ timeout: 5_000 });
    await runButton.click();

    // Should show running state
    await expect(page.locator('.status-card')).toBeVisible({ timeout: 10_000 });

    // Wait for log output to appear
    await expect(page.locator('.log-viewer')).toBeVisible({ timeout: 30_000 });
    const logLines = page.locator('.log-line');
    await expect(logLines.first()).toBeVisible({ timeout: 30_000 });

    // Wait for completion (up to 10 min for indexing + facts)
    await expect(page.locator('.status-chip:has-text("completed"), .status-chip:has-text("failed")')).toBeVisible({
      timeout: 600_000,
    });
  });

  // ── 9. Cross-page navigation flow ───────────────────────

  test('18 - Complete navigation flow: Dashboard → Inputs → Run → Knowledge', async ({ page }) => {
    // Start at dashboard
    await page.goto('/dashboard');
    await expect(page.locator('.hero')).toBeVisible();

    // Navigate to Input Files via sidenav — scope to mat-nav-list to avoid onboarding card links
    await page.locator('mat-nav-list a[href="/inputs"]').click();
    await page.waitForURL('**/inputs');
    await expect(page.locator('.category-card')).toHaveCount(4, { timeout: 10_000 });

    // Navigate to Run Pipeline via sidenav
    await page.locator('a[href="/run"]').click();
    await page.waitForURL('**/run');

    // Expand Advanced Options to access Input Files and Manage Files link
    await page.locator('mat-expansion-panel-header:has-text("Advanced Options")').click();
    await expect(page.locator('.advanced-section-title:has-text("Input Files")').first()).toBeVisible({ timeout: 10_000 });

    // Click "Manage Files" to go back to inputs
    await page.locator('a.manage-btn:has-text("Manage Files")').click();
    await page.waitForURL('**/inputs');

    // Navigate to Knowledge
    await page.locator('a[href="/knowledge"]').click();
    await page.waitForURL('**/knowledge');
    await expect(page.locator('.page-title')).toContainText('Knowledge');
  });
});
