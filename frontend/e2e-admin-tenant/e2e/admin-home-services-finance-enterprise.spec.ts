import { expect, test } from '@playwright/test';
import { loginAsSuperAdmin } from './helpers/admin-auth';

const TABS = [
  'Overview', 'Monetization', 'Provider Charges', 'Credits & Top-ups',
  'Security Deposits', 'Invoices', 'Customer Refunds', 'Warranty Claims',
  'Financial Events',
];

test.describe('Home Services finance enterprise workspace', () => {
  test('all finance surfaces load without failed requests or stale wallet UI', async ({ page }) => {
    const failures: string[] = [];
    page.on('response', response => {
      if (response.url().includes('/v1/') && response.status() >= 400) {
        failures.push(`${response.status()} ${response.url()}`);
      }
    });

    await loginAsSuperAdmin(page);
    await page.goto('/admin/home-services/finance', { waitUntil: 'domcontentloaded' });
    await expect(page.getByRole('heading', { name: 'Home Services Finance' })).toBeVisible();

    for (const label of TABS) {
      const tab = page.getByRole('tab', { name: label, exact: true });
      await expect(tab).toBeVisible();
      await tab.click();
      await expect(tab).toHaveAttribute('aria-selected', 'true');
      await page.waitForTimeout(500);
      await expect(page.getByText(/Failed to load/i)).toHaveCount(0);
    }

    const text = await page.locator('body').innerText();
    expect(text).not.toContain('Provider Wallets');
    expect(text).not.toContain('undefined');
    expect(text.toLowerCase()).not.toMatch(/\bnan\b/);
    expect(failures).toEqual([]);
  });

  test('legacy finance duplicates resolve to the consolidated workspace', async ({ page }) => {
    await loginAsSuperAdmin(page);
    await page.goto('/admin/provider-wallets');
    await expect(page).toHaveURL(/\/admin\/home-services\/finance\?tab=credits&credits_tab=accounts/);
    await page.goto('/admin/home-services/completed-job-deduction');
    await expect(page).toHaveURL(/\/admin\/home-services\/finance\?tab=provider-charges/);
  });
});
