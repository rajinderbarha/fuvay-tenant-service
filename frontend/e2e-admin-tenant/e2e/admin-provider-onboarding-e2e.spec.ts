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

  test('provider export is queued and audit opens the real audit workspace', async ({ page }) => {
    await loginAsSuperAdmin(page);
    await page.goto('/admin/home-services/providers?tab=directory');
    await expect(page.getByRole('heading', { name: 'Home Services Providers' })).toBeVisible();

    await page.getByRole('button', { name: 'Queue export' }).click();
    await expect(page.getByText(/Export (pending|processing|completed)|Export could not be queued/)).toBeVisible({ timeout: 15_000 });

    await page.getByRole('link', { name: 'Audit trail' }).click();
    await expect(page).toHaveURL(/\/admin\/audit-logs\?resource_type=tenant_onboarding/);
    await expect(page.getByText(/^\d+ results?$/)).toBeVisible({ timeout: 15_000 });
  });

  test('provider 360 exposes scoped lifecycle controls and the real enrollment record', async ({ page }) => {
    await loginAsSuperAdmin(page);
    await page.goto('/admin/home-services/providers');
    await expect(page.getByRole('heading', { name: 'Home Services Providers' })).toBeVisible();

    const viewProvider = page.getByRole('button', { name: /View 360/ }).first();
    await expect(viewProvider).toBeVisible({ timeout: 15_000 });
    await viewProvider.click();

    await expect(page).toHaveURL(/\/admin\/home-services\/providers\/[0-9a-f-]+/);
    await expect(page.getByRole('button', { name: 'Lifecycle Record' })).toBeVisible({ timeout: 15_000 });
    await expect(page.getByRole('button', { name: 'Request Changes' })).toBeVisible();
    await expect(
      page.getByRole('button', { name: 'Suspend Home Services' })
        .or(page.getByRole('button', { name: 'Resume Home Services' })),
    ).toBeVisible();

    await page.getByRole('button', { name: 'Lifecycle Record' }).click();
    await expect(page.getByRole('heading', { name: 'Home Services lifecycle' })).toBeVisible();
    await expect(page.getByText('Enrollment decisions are audited independently')).toBeVisible();
  });
});
