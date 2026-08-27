import { test, expect } from '@playwright/test';
import { loginAsSuperAdmin } from './helpers/admin-auth';
import { loginAsTenantOwner } from './helpers/tenant-auth';

const outputRoot = 'G:/serviceos/artifacts/design-audit';
const app = process.env.E2E_APP || 'admin';

test('capture current dashboard and representative directory', async ({ page }) => {
  test.setTimeout(180_000);
  await page.setViewportSize({ width: 1440, height: 1000 });

  if (app === 'tenant') {
    await loginAsTenantOwner(page);
    await page.goto('/dashboard', { waitUntil: 'domcontentloaded' });
    await expect(page.locator('body')).not.toContainText('Internal Server Error');
    await expect(page.getByRole('heading', { name: /Barha auto store operations/i })).toBeVisible({ timeout: 90_000 });
    await page.waitForTimeout(1500);
    await page.screenshot({ path: `${outputRoot}/01-tenant-dashboard.png`, fullPage: true });

    const jobsResponsePromise = page.waitForResponse(
      response => response.request().method() === 'GET' && response.url().includes('/v1/tenant/home-services/bookings-jobs'),
      { timeout: 90_000 },
    );
    await page.goto('/home-services/bookings-jobs', { waitUntil: 'domcontentloaded' });
    await expect(page.locator('body')).not.toContainText('Internal Server Error');
    const jobsResponse = await jobsResponsePromise;
    expect(jobsResponse.status(), await jobsResponse.text()).toBe(200);
    await expect(page.locator('.bj-table')).toBeVisible({ timeout: 15_000 });
    await page.waitForTimeout(1000);
    await page.screenshot({ path: `${outputRoot}/02-tenant-bookings-jobs.png`, fullPage: true });
    return;
  }

  await loginAsSuperAdmin(page);
  await page.goto('/admin/dashboard', { waitUntil: 'domcontentloaded' });
  await expect(page.locator('body')).not.toContainText('Internal Server Error');
  await page.locator('.skeleton').first().waitFor({ state: 'detached', timeout: 45_000 }).catch(() => undefined);
  await page.waitForTimeout(1000);
  await page.screenshot({ path: `${outputRoot}/03-admin-dashboard.png`, fullPage: true });

  await page.goto('/admin/tenants', { waitUntil: 'domcontentloaded' });
  await expect(page.locator('body')).not.toContainText('Internal Server Error');
  await page.locator('.skeleton').first().waitFor({ state: 'detached', timeout: 45_000 }).catch(() => undefined);
  await page.waitForTimeout(1000);
  await page.screenshot({ path: `${outputRoot}/04-admin-tenants.png`, fullPage: true });
});
