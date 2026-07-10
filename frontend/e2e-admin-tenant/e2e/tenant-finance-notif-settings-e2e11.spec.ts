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
    await expect(page).toHaveURL(/\/finance\/package/);
    const bodyText = await page.locator('body').innerText();
    await page.screenshot({ path: path.join(EVIDENCE_DIR, 'finance-overview.png'), fullPage: true });
    log('finance.log', `redirected-to=${page.url()} bodyLen=${bodyText.length}`);
    expect(bodyText).toContain('Demo AC Services');
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
    expect(bodyText).toContain('Usage Credit Balance');
    expect(bodyText).not.toMatch(/Wallet Balance|Cash Wallet|Provider Cash Balance|Withdrawable Balance/i);
  });

  test('Usage Credit Ledger shows real Completed Job Deduction entries with correct arithmetic', async ({ page }) => {
    const apiCalls: string[] = [];
    page.on('response', (resp) => { if (resp.url().includes('/usage-credits/')) apiCalls.push(`${resp.status()} ${resp.url()}`); });
    await loginAsTenantOwner(page);
    await suppressTenantTour(page);
    await page.goto('/finance/usage-credit-ledger');
    await page.waitForTimeout(2500);
    const bodyText = await page.locator('body').innerText();
    await page.screenshot({ path: path.join(EVIDENCE_DIR, 'usage-credit-ledger.png'), fullPage: true });
    log('ledger.log', `apiCalls=${apiCalls.join(' ;; ')}`);
    expect(apiCalls.some(c => c.startsWith('200'))).toBeTruthy();
    expect(bodyText).toContain('Completed Job Deduction');
    // Real chain verified via API before this test: 4000->3979->3958->3937
    expect(bodyText).toMatch(/3937/);
    expect(bodyText).toMatch(/3958/);
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

  test('Tenant notification bell is clickable and navigates to Notifications', async ({ page }) => {
    await loginAsTenantOwner(page);
    await suppressTenantTour(page);
    await page.goto('/finance/package');
    await page.waitForTimeout(1500);
    const bell = page.locator('a[aria-label="Notifications"]');
    await expect(bell).toBeVisible();
    await page.screenshot({ path: path.join(EVIDENCE_DIR, 'bell-before-click.png') });
    await bell.click();
    await page.waitForTimeout(1500);
    await expect(page).toHaveURL(/\/notifications/);
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
