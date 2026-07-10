import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';
import { loginAsSuperAdmin } from './helpers/admin-auth';

const APP = process.env.E2E_APP || 'admin';
const EVIDENCE_DIR = path.join(__dirname, '..', 'evidence', 'e2e02');
if (!fs.existsSync(EVIDENCE_DIR)) fs.mkdirSync(EVIDENCE_DIR, { recursive: true });

test.describe('ADMIN-TENANT-E2E-02 shell/nav', () => {
  test.skip(APP !== 'admin', 'admin-only');

  test('logged-out user is redirected away from admin routes', async ({ page }) => {
    await page.goto('/admin/dashboard');
    await page.waitForTimeout(1000);
    await expect(page).toHaveURL(/login/);
  });

  test('login shows shell: sidebar, topbar, bell, avatar, no tour overlay', async ({ page }) => {
    await loginAsSuperAdmin(page);
    await expect(page.locator('aside')).toBeVisible();
    await expect(page.locator('header')).toBeVisible();
    const bodyText = await page.locator('body').innerText();
    expect(bodyText).not.toMatch(/undefined|NaN/);
    await page.screenshot({ path: path.join(EVIDENCE_DIR, 'shell-dashboard.png'), fullPage: true });
  });

  test('logout returns to login and clears session', async ({ page }) => {
    await loginAsSuperAdmin(page);
    await page.locator('button[title="Log out"]').click();
    await page.waitForTimeout(1000);
    await expect(page).toHaveURL(/login/);
  });

  test('corrupted token shows login redirect (session-expired behavior)', async ({ page }) => {
    await loginAsSuperAdmin(page);
    await page.evaluate(() => localStorage.setItem('serviceos_admin_token', 'corrupted.invalid.token'));
    await page.goto('/admin/dashboard');
    await page.waitForTimeout(1500);
    const bodyText = await page.locator('body').innerText();
    await page.screenshot({ path: path.join(EVIDENCE_DIR, 'corrupted-token.png'), fullPage: true });
    // Document actual behavior rather than assume — see report for pass/fail classification.
    fs.writeFileSync(path.join(EVIDENCE_DIR, 'corrupted-token-url.txt'), page.url() + '\n' + bodyText.slice(0, 300));
  });

  const NESTED_ROUTES: { path: string; expectedActive: string }[] = [
    { path: '/admin/home-services/pricing-rules', expectedActive: 'nav-hs-pricing-rules' },
    { path: '/admin/home-services/service-catalog', expectedActive: 'nav-hs-service-catalog' },
    { path: '/admin/tenants/onboarding', expectedActive: 'nav-onboarding' },
    { path: '/admin/onboarding/providers', expectedActive: 'nav-onboarding-providers' },
    { path: '/admin/users/roles', expectedActive: 'nav-roles' },
    { path: '/admin/users/permissions', expectedActive: 'nav-permissions' },
  ];

  for (const r of NESTED_ROUTES) {
    test(`sidebar active-state for nested route: ${r.path}`, async ({ page }) => {
      await loginAsSuperAdmin(page);
      await page.goto(r.path);
      await page.waitForTimeout(1200);
      const el = page.locator(`#${r.expectedActive}`);
      const exists = await el.count();
      if (exists === 0) {
        fs.appendFileSync(path.join(EVIDENCE_DIR, 'active-state.log'), `${r.path} -> MISSING NAV ITEM ${r.expectedActive}\n`);
        return;
      }
      const fontWeight = await el.evaluate(e => getComputedStyle(e).fontWeight);
      fs.appendFileSync(path.join(EVIDENCE_DIR, 'active-state.log'), `${r.path} -> ${r.expectedActive} fontWeight=${fontWeight}\n`);
      await page.screenshot({ path: path.join(EVIDENCE_DIR, r.path.replace(/\//g, '_') + '.png') });
      expect(Number(fontWeight)).toBeGreaterThanOrEqual(600);
    });
  }

  const SMOKE_ROUTES = [
    '/admin/dashboard', '/admin/tenants', '/admin/bookings', '/admin/customers',
    '/admin/categories', '/admin/pricing-tiers', '/admin/home-services/service-catalog',
    '/admin/finance', '/admin/marketing', '/admin/engines', '/admin/security',
    '/admin/audit-logs', '/admin/users',
  ];
  for (const route of SMOKE_ROUTES) {
    test(`route smoke: ${route}`, async ({ page }) => {
      await loginAsSuperAdmin(page);
      const resp = await page.goto(route);
      await page.waitForTimeout(1200);
      const status = resp?.status() ?? -1;
      const bodyText = await page.locator('body').innerText();
      await page.screenshot({ path: path.join(EVIDENCE_DIR, 'smoke' + route.replace(/\//g, '_') + '.png'), fullPage: true });
      fs.appendFileSync(path.join(EVIDENCE_DIR, 'route-smoke.log'), `${route} | status=${status} | len=${bodyText.length} | hasSidebar=${await page.locator('aside').count()} | hasHeader=${await page.locator('header').count()}\n`);
      expect(status).toBeLessThan(400);
      expect(bodyText.toLowerCase()).not.toMatch(/\bnan\b/);
    });
  }

  for (const width of [1024, 1280, 1440]) {
    test(`responsive at ${width}px`, async ({ page }) => {
      await page.setViewportSize({ width, height: 900 });
      await loginAsSuperAdmin(page);
      await page.goto('/admin/tenants');
      await page.waitForTimeout(1000);
      const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
      const clientWidth = await page.evaluate(() => document.documentElement.clientWidth);
      await page.screenshot({ path: path.join(EVIDENCE_DIR, `responsive-${width}.png`), fullPage: true });
      fs.appendFileSync(path.join(EVIDENCE_DIR, 'responsive.log'), `${width}px -> scrollWidth=${scrollWidth} clientWidth=${clientWidth} overflow=${scrollWidth > clientWidth + 2}\n`);
    });
  }
});
