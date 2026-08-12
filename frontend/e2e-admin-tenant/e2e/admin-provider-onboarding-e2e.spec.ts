import { test, expect } from '@playwright/test';
import { loginAsSuperAdmin } from './helpers/admin-auth';
import { apiGet, login, SUPER_ADMIN } from './helpers/api';

const APP = process.env.E2E_APP || 'admin';

test.describe('admin provider onboarding handoff', () => {
  test.skip(APP !== 'admin', 'admin-only');

  test('queue API is Home Services scoped and paginated', async () => {
    const token = await login(SUPER_ADMIN.email, SUPER_ADMIN.password);
    const res = await apiGet(
      '/v1/admin/onboarding/providers?vertical_type=home_services&page=1&page_size=20',
      token,
    );
    expect(res.status).toBe(200);
    expect(Array.isArray(res.body.data.providers)).toBeTruthy();
    expect(res.body.data.page).toBe(1);
    expect(res.body.data.page_size).toBe(20);
    expect(res.body.data.total).toBeGreaterThanOrEqual(res.body.data.providers.length);
  });

  test('legacy onboarding URLs converge on the canonical queue', async ({ page }) => {
    await loginAsSuperAdmin(page);
    await page.goto('/admin/tenants/onboarding');
    await expect(page).toHaveURL(/\/admin\/home-services\/providers\?tab=onboarding/);
    await expect(page.getByRole('heading', { name: 'Home Services Providers' })).toBeVisible();
    await expect(page.getByText('Pending Review', { exact: true })).toBeVisible({ timeout: 15_000 });
    await expect(
      page.getByText('No Home Services onboarding records match this view.')
        .or(page.getByRole('button', { name: 'View 360°' }).first()),
    ).toBeVisible({ timeout: 15_000 });
    await expect(page.locator('table .skeleton')).toHaveCount(0);
    const body = await page.locator('body').innerText();
    expect(body).not.toMatch(/\bundefined\b|\bNaN\b/);
  });

  test('profile-change requests expose the document approval gate', async ({ page }) => {
    await loginAsSuperAdmin(page);
    await page.goto('/admin/home-services/providers?tab=changes');
    await expect(page.getByRole('button', { name: 'Profile Change Requests' })).toBeVisible();
    await expect(page.getByText(/Approved identity stays published until/i)).toBeVisible({ timeout: 15_000 });
  });

  test('provider export downloads and audit opens the real audit workspace', async ({ page }) => {
    await loginAsSuperAdmin(page);
    await page.goto('/admin/home-services/providers?tab=onboarding');
    await expect(page.getByRole('heading', { name: 'Home Services Providers' })).toBeVisible();

    const downloadPromise = page.waitForEvent('download');
    await page.getByRole('button', { name: 'Export' }).click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toBe('home-services-providers.csv');

    await page.getByRole('button', { name: 'View Audit' }).click();
    await expect(page).toHaveURL(/\/admin\/audit-logs\?resource_type=tenant_onboarding/);
    await expect(page.getByText(/^\d+ results?$/)).toBeVisible({ timeout: 15_000 });
  });
});
