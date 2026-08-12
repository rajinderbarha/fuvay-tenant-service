import { test, expect } from '@playwright/test';
import { loginAsSuperAdmin } from './helpers/admin-auth';
import { apiGet, login, SUPER_ADMIN } from './helpers/api';

const APP = process.env.E2E_APP || 'admin';

test.describe('admin customer payment reliability handoff', () => {
  test.skip(APP !== 'admin', 'admin-only');

  test('summary, list and detail expose canonical reconciliation state', async () => {
    const token = await login(SUPER_ADMIN.email, SUPER_ADMIN.password);
    const summary = await apiGet('/v1/admin/home-services/customers/summary', token);
    expect(summary.status).toBe(200);
    expect(summary.body.data.payment_review_available).toBe(true);
    expect(Number(summary.body.data.payment_review)).toBeGreaterThanOrEqual(0);

    const list = await apiGet('/v1/admin/home-services/customers?page=1&page_size=20', token);
    expect(list.status).toBe(200);
    const first = list.body.data.items[0];
    if (!first) return;
    expect(['insufficient_data', 'reliable', 'needs_review']).toContain(first.payment_reliability);

    const detail = await apiGet(`/v1/admin/home-services/customers/${first.customer_id}`, token);
    expect(detail.status).toBe(200);
    expect(['insufficient_data', 'reliable', 'needs_review']).toContain(detail.body.data.payment_reliability);
    expect(Number(detail.body.data.payment_decisions)).toBeGreaterThanOrEqual(0);
    expect(Number(detail.body.data.payment_records_needing_review)).toBeGreaterThanOrEqual(0);
  });

  test('customer directory and 360 render reliability without placeholders', async ({ page }) => {
    await loginAsSuperAdmin(page);
    await page.goto('/admin/home-services/customers');
    await expect(page.getByRole('heading', { name: 'Home Services Customers' })).toBeVisible();
    await expect(page.getByText('Payment Review', { exact: true })).toBeVisible({ timeout: 15_000 });
    await expect(page.locator('table .skeleton')).toHaveCount(0, { timeout: 15_000 });

    const firstDetail = page.getByRole('button', { name: 'View 360°' }).first();
    if (await firstDetail.count()) {
      await firstDetail.click();
      await expect(page.getByText('Payment Reliability', { exact: true })).toBeVisible({ timeout: 15_000 });
      await expect(page.getByText('Not Implemented', { exact: true })).toHaveCount(0);
      await expect(page.getByText(/customer decisions$/)).toBeVisible();
    }
  });
});
