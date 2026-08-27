import { test, expect, type Page } from '@playwright/test';
import { loginAsSuperAdmin } from './helpers/admin-auth';

const expectedRoutes = [
  '/admin/dashboard',
  '/admin/customers',
  '/admin/staff',
  '/admin/home-services/complaints',
  '/admin/verticals',
  '/admin/categories',
  '/admin/marketing',
  '/admin/marketing/home',
  '/admin/notifications',
  '/admin/analytics',
  '/admin/intelligence',
  '/admin/engines',
  '/admin/security',
  '/admin/compliance',
  '/admin/trust-quality',
  '/admin/audit-logs',
  '/admin/users',
  '/admin/roles',
  '/admin/permissions',
  '/admin/media',
  '/admin/settings',
  '/admin/home-services/dashboard',
  '/admin/catalog-workspace',
  '/admin/home-services/settings',
  '/admin/bookability/providers',
  '/admin/home-services/providers',
  '/admin/home-services/bookings-jobs',
  '/admin/home-services/finance',
] as const;

async function waitForPageToSettle(page: Page) {
  // Several command-centre pages intentionally keep polling. Waiting for
  // `networkidle` or every decorative skeleton made this smoke pass take
  // eight minutes without increasing defect coverage. Two seconds covers
  // the initial API fan-out while response listeners capture late failures.
  await page.waitForTimeout(2_000);
}

test('every current admin workspace destination renders without API or route failures', async ({ page }) => {
  test.setTimeout(15 * 60_000);
  await page.setViewportSize({ width: 1440, height: 1000 });
  await loginAsSuperAdmin(page);

  const apiFailures: string[] = [];
  page.on('response', response => {
    if (response.status() >= 400 && response.url().includes('/v1/')) {
      apiFailures.push(`${response.status()} ${response.request().method()} ${response.url()}`);
    }
  });

  for (const route of expectedRoutes) {
    const response = await page.goto(route, { waitUntil: 'domcontentloaded', timeout: 90_000 });
    if (response) expect(response.status(), route).toBeLessThan(400);
    expect(new URL(page.url()).pathname, route).toBe(route);
    await waitForPageToSettle(page);
    await expect(page.locator('body'), route).not.toContainText(/Internal Server Error|Application error|404: This page could not be found/i);
  }

  expect([...new Set(apiFailures)], apiFailures.join('\n')).toEqual([]);
});
