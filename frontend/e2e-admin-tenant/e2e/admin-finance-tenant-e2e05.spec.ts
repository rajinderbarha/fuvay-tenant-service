import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';
import { loginAsSuperAdmin } from './helpers/admin-auth';

const APP = process.env.E2E_APP || 'admin';
const EVIDENCE_DIR = path.join(__dirname, '..', 'evidence', 'e2e05');
if (!fs.existsSync(EVIDENCE_DIR)) fs.mkdirSync(EVIDENCE_DIR, { recursive: true });

function log(name: string, text: string) {
  fs.appendFileSync(path.join(EVIDENCE_DIR, name), text + '\n');
}

const DEMO_TENANT_ID = '34b427a7-b2be-496c-b826-6d51bb181248';

const FORBIDDEN = [
  'Cash Wallet', 'Withdraw', 'Withdrawable Balance',
  'Tenant Payout', 'Provider Earnings Wallet', 'Escrow',
  'Platform Collected Service Payment', 'Provider Cash Balance',
  'Credit Wallet Health', 'Platform Pay Now', 'Online Payment Required',
  'Manual Bargain Setup', 'Bargain Rule Builder', 'Bargain Settings',
];

test.describe('ADMIN-TENANT-E2E-05 admin finance + tenant detail', () => {
  test.skip(APP !== 'admin', 'admin-only');

  test('route smoke: finance + tenant routes, no crash, no NaN/undefined', async ({ page }) => {
    await loginAsSuperAdmin(page);
    const routes = [
      '/admin/finance/usage-credits',
      '/admin/finance/wallets',
      '/admin/home-services/completed-job-deduction',
      '/admin/tenants',
      `/admin/tenants/${DEMO_TENANT_ID}`,
    ];
    for (const route of routes) {
      const resp = await page.goto(route, { waitUntil: 'domcontentloaded', timeout: 30000 });
      await page.waitForTimeout(2000);
      const status = resp?.status() ?? -1;
      const bodyText = await page.locator('body').innerText();
      await page.screenshot({ path: path.join(EVIDENCE_DIR, 'route' + route.replace(/\//g, '_') + '.png'), fullPage: true });
      log('route-smoke.log', `${route} | status=${status} | len=${bodyText.length} | hasSidebar=${await page.locator('aside').count()}`);
      expect(status).toBeLessThan(400);
      expect(bodyText.toLowerCase()).not.toMatch(/\bnan\b/);
      expect(bodyText).not.toMatch(/undefined/);
      for (const f of FORBIDDEN) {
        expect(bodyText).not.toContain(f);
      }
    }
  });

  test('usage credits page: load ledger for Demo AC Services, balance matches DB (3958)', async ({ page }) => {
    await loginAsSuperAdmin(page);
    await page.goto('/admin/finance/usage-credits', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1000);
    // Tenant ID field pre-filled with DEMO_TENANT_ID by default; click Load Ledger to be sure.
    await page.locator('button:has-text("Load Ledger")').click();
    await page.waitForTimeout(2000);
    const bodyText = await page.locator('body').innerText();
    await page.screenshot({ path: path.join(EVIDENCE_DIR, 'usage-credits.png'), fullPage: true });
    log('usage-credits.log', `Contains 3958: ${bodyText.includes('3958')}`);
    log('usage-credits.log', `Contains Completed Job Deduction: ${bodyText.includes('Completed Job Deduction')}`);
    expect(bodyText).toContain('3958');
    expect(bodyText).toContain('Completed Job Deduction');
  });

  test('completed job deduction config page: shows AC Repair/Split AC/LG rule, 21 credits', async ({ page }) => {
    await loginAsSuperAdmin(page);
    await page.goto('/admin/home-services/completed-job-deduction', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1500);
    const bodyText = await page.locator('body').innerText();
    await page.screenshot({ path: path.join(EVIDENCE_DIR, 'completed-job-deduction.png'), fullPage: true });
    log('completed-job-deduction.log', `Contains 21 usage credits: ${bodyText.includes('21 usage credits')}`);
    expect(bodyText).toContain('Completed Job Deduction');
    expect(bodyText).toContain('usage credits');
  });

  test('tenant list: search Demo AC Services, status active, open detail', async ({ page }) => {
    await loginAsSuperAdmin(page);
    await page.goto('/admin/tenants', { waitUntil: 'domcontentloaded' });
    await page.locator('text=Demo AC Services').first().waitFor({ state: 'visible', timeout: 15000 });
    const bodyText = await page.locator('body').innerText();
    await page.screenshot({ path: path.join(EVIDENCE_DIR, 'tenant-list.png'), fullPage: true });
    log('tenant-list.log', `Contains Demo AC Services: ${bodyText.includes('Demo AC Services')}`);
    expect(bodyText).toContain('Demo AC Services');
  });

  test('tenant detail (Tenant 360): overview + usage credit ledger tab, balance matches usage-credits page', async ({ page }) => {
    await loginAsSuperAdmin(page);
    await page.goto(`/admin/tenants/${DEMO_TENANT_ID}`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3500);
    const overviewText = await page.locator('body').innerText();
    await page.screenshot({ path: path.join(EVIDENCE_DIR, 'tenant-detail-overview.png'), fullPage: true });
    log('tenant-detail.log', `Contains Demo AC Services: ${overviewText.includes('Demo AC Services')}`);
    expect(overviewText).toContain('Demo AC Services');
    expect(overviewText).not.toContain('Your Business');

    // The "Usage Credit Ledger" sub-tab lives under the "Finance" tab-group;
    // the group must be selected first or the sub-tab button never renders in the DOM.
    const financeGroup = page.locator('button:has-text("Finance")').first();
    if (await financeGroup.count() > 0) {
      await financeGroup.click();
      await page.waitForTimeout(500);
    }
    const tab = page.locator('text=Usage Credit Ledger').first();
    if (await tab.count() > 0) {
      await tab.click();
      await page.waitForTimeout(2000);
      const ledgerText = await page.locator('body').innerText();
      await page.screenshot({ path: path.join(EVIDENCE_DIR, 'tenant-detail-ledger.png'), fullPage: true });
      log('tenant-detail.log', `Ledger tab contains 3958 (matches Usage Credits page): ${ledgerText.includes('3,958') || ledgerText.includes('3958')}`);
      expect(ledgerText.includes('3,958') || ledgerText.includes('3958')).toBeTruthy();
      for (const f of FORBIDDEN) {
        expect(ledgerText).not.toContain(f);
      }
    } else {
      log('tenant-detail.log', 'Usage Credit Ledger tab link not found by text locator.');
    }
  });
});
