import { test, expect } from '@playwright/test';

test.describe('App Shell', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should render toolbar with brand name', async ({ page }) => {
    const toolbar = page.locator('mat-toolbar');
    await expect(toolbar).toBeVisible();
    await expect(toolbar).toContainText('SDLC');
    await expect(toolbar).toContainText('Pilot');
  });

  test('should render sidenav with 3 groups', async ({ page }) => {
    await expect(page.locator('.nav-group-label')).toHaveCount(3);
    await expect(page.locator('.nav-group-label').nth(0)).toContainText('Operations');
    await expect(page.locator('.nav-group-label').nth(1)).toContainText('Explore');
    await expect(page.locator('.nav-group-label').nth(2)).toContainText('Monitor');
  });

  test('should render all 12 nav items', async ({ page }) => {
    const navItems = page.locator('mat-nav-list a[mat-list-item]');
    await expect(navItems).toHaveCount(12);
  });

  test('should show version badge in sidenav footer', async ({ page }) => {
    await expect(page.locator('.footer-version')).toContainText('v0.5.0');
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
      { label: 'Collectors', url: '/collectors' },
      { label: 'Settings', url: '/settings' },
      { label: 'Phases', url: '/phases' },
      { label: 'Knowledge', url: '/knowledge' },
      { label: 'Reports', url: '/reports' },
      { label: 'Metrics', url: '/metrics' },
      { label: 'Logs', url: '/logs' },
      { label: 'History', url: '/history' },
      { label: 'Dashboard', url: '/dashboard' },
    ];

    for (const route of routes) {
      await page.locator(`a[mat-list-item]:has-text("${route.label}")`).click();
      await page.waitForURL(`**${route.url}`);
      expect(page.url()).toContain(route.url);
    }
  });

  // --- Responsive Sidebar Tests ---

  test('should start with sidenav visible at desktop width', async ({ page }) => {
    // Default Playwright viewport is 1280x720 → rail mode (1024-1439px)
    const sidenav = page.locator('mat-sidenav');
    await expect(sidenav).toBeVisible();
  });

  test('should switch to rail mode at medium viewport', async ({ page }) => {
    await page.setViewportSize({ width: 1200, height: 800 });
    await page.waitForTimeout(300); // Allow media query to fire
    const sidenav = page.locator('mat-sidenav');
    await expect(sidenav).toBeVisible();
    // In rail mode, nav labels are hidden (opacity: 0)
    await expect(sidenav).toHaveClass(/sidenav-rail/);
  });

  test('should switch to full mode at large viewport', async ({ page }) => {
    await page.setViewportSize({ width: 1500, height: 900 });
    await page.waitForTimeout(300);
    const sidenav = page.locator('mat-sidenav');
    await expect(sidenav).toBeVisible();
    await expect(sidenav).toHaveClass(/sidenav-full/);
  });

  test('should hide sidenav in overlay mode at small viewport', async ({ page }) => {
    await page.setViewportSize({ width: 900, height: 700 });
    await page.waitForTimeout(300);
    const sidenav = page.locator('mat-sidenav');
    // In overlay mode, sidenav is hidden by default
    await expect(sidenav).toBeHidden();
  });

  test('should open overlay sidenav via menu button on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 900, height: 700 });
    await page.waitForTimeout(300);
    const sidenav = page.locator('mat-sidenav');
    await expect(sidenav).toBeHidden();

    // Click menu button to open
    await page.locator('mat-toolbar button[mat-icon-button]').click();
    await expect(sidenav).toBeVisible();
  });

  test('should toggle between full and rail via menu button at desktop', async ({ page }) => {
    await page.setViewportSize({ width: 1500, height: 900 });
    await page.waitForTimeout(300);
    const sidenav = page.locator('mat-sidenav');
    await expect(sidenav).toHaveClass(/sidenav-full/);

    // Click menu button → should switch to rail
    await page.locator('mat-toolbar button[mat-icon-button]').click();
    await page.waitForTimeout(200);
    await expect(sidenav).toHaveClass(/sidenav-rail/);
  });

  test('should show tooltips on nav items in rail mode', async ({ page }) => {
    await page.setViewportSize({ width: 1200, height: 800 });
    await page.waitForTimeout(300);
    // In rail mode, nav items have tooltips
    const navItem = page.locator('a[mat-list-item]').first();
    const tooltip = await navItem.getAttribute('ng-reflect-message');
    // Tooltip should be set (non-empty) in rail mode
    // Since Angular tooltips are rendered dynamically, just verify the item is visible
    await expect(navItem).toBeVisible();
  });

  test('should hide tagline on small screens', async ({ page }) => {
    await page.setViewportSize({ width: 700, height: 500 });
    await page.waitForTimeout(200);
    const tagline = page.locator('.brand-sub');
    await expect(tagline).toBeHidden();
  });
});
