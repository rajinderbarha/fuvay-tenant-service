import { test, expect, type Page } from '@playwright/test';
import { loginAsTenantOwner } from './helpers/tenant-auth';

const expectedRoutes = [
  '/dashboard',
  '/profile',
  '/business/coverage-hours',
  '/business/verification-documents',
  '/provider/compliance',
  '/home-services/bookings-jobs',
  '/home-services/dispatch',
  '/appointments',
  '/home-services/availability',
  '/home-services/services',
  '/inventory',
  '/home-services/team',
  '/customers',
  '/home-services/reviews',
  '/home-services/complaints',
  '/provider/refund-requests',
  '/marketing',
  '/home-services/finance',
  '/home-services/direct-payments',
  '/media',
  '/reports',
  '/activity',
  '/settings',
  '/help-support',
] as const;

async function waitForPageToSettle(page: Page) {
  await page.locator('.skeleton').first().waitFor({ state: 'detached', timeout: 12_000 }).catch(() => undefined);
  await page.waitForTimeout(600);
}

test('every visible tenant workspace destination renders without API or route failures', async ({ page }) => {
  test.setTimeout(12 * 60_000);
  await page.setViewportSize({ width: 1440, height: 1000 });
  await loginAsTenantOwner(page);

  const apiFailures: string[] = [];
  page.on('response', response => {
    if (response.status() >= 400 && response.url().includes('/v1/')) {
      apiFailures.push(`${response.status()} ${response.request().method()} ${response.url()}`);
    }
  });

  for (const route of expectedRoutes) {
    const response = await page.goto(route, { waitUntil: 'domcontentloaded', timeout: 90_000 });
    expect(response?.status(), route).toBeLessThan(400);
    await expect(page.locator('body'), route).not.toContainText(/Internal Server Error|Application error|404: This page could not be found/i);
    await waitForPageToSettle(page);
  }

  expect([...new Set(apiFailures)], apiFailures.join('\n')).toEqual([]);
});
