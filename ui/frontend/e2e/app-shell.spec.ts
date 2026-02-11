import { test, expect } from '@playwright/test';

test.describe('App Shell', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should render toolbar with brand name', async ({ page }) => {
    const toolbar = page.locator('mat-toolbar');
    await expect(toolbar).toBeVisible();
    await expect(toolbar).toContainText('AICodeGenCrew');
    await expect(toolbar).toContainText('SDLC Dashboard');
  });

  test('should render sidenav with 3 groups', async ({ page }) => {
    await expect(page.locator('.nav-group-label')).toHaveCount(3);
    await expect(page.locator('.nav-group-label').nth(0)).toContainText('Operations');
    await expect(page.locator('.nav-group-label').nth(1)).toContainText('Explore');
    await expect(page.locator('.nav-group-label').nth(2)).toContainText('Monitor');
  });

  test('should render all 8 nav items', async ({ page }) => {
    const navItems = page.locator('mat-nav-list a[mat-list-item]');
    await expect(navItems).toHaveCount(8);
  });

  test('should show version badge in sidenav footer', async ({ page }) => {
    await expect(page.locator('.version-badge')).toContainText('v0.3.0');
  });

  test('should highlight active nav item', async ({ page }) => {
    await page.waitForURL('**/dashboard');
    const activeLink = page.locator('.active-link');
    await expect(activeLink).toHaveCount(1);
    await expect(activeLink).toContainText('Dashboard');
  });

  test('should navigate to all pages via sidenav', async ({ page }) => {
    const routes = [
      { label: 'Run Pipeline', url: '/run' },
      { label: 'Input Files', url: '/inputs' },
      { label: 'Phases', url: '/phases' },
      { label: 'Knowledge', url: '/knowledge' },
      { label: 'Reports', url: '/reports' },
      { label: 'Metrics', url: '/metrics' },
      { label: 'Logs', url: '/logs' },
      { label: 'Dashboard', url: '/dashboard' },
    ];

    for (const route of routes) {
      await page.locator(`a[mat-list-item]:has-text("${route.label}")`).click();
      await page.waitForURL(`**${route.url}`);
      expect(page.url()).toContain(route.url);
    }
  });

  test('should toggle sidenav with menu button', async ({ page }) => {
    const sidenav = page.locator('mat-sidenav');
    await expect(sidenav).toBeVisible();

    await page.locator('mat-toolbar button[mat-icon-button]').click();
    await expect(sidenav).toBeHidden();

    await page.locator('mat-toolbar button[mat-icon-button]').click();
    await expect(sidenav).toBeVisible();
  });
});
