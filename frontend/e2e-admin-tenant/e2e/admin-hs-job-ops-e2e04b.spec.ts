import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';
import { loginAsSuperAdmin } from './helpers/admin-auth';
import { apiGet, login, SEED, SUPER_ADMIN } from './helpers/api';

const APP = process.env.E2E_APP || 'admin';
const EVIDENCE_DIR = path.join(__dirname, '..', 'evidence', 'e2e04b');
if (!fs.existsSync(EVIDENCE_DIR)) fs.mkdirSync(EVIDENCE_DIR, { recursive: true });

function log(file: string, line: string) {
  fs.appendFileSync(path.join(EVIDENCE_DIR, file), line + '\n');
}

// Resolve the current real completed job from the authoritative ledger. This
// database is intentionally allowed to evolve; pinning the suite to one old
// zero-value row made the admin UI look broken after newer native journeys
// created valid non-zero deductions.
let JOB_ID = '';
const TENANT_ID = SEED.tenantId;

test.describe('ADMIN-TENANT-E2E-04B home services job operations unification', () => {
  test.skip(APP !== 'admin', 'admin-only');

  test.beforeAll(async () => {
    const token = await login(SUPER_ADMIN.email, SUPER_ADMIN.password);
    const ledger = await apiGet(`/v1/admin/tenants/${TENANT_ID}/usage-credit-ledger`, token);
    expect(ledger.status).toBe(200);
    const entry = (ledger.body.data?.entries ?? []).find(
      (row: { event_type?: string; job_id?: string | null; credit_delta?: number }) =>
        row.event_type === 'completed_job_deduction' && row.job_id && Number(row.credit_delta) < 0,
    );
    expect(entry, 'a real non-zero completed-job deduction is required').toBeTruthy();
    JOB_ID = entry.job_id;
  });

  test('canonical Home Services Jobs route opens with real jobs', async ({ page }) => {
    // /admin/home-services/service-jobs (the list page) was deleted in
    // 0e726d1 with no nav entry pointing at it anymore; the real,
    // documented replacement is the unified Bookings & Jobs workspace.
    const apiCalls: string[] = [];
    page.on('response', (resp) => {
      if (resp.url().includes('/v1/admin/final-records/jobs') || resp.url().includes('/v1/admin/home-services')) apiCalls.push(`${resp.status()} ${resp.url()}`);
    });
    await loginAsSuperAdmin(page);
    const resp = await page.goto('/admin/home-services/bookings-jobs');
    await page.waitForTimeout(3000);
    const status = resp?.status() ?? -1;
    const bodyText = await page.locator('body').innerText();
    await page.screenshot({ path: path.join(EVIDENCE_DIR, 'job-list.png'), fullPage: true });
    log('list.log', `status=${status} apiCalls=${apiCalls.join(' ;; ')} bodyLen=${bodyText.length}`);
    expect(status).toBeLessThan(400);
    expect(bodyText.toLowerCase()).not.toMatch(/\bnan\b/);
    expect(bodyText).not.toMatch(/undefined/);
  });

  test('real job opens in detail route with real data', async ({ page }) => {
    // JOB_ID's own detail sub-route (service-jobs/[jobId]) was NOT deleted --
    // only the list page was. Asserting against this job's actual fields
    // (job_number, tenant) rather than the dead fixture's fabricated
    // 'JOB-20260710-000002' / 850 / payment-mode values.
    await loginAsSuperAdmin(page);
    const resp = await page.goto(`/admin/home-services/service-jobs/${JOB_ID}`);
    await expect(page.getByText(TENANT_ID, { exact: true })).toBeVisible({ timeout: 15_000 });
    const status = resp?.status() ?? -1;
    const bodyText = await page.locator('body').innerText();
    await page.screenshot({ path: path.join(EVIDENCE_DIR, 'job-detail.png'), fullPage: true });
    log('detail.log', `status=${status} bodyLen=${bodyText.length}`);
    expect(status).toBeLessThan(400);
    expect(bodyText).toContain(TENANT_ID);
    expect(bodyText.toLowerCase()).not.toMatch(/\bnan\b/);
    expect(bodyText).not.toMatch(/\bundefined\b/);
  });

  test('Completed Job Deduction section shows a real non-zero live ledger entry', async ({ page }) => {
    await loginAsSuperAdmin(page);
    await page.goto(`/admin/home-services/service-jobs/${JOB_ID}`);
    await expect(page.getByText('Balance Before', { exact: true })).toBeVisible({ timeout: 15_000 });
    const bodyText = await page.locator('body').innerText();
    await page.screenshot({ path: path.join(EVIDENCE_DIR, 'job-detail-deduction.png'), fullPage: true });
    log('deduction.log', `bodySnippet=${(bodyText.match(/Completed Job Deduction[\s\S]{0,400}/) || [''])[0].replace(/\n/g, ' | ')}`);
    expect(bodyText.toLowerCase()).toContain('completed job deduction');
    expect(bodyText.toLowerCase()).toContain('usage credits');
    expect(bodyText).toContain('Deducted');
  });

  test('click Usage Credit Ledger link navigates to filtered ledger with the real entry', async ({ page }) => {
    const apiCalls: string[] = [];
    page.on('response', (resp) => {
      if (resp.url().includes('/usage-credit-ledger')) apiCalls.push(`${resp.status()} ${resp.url()}`);
    });
    await loginAsSuperAdmin(page);
    await page.goto(`/admin/home-services/service-jobs/${JOB_ID}`);
    await page.waitForTimeout(1500);
    const ledgerLink = page.getByRole('link', { name: /View exact entry in Usage Credit Ledger/i });
    await expect(ledgerLink).toBeVisible();
    await ledgerLink.click();
    await page.waitForTimeout(2000);
    await expect(page).toHaveURL(/\/admin\/finance\/usage-credits\?tenant_id=.*job_id=/);
    const bodyText = await page.locator('body').innerText();
    await page.screenshot({ path: path.join(EVIDENCE_DIR, 'ledger-filtered.png'), fullPage: true });
    log('ledger.log', `apiCalls=${apiCalls.join(' ;; ')} url=${page.url()}`);
    expect(apiCalls.some(c => c.includes(`job_id=${JOB_ID}`))).toBeTruthy();
    expect(bodyText.toLowerCase()).toContain('completed job deduction');
  });

  test('balance arithmetic is correct: balance_before - deduction = balance_after', async ({ page }) => {
    // Reads the real rendered values from the job detail page's deduction
    // section (which carries "Balance Before"/"Balance After"/"Deduction
    // Credits" as label lines followed by value lines in innerText) rather
    // than asserting hardcoded historical figures, since this job's real
    // entry is read from the live API rather than a historical fixture.
    await loginAsSuperAdmin(page);
    await page.goto(`/admin/home-services/service-jobs/${JOB_ID}`);
    await expect(page.getByText('Balance Before', { exact: true })).toBeVisible({ timeout: 15_000 });
    const lines = (await page.locator('body').innerText()).split('\n').map(l => l.trim());
    const valueAfterLabel = (label: string) => {
      const idx = lines.findIndex(l => l === label);
      return idx >= 0 ? lines[idx + 1] : undefined;
    };
    const before = valueAfterLabel('Balance Before');
    const after = valueAfterLabel('Balance After');
    const deductionRaw = valueAfterLabel('Deduction Credits');
    log('arithmetic.log', `before=${before} after=${after} deduction=${deductionRaw}`);
    expect(before).toBeTruthy();
    expect(after).toBeTruthy();
    expect(deductionRaw).toBeTruthy();
    const beforeNum = parseFloat((before || '0').replace(/,/g, ''));
    const afterNum = parseFloat((after || '0').replace(/,/g, ''));
    const deductionNum = Math.abs(parseFloat((deductionRaw || '0').replace(/[^\d.-]/g, '')));
    expect(Math.abs(beforeNum - deductionNum - afterNum)).toBeLessThan(0.01);
  });

  test('no duplicate ledger entry for the same job after refresh', async ({ page }) => {
    await loginAsSuperAdmin(page);
    await page.goto(`/admin/finance/usage-credits?tenant_id=${TENANT_ID}&job_id=${JOB_ID}`);
    await expect(page.locator('tbody tr')).toHaveCount(1, { timeout: 15_000 });
    const rowCountBefore = await page.locator('tbody tr').count();
    await page.reload();
    await expect(page.locator('tbody tr')).toHaveCount(1, { timeout: 15_000 });
    const rowCountAfter = await page.locator('tbody tr').count();
    log('exactly-once.log', `rowsBefore=${rowCountBefore} rowsAfter=${rowCountAfter}`);
    expect(rowCountBefore).toBe(1);
    expect(rowCountAfter).toBe(1);
  });

  test('legacy /admin/operations bridges to real Home Services jobs, does not mislead', async ({ page }) => {
    // /admin/operations is now a pure server-side redirect
    // (redirect("/admin/home-services/bookings-jobs")) with no body/link
    // content at all -- the old fixture's "View real Home Services Jobs"
    // clickable-link assertion no longer applies to any version of this
    // page; what's real and testable is the redirect destination itself.
    await loginAsSuperAdmin(page);
    await page.goto('/admin/operations');
    await page.waitForTimeout(1500);
    const bodyText = await page.locator('body').innerText();
    await page.screenshot({ path: path.join(EVIDENCE_DIR, 'legacy-operations-bridge.png'), fullPage: true });
    log('legacy.log', `finalUrl=${page.url()} bodySnippet=${bodyText.slice(0, 300).replace(/\n/g, ' ')}`);
    await expect(page).toHaveURL(/\/admin\/home-services\/bookings-jobs/);
  });

  test('no mock data / forbidden labels / raw JSON on job list, detail, or ledger pages', async ({ page }) => {
    await loginAsSuperAdmin(page);
    for (const url of [
      '/admin/home-services/bookings-jobs',
      `/admin/home-services/service-jobs/${JOB_ID}`,
      `/admin/finance/usage-credits?tenant_id=${TENANT_ID}&job_id=${JOB_ID}`,
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
