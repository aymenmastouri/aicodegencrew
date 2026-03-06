import { test, expect, Page } from '@playwright/test';

async function pause(page: Page, ms = 800) {
  await page.waitForTimeout(ms);
}

async function showSubtitle(page: Page, text: string, durationMs = 3000) {
  await page.evaluate((t) => {
    document.getElementById('demo-subtitle')?.remove();
    const el = document.createElement('div');
    el.id = 'demo-subtitle';
    el.textContent = t;
    Object.assign(el.style, {
      position: 'fixed', bottom: '32px', left: '50%', transform: 'translateX(-50%)',
      background: 'rgba(0,0,0,0.82)', color: '#fff', padding: '14px 32px',
      borderRadius: '10px', fontSize: '20px', fontFamily: 'system-ui, sans-serif',
      fontWeight: '500', zIndex: '99999', maxWidth: '80%', textAlign: 'center',
      boxShadow: '0 4px 24px rgba(0,0,0,0.3)',
    });
    document.body.appendChild(el);
  }, text);
  await pause(page, durationMs);
}

async function hideSubtitle(page: Page) {
  await page.evaluate(() => document.getElementById('demo-subtitle')?.remove());
}

test('Debug subtitle on dashboard', async ({ page }) => {
  test.setTimeout(120_000);

  await page.goto('/dashboard');
  await expect(page.locator('.hero, mat-toolbar').first()).toBeVisible({ timeout: 15_000 });

  await pause(page, 2000);
  await showSubtitle(page, 'TEST — Can you see this subtitle?', 5000);
  await hideSubtitle(page);

  await pause(page, 1000);
  await showSubtitle(page, 'Second subtitle — if you see this, subtitles work!', 5000);
  await hideSubtitle(page);

  await pause(page, 2000);
});
