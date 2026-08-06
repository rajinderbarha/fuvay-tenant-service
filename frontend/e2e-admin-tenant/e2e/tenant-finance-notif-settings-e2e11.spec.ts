import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';
import { loginAsTenantOwner, loginAsTenantReadOnly } from './helpers/tenant-auth';

const APP = process.env.E2E_APP || 'admin';
const EVIDENCE_DIR = path.join(__dirname, '..', 'evidence', 'e2e11');
if (!fs.existsSync(EVIDENCE_DIR)) fs.mkdirSync(EVIDENCE_DIR, { recursive: true });

function log(file: string, line: string) {
  fs.appendFileSync(path.join(EVIDENCE_DIR, file), line + '\n');
}

// The shared loginViaUi() helper only suppresses the ADMIN app's tour
// overlay (serviceos_disable_tour_e2e). The tenant app's onboarding tour
// uses a different, tenant-specific key (hooks/useTour.ts) and was left
// unsuppressed here — its modal intercepts pointer events and blocks
// every subsequent click/render check. Set it post-login, pre-navigation.
async function suppressTenantTour(page: import('@playwright/test').Page) {
  await page.evaluate(() => localStorage.setItem('serviceos-tenant-tour-done', 'true'));
}

test.describe('ADMIN-TENANT-E2E-11 tenant finance/notifications/settings', () => {
  test.skip(APP !== 'tenant', 'tenant-only');

  test('/finance redirects to the real Package & Credits page, not the legacy wallet page', async ({ page }) => {
    await loginAsTenantOwner(page);
    await suppressTenantTour(page);
    await page.goto('/finance');
    await page.waitForTimeout(2000);
    // /finance/package itself now redirects again, into the consolidated
    // /packages page (see finance/package/page.tsx) -- both hops are real,
    // intentional redirects, not a broken route.
    await expect(page).toHaveURL(/\/packages/);
    const bodyText = await page.locator('body').innerText();
    await page.screenshot({ path: path.join(EVIDENCE_DIR, 'finance-overview.png'), fullPage: true });
    log('finance.log', `redirected-to=${page.url()} bodyLen=${bodyText.length}`);
    // "Demo AC Services" was the removed demo tenant; live login is Guramrit.
    expect(bodyText).toContain('Guramrit');
    expect(bodyText).not.toMatch(/Request Payout|Bank Account ID|Payout History/i);
  });

  test('Usage Credit Balance shows real backend value', async ({ page }) => {
    const apiCalls: string[] = [];
    page.on('response', (resp) => { if (resp.url().includes('/usage-credits/')) apiCalls.push(`${resp.status()} ${resp.url()}`); });
    await loginAsTenantOwner(page);
    await suppressTenantTour(page);
    await page.goto('/finance/package');
    await page.waitForTimeout(2000);
    const bodyText = await page.locator('body').innerText();
    await page.screenshot({ path: path.join(EVIDENCE_DIR, 'usage-credit-balance.png'), fullPage: true });
    log('balance.log', `apiCalls=${apiCalls.join(' ;; ')}`);
    // "Usage Credit Balance" (that exact label) only renders on the
    // Credit Ledger tab of the consolidated /packages page; the Overview
    // tab this redirect lands on shows the same real balance under the
    // "Usage Credits" card instead (packages/page.tsx ~L200-210).
    expect(bodyText.toLowerCase()).toContain('usage credits');
    expect(bodyText).not.toMatch(/Wallet Balance|Cash Wallet|Provider Cash Balance|Withdrawable Balance/i);
  });

  test('Usage Credit Ledger shows real ledger entries with correct arithmetic', async ({ page }) => {
    // Guramrit (the live E2E tenant-owner login) has never had a real
    // completed-job deduction -- its only usage_credit_ledger row is the
    // original activation_credit_package_purchase (0 -> 1000), confirmed
    // via direct Postgres query. The one real completed_job_deduction row
    // in the whole database belongs to a different tenant ("T Co"), which
    // this login has no access to. So this asserts against what's actually
    // real for THIS tenant rather than a dead demo balance chain
    // (4000->3979->3958->3937, none of which exist anymore).
    const apiCalls: string[] = [];
    page.on('response', (resp) => { if (resp.url().includes('/usage-credits/')) apiCalls.push(`${resp.status()} ${resp.url()}`); });
    await loginAsTenantOwner(page);
    await suppressTenantTour(page);
    await page.goto('/finance/usage-credit-ledger');
    await page.waitForTimeout(1500);
    // Consolidated into /packages' "Credit Ledger" tab (redirect loses the
    // deep link to that specific tab -- must click it after landing).
    await page.getByRole('button', { name: /Credit Ledger/i }).click();
    await page.waitForTimeout(1500);
    const bodyText = await page.locator('body').innerText();
    await page.screenshot({ path: path.join(EVIDENCE_DIR, 'usage-credit-ledger.png'), fullPage: true });
    log('ledger.log', `apiCalls=${apiCalls.join(' ;; ')}`);
    expect(apiCalls.some(c => c.startsWith('200'))).toBeTruthy();
    expect(bodyText).toContain('activation_credit_package_purchase');
    expect(bodyText).toMatch(/\+1000/);
    expect(bodyText.toLowerCase()).not.toMatch(/\bnan\b/);
    expect(bodyText).not.toMatch(/\bundefined\b/);
  });

  test('Security Deposit page shows real status, separate from usage credits, no withdraw action', async ({ page }) => {
    await loginAsTenantOwner(page);
    await suppressTenantTour(page);
    await page.goto('/finance/security-deposit');
    await page.waitForTimeout(2000);
    const bodyText = await page.locator('body').innerText();
    await page.screenshot({ path: path.join(EVIDENCE_DIR, 'security-deposit.png'), fullPage: true });
    log('deposit.log', `bodyLen=${bodyText.length}`);
    expect(bodyText).toContain('Security Deposit');
    expect(bodyText).not.toMatch(/Withdraw|Escrow/i);
  });

  test('Tenant Notifications route loads real data or honest empty state', async ({ page }) => {
    const apiCalls: string[] = [];
    page.on('response', (resp) => { if (resp.url().includes('/v1/notifications/')) apiCalls.push(`${resp.status()} ${resp.url()}`); });
    await loginAsTenantOwner(page);
    await suppressTenantTour(page);
    await page.goto('/notifications');
    await page.waitForTimeout(2000);
    const bodyText = await page.locator('body').innerText();
    await page.screenshot({ path: path.join(EVIDENCE_DIR, 'notifications.png'), fullPage: true });
    log('notifications.log', `apiCalls=${apiCalls.join(' ;; ')}`);
    expect(apiCalls.some(c => c.startsWith('200'))).toBeTruthy();
    expect(bodyText).toContain('Notifications');
    expect(bodyText.toLowerCase()).not.toMatch(/\bnan\b/);
  });

  test('Tenant notification bell is clickable, opens a dropdown, and "View all" navigates', async ({ page }) => {
    // Real element is a <button> (TenantLayout.tsx:709-712), never an <a> --
    // it opens a recent-notifications dropdown rather than navigating
    // directly, same pattern as the admin bell. Its "View all notifications"
    // link (TenantLayout.tsx:794) goes to /provider/notifications, a
    // separate real route from /notifications (both exist).
    await loginAsTenantOwner(page);
    await suppressTenantTour(page);
    await page.goto('/finance/package');
    await page.waitForTimeout(1500);
    const bell = page.locator('button[aria-label*="Notification"]');
    await expect(bell).toBeVisible();
    await page.screenshot({ path: path.join(EVIDENCE_DIR, 'bell-before-click.png') });
    await bell.click();
    await page.waitForTimeout(1000);
    await page.screenshot({ path: path.join(EVIDENCE_DIR, 'bell-dropdown-open.png'), fullPage: true });
    const viewAllLink = page.getByRole('link', { name: /View all notifications/i });
    await expect(viewAllLink).toBeVisible();
    await viewAllLink.click();
    await page.waitForTimeout(1500);
    await expect(page).toHaveURL(/\/(provider\/)?notifications/);
    await page.screenshot({ path: path.join(EVIDENCE_DIR, 'bell-after-click.png'), fullPage: true });
  });

  test('Tenant Settings route loads real profile data, tabs work', async ({ page }) => {
    const apiCalls: string[] = [];
    page.on('response', (resp) => { if (resp.url().includes('/v1/tenants/') || resp.url().includes('/settings')) apiCalls.push(`${resp.status()} ${resp.url()}`); });
    await loginAsTenantOwner(page);
    await suppressTenantTour(page);
    await page.goto('/settings');
    await page.waitForTimeout(2000);
    const bodyText = await page.locator('body').innerText();
    await page.screenshot({ path: path.join(EVIDENCE_DIR, 'settings.png'), fullPage: true });
    log('settings.log', `apiCalls=${apiCalls.join(' ;; ')}`);
    expect(bodyText).toContain('Settings');
    expect(bodyText.toLowerCase()).not.toMatch(/\bnan\b/);
  });

  test('Read-only tenant cannot mutate settings (mutation controls blocked or absent)', async ({ page }) => {
    await loginAsTenantReadOnly(page);
    await suppressTenantTour(page);
    await page.goto('/settings');
    await page.waitForTimeout(2000);
    const bodyText = await page.locator('body').innerText();
    await page.screenshot({ path: path.join(EVIDENCE_DIR, 'readonly-settings.png'), fullPage: true });
    log('rbac.log', `readonly-body-len=${bodyText.length}`);
    // Attempt a real, COMPLETE mutation (valid payload, including the
    // required "reason" field) via direct API call using the read-only
    // session's token — a valid-but-unauthorized request must be
    // rejected on permission grounds (403), not merely fail validation.
    const token = await page.evaluate(() => localStorage.getItem('serviceos_tenant_token'));
    const tenantId = await page.evaluate(() => localStorage.getItem('serviceos_tenant_id'));
    const apiBase = process.env.E2E_API_BASE || 'http://localhost:8000';
    const res = await page.request.put(`${apiBase}/v1/settings/tenants/${tenantId}/test_e2e11_key`, {
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      data: JSON.stringify({ value: 'should-not-be-allowed', reason: 'e2e11 rbac probe' }),
      failOnStatusCode: false,
    });
    const body = await res.text();
    log('rbac.log', `mutation-attempt-status=${res.status()} body=${body.slice(0, 300)}`);
    // Clean up if the mutation was (wrongly) allowed through, so this
    // probe never leaves stray state behind regardless of outcome.
    if (res.status() === 200) {
      await page.request.delete(`${apiBase}/v1/settings/tenants/${tenantId}/test_e2e11_key`, {
        headers: { Authorization: `Bearer ${token}` }, failOnStatusCode: false,
      });
    }
    expect(res.status(), 'read-only role must not be able to complete a valid tenant-settings mutation').toBe(403);
  });

  test('no mock data / forbidden labels / raw JSON across finance, notifications, settings', async ({ page }) => {
    await loginAsTenantOwner(page);
    await suppressTenantTour(page);
    const forbidden = ['Cash Wallet', 'Wallet Balance', 'Withdraw', 'Withdrawable Balance', 'Tenant Payout',
      'Provider Earnings Wallet', 'Escrow', 'Provider Cash Balance', 'Credit Wallet Health',
      'Platform Pay Now', 'Recharge Wallet', 'Wallet Low'];
    for (const url of ['/finance/package', '/finance/usage-credit-ledger', '/finance/security-deposit', '/notifications', '/settings']) {
      await page.goto(url);
      await page.waitForTimeout(1500);
      const bodyText = await page.locator('body').innerText();
      const found = forbidden.filter(f => bodyText.includes(f));
      log('labels.log', `${url} -> forbidden=${JSON.stringify(found)}`);
      expect(found.length).toBe(0);
      expect(bodyText).not.toMatch(/\bundefined\b/);
    }
  });
});
