import { test, Page } from '@playwright/test';

async function pause(page: Page, ms = 800) {
  await page.waitForTimeout(ms);
}

test('Debug Chapter 4 - preset + parallel + tasks + run', async ({ page }) => {
  test.setTimeout(60_000);

  await page.goto('/run');
  await pause(page, 3000); // Wait for async loading

  // 1. Select preset (retry if not loaded)
  console.log('--- Step 1: Select preset ---');
  const select = page.locator('.config-card mat-select');
  await select.waitFor({ state: 'visible', timeout: 5_000 });

  let presetOk = false;
  for (let i = 0; i < 3 && !presetOk; i++) {
    await select.click();
    await pause(page, 1500);
    const opts = await page.locator('mat-option').allTextContents();
    console.log(`Attempt ${i + 1} options:`, opts);
    const opt = page.locator('mat-option').filter({ hasText: /Triage/i }).first();
    if (await opt.isVisible({ timeout: 2_000 }).catch(() => false)) {
      await opt.click();
      presetOk = true;
      console.log('Preset selected!');
    } else {
      await page.keyboard.press('Escape');
      await pause(page, 2000);
    }
  }

  await pause(page, 1000);

  // 2. Enable parallel
  console.log('--- Step 2: Enable parallel ---');
  const parallelSection = page.locator('.parallel-section');
  console.log('parallel visible:', await parallelSection.isVisible().catch(() => false));

  const toggle = parallelSection.locator('mat-slide-toggle').first();
  if (await toggle.isVisible({ timeout: 3_000 }).catch(() => false)) {
    await toggle.click();
    await pause(page, 1500);
    console.log('toggle clicked');
  }

  // 3. Check tasks
  console.log('--- Step 3: Check tasks ---');
  const selectedCount = await page.locator('.task-chip.selected').count();
  console.log('selected tasks:', selectedCount);

  if (selectedCount === 0) {
    const selectAllBtn = page.locator('.task-picker-toggle');
    if (await selectAllBtn.isVisible({ timeout: 2_000 }).catch(() => false)) {
      await selectAllBtn.click();
      await pause(page, 1000);
      console.log('clicked Select all');
    }
  }

  const finalSelected = await page.locator('.task-chip.selected').count();
  console.log('final selected tasks:', finalSelected);

  // 4. Run
  console.log('--- Step 4: Run ---');
  const runBtn = page.locator('button.run-btn');
  const disabled = await runBtn.isDisabled();
  console.log('run-btn disabled:', disabled);
  await runBtn.focus();
  await page.keyboard.press('Enter');
  await pause(page, 3000);

  const resp = await page.request.get('http://localhost:4200/api/pipeline/status');
  const data = await resp.json();
  console.log('State:', data.state);
  console.log('Task progress:', JSON.stringify(data.task_progress || {}));

  if (data.state === 'idle') {
    console.log('--- Fallback: API ---');
    await page.request.post('http://localhost:4200/api/pipeline/run', {
      data: { phases: ['triage', 'plan'], task_ids: ['BNUVZ-12529', 'BNUVZ-12568'], max_parallel: 2 },
    });
    await pause(page, 2000);
    const r2 = await page.request.get('http://localhost:4200/api/pipeline/status');
    const d2 = await r2.json();
    console.log('State after API:', d2.state);
  }
});
