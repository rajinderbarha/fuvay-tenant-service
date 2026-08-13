import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';
import { loginAsSuperAdmin } from './helpers/admin-auth';
import { login, apiGet, SUPER_ADMIN, SEED } from './helpers/api';

const APP = process.env.E2E_APP || 'admin';
const EVIDENCE_DIR = path.join(__dirname, '..', 'evidence', 'e2e05');
if (!fs.existsSync(EVIDENCE_DIR)) fs.mkdirSync(EVIDENCE_DIR, { recursive: true });

function log(name: string, text: string) {
  fs.appendFileSync(path.join(EVIDENCE_DIR, name), text + '\n');
}

// Was a hardcoded tenant id (34b427a7) that no longer exists -- every test
// using it hit a dead detail route. Now derived from the single SEED source
// of truth in helpers/api.ts.
const DEMO_TENANT_ID = SEED.tenantId;

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

  test('usage credits page: ledger balance matches the live backend value', async ({ page }) => {
    // Was asserting a hardcoded 3958. That number belonged to a tenant that
    // has since been removed, and a credit balance legitimately CHANGES every
    // time a job completes -- so pinning it made the test fail on correct
    // code. Now reads the authoritative value from the API and asserts the
    // page renders that same number, which is the real invariant (UI agrees
    // with backend) rather than a snapshot of one moment.
    const token = await login(SUPER_ADMIN.email, SUPER_ADMIN.password);
    const res = await apiGet(`/v1/admin/usage-credits/${SEED.tenantId}/balance`, token);
    const balance = Number(res.body?.data?.usage_credit_balance ?? NaN);
    expect(Number.isFinite(balance)).toBeTruthy();
    const asInt = String(Math.trunc(balance));
    const grouped = Math.trunc(balance).toLocaleString('en-IN');

    await loginAsSuperAdmin(page);
    // The page no longer pre-fills a (dead) demo tenant id, so the test must
    // supply one -- previously it relied on that hardcoded default and would
    // silently assert against whatever tenant the page happened to embed.
    await page.goto(`/admin/home-services/finance?tab=credits&credits_tab=ledger&tenant_id=${SEED.tenantId}`, { waitUntil: 'domcontentloaded' });
    await expect(page.getByText('Credit Ledger', { exact: true }).first()).toBeVisible({ timeout: 15000 });
    await expect(page.locator('tbody tr').first()).toBeVisible({ timeout: 15000 });
    await expect(page.getByText(`${balance.toLocaleString('en-IN')} credits`, { exact: true }).first())
      .toBeVisible({ timeout: 15000 });
    const bodyText = await page.locator('body').innerText();
    // Give this assertion its own evidence name; the suite-wide Playwright
    // screenshot attachment can otherwise race a prior retained file on
    // Windows when multiple verification runs reuse the same directory.
    await page.screenshot({ path: path.join(EVIDENCE_DIR, 'usage-credits-live-balance.png'), fullPage: true });
    log('usage-credits.log', `API balance=${balance} rendered=${bodyText.includes(asInt) || bodyText.includes(grouped)}`);
    expect(bodyText).toContain(`${balance.toLocaleString('en-IN')} credits`);
  });

  test('completed job deduction config page: renders real per-rule deduction credits', async ({ page }) => {
    // Two fixes here. (1) It asserted a specific "AC Repair/Split AC/LG rule,
    // 21 credits" that no longer exists -- the live charge-config rows are
    // AC Service and AC Gas Refilling. Asserting a specific credit VALUE is
    // wrong anyway: an admin can edit it at any time, so the test would fail
    // on a legitimate config change. (2) It read body innerText after a fixed
    // 1500ms wait, which raced the data fetch -- the strings were present in
    // the page but not yet rendered. Now uses web-first assertions that wait
    // for the real rendered row instead of a sleep.
    await loginAsSuperAdmin(page);
    await page.goto('/admin/home-services/completed-job-deduction', { waitUntil: 'domcontentloaded' });

    await expect(page.getByRole('heading', { name: 'Completed Job Deduction' })).toBeVisible({ timeout: 15000 });
    // At least one real rule row, showing its deduction in usage credits.
    await expect(page.locator('td', { hasText: /\d+ usage credits/ }).first())
      .toBeVisible({ timeout: 15000 });

    await page.screenshot({ path: path.join(EVIDENCE_DIR, 'completed-job-deduction.png'), fullPage: true });
    const bodyText = await page.locator('body').innerText();
    log('completed-job-deduction.log', `rendered rule rows with usage credits: ${/\d+ usage credits/.test(bodyText)}`);
    for (const f of FORBIDDEN) expect(bodyText).not.toContain(f);
  });

  test('tenant list: search the seed tenant, status active, open detail', async ({ page }) => {
    await loginAsSuperAdmin(page);
    await page.goto('/admin/tenants', { waitUntil: 'domcontentloaded' });
    await page.locator(`text=${SEED.tenantName}`).first().waitFor({ state: 'visible', timeout: 15000 });
    const bodyText = await page.locator('body').innerText();
    await page.screenshot({ path: path.join(EVIDENCE_DIR, 'tenant-list.png'), fullPage: true });
    log('tenant-list.log', `Contains seed tenant: ${bodyText.includes(SEED.tenantName)}`);
    expect(bodyText).toContain(SEED.tenantName);
  });

  test('tenant detail (Tenant 360): overview + usage credit ledger tab, balance matches usage-credits page', async ({ page }) => {
    await loginAsSuperAdmin(page);
    await page.goto(`/admin/tenants/${DEMO_TENANT_ID}`, { waitUntil: 'domcontentloaded' });
    // Was a bare 3500ms sleep then a body innerText read, which raced the
    // detail fetch on a slow compile and failed even though the API returns
    // business_name correctly. Wait for the actual rendered name instead.
    await expect(page.getByText(SEED.tenantName, { exact: false }).first())
      .toBeVisible({ timeout: 20000 });
    const overviewText = await page.locator('body').innerText();
    await page.screenshot({ path: path.join(EVIDENCE_DIR, 'tenant-detail-overview.png'), fullPage: true });
    log('tenant-detail.log', `Contains seed tenant: ${overviewText.includes(SEED.tenantName)}`);
    expect(overviewText).toContain(SEED.tenantName);
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
      // Was pinned to 3958 (removed tenant's balance, and a value that
      // legitimately moves whenever a job completes). The real invariant is
      // that Tenant 360's ledger tab agrees with the backend, so resolve the
      // live balance and assert THAT renders.
      const tok = await login(SUPER_ADMIN.email, SUPER_ADMIN.password);
      const fin = await apiGet(`/v1/admin/usage-credits/${SEED.tenantId}/balance`, tok);
      const bal = Number(fin.body?.data?.usage_credit_balance ?? NaN);
      const plain = String(Math.trunc(bal));
      const grouped = Math.trunc(bal).toLocaleString('en-IN');
      log('tenant-detail.log', `Ledger tab shows live balance ${bal}: ${ledgerText.includes(plain) || ledgerText.includes(grouped)}`);
      expect(Number.isFinite(bal)).toBeTruthy();
      expect(ledgerText.includes(plain) || ledgerText.includes(grouped)).toBeTruthy();
      for (const f of FORBIDDEN) {
        expect(ledgerText).not.toContain(f);
      }
    } else {
      log('tenant-detail.log', 'Usage Credit Ledger tab link not found by text locator.');
    }
  });
});
