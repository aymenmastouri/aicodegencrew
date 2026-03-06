import { test, expect } from '@playwright/test';

test('Debug Chapter 4 - run pipeline', async ({ page }) => {
  test.setTimeout(60_000);

  await page.goto('/run');
  await page.waitForTimeout(3000);

  // Log page state
  const configVisible = await page.locator('.config-card').isVisible();
  const state = await page.request.get('http://localhost:4200/api/pipeline/status')
    .then(r => r.json()).then(d => d.state).catch(() => 'error');
  console.log('config-card visible:', configVisible, '| pipeline state:', state);

  // Wait for select
  const select = page.locator('.config-card mat-select');
  await select.waitFor({ state: 'visible', timeout: 10_000 });
  console.log('mat-select found');
  await select.click();
  await page.waitForTimeout(1500);

  // Log all options
  const options = await page.locator('mat-option').allTextContents();
  console.log('Options:', options);

  // Click triage option
  const opt = page.locator('mat-option').filter({ hasText: /triage/i }).first();
  const optVisible = await opt.isVisible().catch(() => false);
  console.log('triage option visible:', optVisible);
  if (optVisible) {
    await opt.click();
    await page.waitForTimeout(1000);
    console.log('clicked triage option');
  }

  // Check parallel section
  const parallel = await page.locator('.parallel-section').isVisible().catch(() => false);
  console.log('parallel-section visible:', parallel);

  // Check run button
  const runBtn = page.locator('button.run-btn');
  const runBtnVisible = await runBtn.isVisible().catch(() => false);
  const runBtnDisabled = await runBtn.isDisabled().catch(() => true);
  console.log('run-btn visible:', runBtnVisible, '| disabled:', runBtnDisabled);

  await page.waitForTimeout(5000);
});
