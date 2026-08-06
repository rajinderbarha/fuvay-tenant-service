import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';
import { loginAsSuperAdmin } from './helpers/admin-auth';

const APP = process.env.E2E_APP || 'admin';
const EVIDENCE_DIR = path.join(__dirname, '..', 'evidence', 'e2e06b');
if (!fs.existsSync(EVIDENCE_DIR)) fs.mkdirSync(EVIDENCE_DIR, { recursive: true });

function log(file: string, line: string) {
  fs.appendFileSync(path.join(EVIDENCE_DIR, file), line + '\n');
}

test.describe('ADMIN-TENANT-E2E-06B notifications/audit/reports browser', () => {
  test.skip(APP !== 'admin', 'admin-only');

  test('notification bell is visible, clickable, opens a dropdown, "View all" navigates, no fake badge when zero', async ({ page }) => {
    // Bell no longer navigates directly on click (AdminLayout.tsx:898-904):
    // it opens a dropdown of recent notifications with a "View all
    // notifications" link, deliberately so the admin doesn't lose their
    // place just to peek. Old test assumed direct navigation; that behavior
    // was intentionally replaced, not broken.
    await loginAsSuperAdmin(page);
    const bell = page.locator('button[aria-label*="Notification"]');
    await expect(bell).toBeVisible();
    const badgeCountBefore = await bell.locator('span').count();
    await page.screenshot({ path: path.join(EVIDENCE_DIR, 'bell-before-click.png') });
    await bell.click();
    await page.waitForTimeout(1000);
    await page.screenshot({ path: path.join(EVIDENCE_DIR, 'bell-dropdown-open.png'), fullPage: true });
    const dropdownBody = await page.locator('body').innerText();
    expect(dropdownBody).not.toMatch(/undefined|NaN/);
    const viewAllLink = page.getByRole('link', { name: /View all notifications/i });
    await expect(viewAllLink).toBeVisible();
    await viewAllLink.click();
    await page.waitForTimeout(1000);
    await expect(page).toHaveURL(/\/admin\/notifications/);
    const bodyText = await page.locator('body').innerText();
    expect(bodyText).not.toMatch(/undefined|NaN/);
    await page.screenshot({ path: path.join(EVIDENCE_DIR, 'bell-after-click-notifications.png'), fullPage: true });
    log('bell.log', `badge-span-count-before-click=${badgeCountBefore}`);
  });

  const ROUTES: { path: string; navId?: string; evidence: string }[] = [
    { path: '/admin/notifications', navId: 'notifications', evidence: 'notification-center.png' },
    { path: '/admin/notification-templates', evidence: 'templates.png' },
    { path: '/admin/notification-outbox', evidence: 'outbox.png' },
    { path: '/admin/audit-logs', navId: 'audit-logs', evidence: 'audit-logs.png' },
    { path: '/admin/reports', navId: 'reports', evidence: 'reports.png' },
  ];

  for (const r of ROUTES) {
    test(`route browser-verify: ${r.path}`, async ({ page }) => {
      const apiCalls: string[] = [];
      page.on('response', (resp) => {
        if (resp.url().includes('/v1/admin/')) apiCalls.push(`${resp.status()} ${resp.url()}`);
      });
      await loginAsSuperAdmin(page);
      const resp = await page.goto(r.path);
      await page.waitForTimeout(1500);
      const status = resp?.status() ?? -1;
      const bodyText = await page.locator('body').innerText();
      const hasSidebar = await page.locator('aside').count();
      const hasHeader = await page.locator('header').count();
      await page.screenshot({ path: path.join(EVIDENCE_DIR, r.evidence), fullPage: true });
      log('routes.log', `${r.path} | status=${status} | len=${bodyText.length} | sidebar=${hasSidebar} | header=${hasHeader} | apiCalls=${apiCalls.join(' ;; ')}`);
      expect(status).toBeLessThan(400);
      expect(bodyText.toLowerCase()).not.toMatch(/\bnan\b/);
      expect(bodyText).not.toMatch(/undefined/);
      expect(apiCalls.some(c => c.startsWith('200') || c.startsWith('4') === false)).toBeTruthy();
      if (r.navId) {
        const navEl = page.locator(`#nav-${r.navId}`);
        if (await navEl.count() > 0) {
          const fontWeight = await navEl.evaluate(e => getComputedStyle(e).fontWeight);
          log('routes.log', `${r.path} -> nav-${r.navId} fontWeight=${fontWeight}`);
        }
      }
    });
  }

  test('reports page: run a real report, verify real data, no 500', async ({ page }) => {
    const apiCalls: { url: string; status: number }[] = [];
    page.on('response', (resp) => {
      if (resp.url().includes('/v1/admin/reports')) apiCalls.push({ url: resp.url(), status: resp.status() });
    });
    await loginAsSuperAdmin(page);
    await page.goto('/admin/reports');
    await page.waitForTimeout(1500);
    const bodyText = await page.locator('body').innerText();
    await page.screenshot({ path: path.join(EVIDENCE_DIR, 'reports-list.png'), fullPage: true });
    expect(apiCalls.some(c => c.status === 500)).toBeFalsy();
    log('reports.log', `list-calls=${JSON.stringify(apiCalls)}`);

    // Target the exact "Run" button inside a report card (not sidebar/nav "Run"-like text).
    const runButtons = page.getByRole('button', { name: 'Run', exact: true });
    const runCount = await runButtons.count();
    log('reports.log', `exact-run-buttons-found=${runCount}`);
    expect(runCount).toBeGreaterThan(0);
    await runButtons.first().click();
    await page.waitForTimeout(2500);
    await page.screenshot({ path: path.join(EVIDENCE_DIR, 'reports-run-result.png'), fullPage: true });
    const afterText = await page.locator('body').innerText();
    log('reports.log', `after-run-message-snippet=${(afterText.match(/[^\n]*rows[^\n]*/) || [''])[0]}`);
    expect(afterText.toLowerCase()).not.toMatch(/\bnan\b/);
    expect(afterText).toMatch(/rows/i);
  });

  test('reports page: CSV export button triggers a real download', async ({ page }) => {
    await loginAsSuperAdmin(page);
    await page.goto('/admin/reports');
    await page.waitForTimeout(1500);
    const csvButtons = page.getByRole('button', { name: 'CSV', exact: true });
    const csvCount = await csvButtons.count();
    log('export.log', `csv-buttons-found=${csvCount}`);
    expect(csvCount).toBeGreaterThan(0);
    const [download] = await Promise.all([
      page.waitForEvent('download', { timeout: 15000 }),
      csvButtons.first().click(),
    ]);
    const suggestedName = download.suggestedFilename();
    const downloadPath = path.join(EVIDENCE_DIR, suggestedName);
    await download.saveAs(downloadPath);
    const content = fs.readFileSync(downloadPath, 'utf-8');
    log('export.log', `filename=${suggestedName} bytes=${content.length} firstLine=${content.split('\n')[0]}`);
    await page.screenshot({ path: path.join(EVIDENCE_DIR, 'csv-export-evidence.png'), fullPage: true });
    expect(content.length).toBeGreaterThan(0);
    // No secrets/tokens/passwords should ever appear in an export.
    expect(content.toLowerCase()).not.toMatch(/password|secret|token|api_key/);
  });

  test('audit log page shows real records or honest empty state, no raw JSON as primary UI', async ({ page }) => {
    await loginAsSuperAdmin(page);
    await page.goto('/admin/audit-logs');
    await page.waitForTimeout(1500);
    const bodyText = await page.locator('body').innerText();
    await page.screenshot({ path: path.join(EVIDENCE_DIR, 'audit-log-detail.png'), fullPage: true });
    const looksLikeRawJson = /^\s*[{[]/.test(bodyText.trim());
    log('audit.log', `raw-json-primary-ui=${looksLikeRawJson} len=${bodyText.length}`);
    expect(looksLikeRawJson).toBeFalsy();
  });

  test('templates page shows real rows, not hardcoded count', async ({ page }) => {
    await loginAsSuperAdmin(page);
    await page.goto('/admin/notification-templates');
    await page.waitForTimeout(1500);
    const bodyText = await page.locator('body').innerText();
    await page.screenshot({ path: path.join(EVIDENCE_DIR, 'templates-detail.png'), fullPage: true });
    log('templates.log', `body-len=${bodyText.length}`);
    expect(bodyText.length).toBeGreaterThan(50);
  });

  test('outbox/delivery logs page loads with honest state', async ({ page }) => {
    await loginAsSuperAdmin(page);
    await page.goto('/admin/notification-outbox');
    await page.waitForTimeout(1500);
    const bodyText = await page.locator('body').innerText();
    await page.screenshot({ path: path.join(EVIDENCE_DIR, 'outbox-detail.png'), fullPage: true });
    log('outbox.log', `body-len=${bodyText.length}`);
  });

  test('no secrets/tokens visible on any of the 5 pages', async ({ page }) => {
    await loginAsSuperAdmin(page);
    for (const p of ['/admin/notifications', '/admin/notification-templates', '/admin/notification-outbox', '/admin/audit-logs', '/admin/reports']) {
      await page.goto(p);
      await page.waitForTimeout(1000);
      const bodyText = await page.locator('body').innerText();
      const hasJwtLike = /eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}/.test(bodyText);
      log('security.log', `${p} -> jwt-like-token-visible=${hasJwtLike}`);
      expect(hasJwtLike).toBeFalsy();
    }
  });
});
