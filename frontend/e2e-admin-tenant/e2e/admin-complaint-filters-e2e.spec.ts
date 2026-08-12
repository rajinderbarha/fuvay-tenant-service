import { expect, test } from '@playwright/test';
import { loginAsSuperAdmin } from './helpers/admin-auth';

test.describe('Admin complaint summary filters', () => {
  test('summary cards issue the matching server-side filters', async ({ page }) => {
    await loginAsSuperAdmin(page);
    await page.goto('/admin/complaints');

    await expect(page.getByRole('heading', { name: /complaints/i })).toBeVisible();
    const aiSettlement = page.getByRole('button', { name: /AI Settlement: \d+/ });
    const newToday = page.getByRole('button', { name: /New Today: \d+/ });
    await expect(aiSettlement).toBeVisible();
    await expect(newToday).toBeVisible();

    const [aiResponse] = await Promise.all([
      page.waitForResponse(response => {
        if (!response.url().includes('/v1/admin/complaints/list?')) return false;
        return new URL(response.url()).searchParams.get('status') === 'ai_settlement_started';
      }),
      aiSettlement.click(),
    ]);
    expect(aiResponse.ok()).toBeTruthy();
    await expect(aiSettlement).toHaveAttribute('aria-pressed', 'true');

    const [todayResponse] = await Promise.all([
      page.waitForResponse(response => {
        if (!response.url().includes('/v1/admin/complaints/list?')) return false;
        const params = new URL(response.url()).searchParams;
        return Boolean(params.get('date_from')) && !params.has('status');
      }),
      newToday.click(),
    ]);
    expect(todayResponse.ok()).toBeTruthy();
    const dateFrom = new URL(todayResponse.url()).searchParams.get('date_from');
    expect(dateFrom).toBeTruthy();
    expect(Number.isNaN(Date.parse(dateFrom!))).toBeFalsy();
    await expect(newToday).toHaveAttribute('aria-pressed', 'true');

    await expect(page.locator('body')).not.toContainText(/\b(?:undefined|invalid date|nan)\b/i);
  });
});
