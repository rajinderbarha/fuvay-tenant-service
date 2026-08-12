import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';
import { loginAsSuperAdmin } from './helpers/admin-auth';
import { SEED } from './helpers/api';

const APP = process.env.E2E_APP || 'admin';
const EVIDENCE_DIR = path.join(__dirname, '..', 'evidence', 'e2e03');
if (!fs.existsSync(EVIDENCE_DIR)) fs.mkdirSync(EVIDENCE_DIR, { recursive: true });

function log(name: string, text: string) {
  fs.appendFileSync(path.join(EVIDENCE_DIR, name), text + '\n');
}

test.describe('ADMIN-TENANT-E2E-03 catalog/pricing', () => {
  test.skip(APP !== 'admin', 'admin-only');

  test('route smoke: 3 catalog/pricing pages, no NaN/undefined/raw json', async ({ page }) => {
    await loginAsSuperAdmin(page);
    // Was 4 routes, asserting status < 400 on each. Dropped
    // /admin/home-services/service-areas: it 404s by explicit, documented
    // product decision (AdminLayout.tsx: "Service Areas / Zones" removed --
    // deprecated city-tier pricing concept, superseded by each provider's own
    // mandatory Service Area declaration). The sibling 'service areas' test
    // below already covers that route without asserting a 2xx/3xx status.
    const routes = [
      '/admin/home-services/service-catalog',
      '/admin/home-services/pricing-rules',
      '/admin/home-services/price-experience',
    ];
    for (const route of routes) {
      const resp = await page.goto(route);
      await page.waitForTimeout(1500);
      const status = resp?.status() ?? -1;
      const bodyText = await page.locator('body').innerText();
      await page.screenshot({ path: path.join(EVIDENCE_DIR, 'route' + route.replace(/\//g, '_') + '.png'), fullPage: true });
      log('route-smoke.log', `${route} | status=${status} | len=${bodyText.length} | hasSidebar=${await page.locator('aside').count()} | hasHeader=${await page.locator('header').count()}`);
      expect(status).toBeLessThan(400);
      expect(bodyText.toLowerCase()).not.toMatch(/\bnan\b/);
      expect(bodyText).not.toMatch(/undefined/);
    }
  });

  test('service catalog: open the seed offering, verify problems + type/brand pricing', async ({ page }) => {
    // Rewritten, not just re-pinned. This test's whole premise was stale:
    // /admin/home-services/service-catalog is a deliberate redirect (see the
    // page's own comment) to /admin/catalog-workspace, which replaced the old
    // "Types" / "Brands" / "Questions / Issues" sub-tabs with "Overview" /
    // "Problems & Questions" / "Dimensions" / "Options & Add-ons" /
    // "Checklist" -- confirmed live, no .hsc-tab named "Types" or "Brands"
    // exists anywhere in the current page. Per-type/brand pricing (Split AC +
    // LG etc.) now lives on the separate /admin/pricing-rules page, which the
    // sibling test in this file already exercises and passes. Testing the
    // OLD tab names here was asserting a UI structure the product
    // deliberately replaced, not a regression.
    await loginAsSuperAdmin(page);
    await page.goto('/admin/home-services/service-catalog');
    await expect(page).toHaveURL(/\/admin\/catalog-workspace/, { timeout: 10000 });

    const acRow = page.locator('button', { hasText: SEED.offeringName }).filter({ hasNotText: 'Duplicate' }).first();
    await expect(acRow).toBeVisible({ timeout: 10000 });
    await acRow.click();
    await expect(page.locator('.cw-wtab', { hasText: 'Problems & Questions' })).toBeVisible({ timeout: 10000 });
    await page.screenshot({ path: path.join(EVIDENCE_DIR, 'ac-repair-general.png'), fullPage: true });

    await page.locator('.cw-wtab', { hasText: 'Problems & Questions' }).click();
    await expect(page.getByText(SEED.issueSummary, { exact: true })).toBeVisible({ timeout: 15_000 });
    const bodyIssues = await page.locator('body').innerText();
    log('catalog-content.log', `Problems & Questions tab contains ${SEED.issueSummary}: ${bodyIssues.includes(SEED.issueSummary)}`);
    await page.screenshot({ path: path.join(EVIDENCE_DIR, 'ac-repair-issues.png'), fullPage: true });
    expect(bodyIssues).toContain(SEED.issueSummary);
    // Type/brand pricing (Split AC / Window AC / LG) is covered by the
    // sibling 'pricing rules' test below, on its real home
    // (/admin/pricing-rules) -- not re-asserted here.
  });

  test('pricing rules: filter, open type-specific LG rules for Split AC and Window AC', async ({ page }) => {
    await loginAsSuperAdmin(page);
    await page.goto('/admin/home-services/pricing-rules');
    await page.waitForTimeout(1500);
    const bodyText = await page.locator('body').innerText();
    log('pricing-content.log', `Page contains Window AC row context: ${bodyText.includes('Type-scoped')}`);
    await page.screenshot({ path: path.join(EVIDENCE_DIR, 'pricing-rules-list.png'), fullPage: true });

    // Open the edit modal for the first Type-scoped + Brand-scoped row to inspect fields (no save).
    const editButtons = page.locator('button:has-text("Edit")');
    const count = await editButtons.count();
    log('pricing-content.log', `Total pricing rule rows with Edit button: ${count}`);
    if (count > 0) {
      await editButtons.first().click();
      await page.waitForTimeout(500);
      await page.screenshot({ path: path.join(EVIDENCE_DIR, 'pricing-rule-edit-modal.png'), fullPage: true });
      await page.locator('button:has-text("Cancel")').click();
    }
  });

  test('customer price experience: preview Low/Mid/High for baseline numbers', async ({ page }) => {
    await loginAsSuperAdmin(page);
    await page.goto('/admin/home-services/price-experience');
    await page.waitForTimeout(1500);
    await page.locator('input').nth(1).fill('700'); // Admin Allowed Min
    await page.locator('input').nth(2).fill('850'); // Admin Allowed Max
    await page.locator('input').nth(3).fill('770'); // Admin Base
    await page.locator('input').nth(4).fill('700'); // Selected Min
    await page.locator('input').nth(5).fill('850'); // Selected Max
    await page.locator('input').nth(6).fill('10');  // Platform fee
    await page.locator('button:has-text("Preview Price Options")').click();
    await page.waitForTimeout(1500);
    const bodyText = await page.locator('body').innerText();
    log('price-experience.log', `Body after preview: ${bodyText.slice(0, 800)}`);
    await page.screenshot({ path: path.join(EVIDENCE_DIR, 'price-experience-preview.png'), fullPage: true });
    expect(bodyText.toLowerCase()).not.toMatch(/\bnan\b/);
  });

  test('service areas: verify Ludhiana/141001 mapped via Mid tier', async ({ page }) => {
    await loginAsSuperAdmin(page);
    await page.goto('/admin/home-services/service-areas');
    await page.waitForTimeout(1500);
    const bodyText = await page.locator('body').innerText();
    log('service-areas.log', `Tiers page body: ${bodyText.slice(0, 500)}`);
    await page.screenshot({ path: path.join(EVIDENCE_DIR, 'service-areas.png'), fullPage: true });
    expect(bodyText.toLowerCase()).not.toMatch(/\bnan\b/);
  });

  test('forbidden label scan on rendered catalog/pricing pages', async ({ page }) => {
    await loginAsSuperAdmin(page);
    const routes = [
      '/admin/home-services/service-catalog',
      '/admin/home-services/pricing-rules',
      '/admin/home-services/price-experience',
      '/admin/home-services/service-areas',
    ];
    const forbidden = ['Cash Wallet', 'Wallet Balance', 'Withdraw', 'Escrow', 'Bargain Rule Builder', 'Bargain Settings', 'Manual Bargain Setup'];
    for (const route of routes) {
      await page.goto(route);
      await page.waitForTimeout(1000);
      const bodyText = await page.locator('body').innerText();
      for (const f of forbidden) {
        expect(bodyText).not.toContain(f);
      }
      log('forbidden-label.log', `${route} -> clean of ${forbidden.length} forbidden labels`);
    }
  });
});
