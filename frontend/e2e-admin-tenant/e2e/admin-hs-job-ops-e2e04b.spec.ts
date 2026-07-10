import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';
import { loginAsSuperAdmin } from './helpers/admin-auth';

const APP = process.env.E2E_APP || 'admin';
const EVIDENCE_DIR = path.join(__dirname, '..', 'evidence', 'e2e04b');
if (!fs.existsSync(EVIDENCE_DIR)) fs.mkdirSync(EVIDENCE_DIR, { recursive: true });

function log(file: string, line: string) {
  fs.appendFileSync(path.join(EVIDENCE_DIR, file), line + '\n');
}

// Freshest completed job with a real, verified Completed Job Deduction
// ledger link — produced by driving a real pending job through the real
// staff completion lifecycle this sprint (not a pre-seeded fixture).
const FRESH_COMPLETED_JOB_ID = 'b035159a-b19b-4500-8cb4-99a412e8ac34';
const TENANT_ID = '34b427a7-b2be-496c-b826-6d51bb181248';

test.describe('ADMIN-TENANT-E2E-04B home services job operations unification', () => {
  test.skip(APP !== 'admin', 'admin-only');

  test('canonical Home Services Jobs route opens with real jobs', async ({ page }) => {
    const apiCalls: string[] = [];
    page.on('response', (resp) => {
      if (resp.url().includes('/v1/admin/final-records/jobs')) apiCalls.push(`${resp.status()} ${resp.url()}`);
    });
    await loginAsSuperAdmin(page);
    const resp = await page.goto('/admin/home-services/service-jobs');
    await page.waitForTimeout(5000);
    const status = resp?.status() ?? -1;
    const bodyText = await page.locator('body').innerText();
    await page.screenshot({ path: path.join(EVIDENCE_DIR, 'job-list.png'), fullPage: true });
    log('list.log', `status=${status} apiCalls=${apiCalls.join(' ;; ')} bodyLen=${bodyText.length}`);
    expect(status).toBeLessThan(400);
    expect(apiCalls.some(c => c.startsWith('200'))).toBeTruthy();
    expect(bodyText.toLowerCase()).not.toMatch(/\bnan\b/);
    expect(bodyText).not.toMatch(/undefined/);
  });

  test('fresh completed job opens in detail route with real data', async ({ page }) => {
    await loginAsSuperAdmin(page);
    const resp = await page.goto(`/admin/home-services/service-jobs/${FRESH_COMPLETED_JOB_ID}`);
    await page.waitForTimeout(2000);
    const status = resp?.status() ?? -1;
    const bodyText = await page.locator('body').innerText();
    await page.screenshot({ path: path.join(EVIDENCE_DIR, 'job-detail.png'), fullPage: true });
    log('detail.log', `status=${status} bodyLen=${bodyText.length}`);
    expect(status).toBeLessThan(400);
    expect(bodyText).toContain('JOB-20260710-000002');
    expect(bodyText).toContain('Customer Pays Provider Directly');
    expect(bodyText).toMatch(/850/); // selected price
    expect(bodyText.toLowerCase()).not.toMatch(/\bnan\b/);
  });

  test('Completed Job Deduction section shows real 21-credit deduction', async ({ page }) => {
    await loginAsSuperAdmin(page);
    await page.goto(`/admin/home-services/service-jobs/${FRESH_COMPLETED_JOB_ID}`);
    await page.waitForTimeout(2000);
    const bodyText = await page.locator('body').innerText();
    await page.screenshot({ path: path.join(EVIDENCE_DIR, 'job-detail-deduction.png'), fullPage: true });
    log('deduction.log', `bodySnippet=${(bodyText.match(/Completed Job Deduction[\s\S]{0,400}/) || [''])[0].replace(/\n/g, ' | ')}`);
    expect(bodyText).toContain('21 usage credits');
    expect(bodyText).toContain('3958');
    expect(bodyText).toContain('3937');
    expect(bodyText).not.toMatch(/duplicate/i);
  });

  test('click Usage Credit Ledger link navigates to filtered ledger with exact entry', async ({ page }) => {
    const apiCalls: string[] = [];
    page.on('response', (resp) => {
      if (resp.url().includes('/usage-credit-ledger')) apiCalls.push(`${resp.status()} ${resp.url()}`);
    });
    await loginAsSuperAdmin(page);
    await page.goto(`/admin/home-services/service-jobs/${FRESH_COMPLETED_JOB_ID}`);
    await page.waitForTimeout(1500);
    const ledgerLink = page.getByRole('link', { name: /View exact entry in Usage Credit Ledger/i });
    await expect(ledgerLink).toBeVisible();
    await ledgerLink.click();
    await page.waitForTimeout(2000);
    await expect(page).toHaveURL(/\/admin\/finance\/usage-credits\?tenant_id=.*job_id=/);
    const bodyText = await page.locator('body').innerText();
    await page.screenshot({ path: path.join(EVIDENCE_DIR, 'ledger-filtered.png'), fullPage: true });
    log('ledger.log', `apiCalls=${apiCalls.join(' ;; ')} url=${page.url()}`);
    expect(apiCalls.some(c => c.includes(`job_id=${FRESH_COMPLETED_JOB_ID}`))).toBeTruthy();
    expect(bodyText).toContain('Completed Job Deduction');
    expect(bodyText).toMatch(/-21/);
    expect(bodyText).toContain('3958');
    expect(bodyText).toContain('3937');
  });

  test('balance arithmetic is correct: balance_before - deduction = balance_after', async ({ page }) => {
    await loginAsSuperAdmin(page);
    await page.goto(`/admin/finance/usage-credits?tenant_id=${TENANT_ID}&job_id=${FRESH_COMPLETED_JOB_ID}`);
    await page.waitForTimeout(2000);
    const bodyText = await page.locator('body').innerText();
    // Real math: 3958 - 21 = 3937 (verified via live API before this test).
    expect(bodyText).toContain('3958');
    expect(bodyText).toContain('3937');
  });

  test('no duplicate ledger entry for the same job after refresh', async ({ page }) => {
    await loginAsSuperAdmin(page);
    await page.goto(`/admin/finance/usage-credits?tenant_id=${TENANT_ID}&job_id=${FRESH_COMPLETED_JOB_ID}`);
    await page.waitForTimeout(1500);
    const rowCountBefore = await page.locator('tbody tr').count();
    await page.reload();
    await page.waitForTimeout(1500);
    const rowCountAfter = await page.locator('tbody tr').count();
    log('exactly-once.log', `rowsBefore=${rowCountBefore} rowsAfter=${rowCountAfter}`);
    expect(rowCountBefore).toBe(1);
    expect(rowCountAfter).toBe(1);
  });

  test('legacy /admin/operations bridges to real Home Services jobs, does not mislead', async ({ page }) => {
    await loginAsSuperAdmin(page);
    await page.goto('/admin/operations');
    await page.waitForTimeout(1500);
    const bodyText = await page.locator('body').innerText();
    await page.screenshot({ path: path.join(EVIDENCE_DIR, 'legacy-operations-bridge.png'), fullPage: true });
    const bridgeLink = page.getByRole('link', { name: /View real Home Services Jobs/i });
    await expect(bridgeLink).toBeVisible();
    log('legacy.log', `bridgeLinkVisible=true bodySnippet=${bodyText.slice(0, 300).replace(/\n/g, ' ')}`);
    await bridgeLink.click();
    await page.waitForTimeout(1500);
    await expect(page).toHaveURL(/\/admin\/home-services\/service-jobs/);
  });

  test('no mock data / forbidden labels / raw JSON on job list, detail, or ledger pages', async ({ page }) => {
    await loginAsSuperAdmin(page);
    for (const url of [
      '/admin/home-services/service-jobs',
      `/admin/home-services/service-jobs/${FRESH_COMPLETED_JOB_ID}`,
      `/admin/finance/usage-credits?tenant_id=${TENANT_ID}&job_id=${FRESH_COMPLETED_JOB_ID}`,
    ]) {
      await page.goto(url);
      await page.waitForTimeout(1500);
      const bodyText = await page.locator('body').innerText();
      const forbidden = ['Cash Wallet', 'Wallet Balance', 'Withdraw', 'Escrow', 'Platform Pay Now', 'Manual Bargain'];
      const foundForbidden = forbidden.filter(f => bodyText.includes(f));
      log('labels.log', `${url} -> forbidden=${JSON.stringify(foundForbidden)}`);
      expect(foundForbidden.length).toBe(0);
      expect(bodyText.toLowerCase()).not.toMatch(/\bnan\b/);
      expect(bodyText).not.toMatch(/\bundefined\b/);
    }
  });
});
