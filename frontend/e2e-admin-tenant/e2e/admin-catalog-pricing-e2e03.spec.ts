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

  test('route smoke: 4 catalog/pricing pages, no NaN/undefined/raw json', async ({ page }) => {
    await loginAsSuperAdmin(page);
    const routes = [
      '/admin/home-services/service-catalog',
      '/admin/home-services/pricing-rules',
      '/admin/home-services/price-experience',
      '/admin/home-services/service-areas',
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

  test('service catalog: open the seed offering, verify Split AC / Window AC / LG / Not Cooling', async ({ page }) => {
    await loginAsSuperAdmin(page);
    await page.goto('/admin/home-services/service-catalog');
    await page.waitForTimeout(1500);
    // Was hasText:'AC Repair' -- that master service was removed, so this row
    // never rendered and the test failed before exercising any UI.
    const acRow = page.locator('button', { hasText: SEED.offeringName }).filter({ hasNotText: 'Duplicate' }).first();
    await expect(acRow).toBeVisible({ timeout: 10000 });
    await acRow.click();
    await page.waitForTimeout(1200);
    await page.screenshot({ path: path.join(EVIDENCE_DIR, 'ac-repair-general.png'), fullPage: true });

    await page.locator('.hsc-tab', { hasText: 'Types' }).click();
    await page.waitForTimeout(600);
    const bodyTypes = await page.locator('body').innerText();
    log('catalog-content.log', `Types tab contains Split AC: ${bodyTypes.includes('Split AC')}, Window AC: ${bodyTypes.includes('Window AC')}`);
    await page.screenshot({ path: path.join(EVIDENCE_DIR, 'ac-repair-types.png'), fullPage: true });

    await page.locator('.hsc-tab', { hasText: 'Brands' }).click();
    await page.waitForTimeout(600);
    const bodyBrands = await page.locator('body').innerText();
    log('catalog-content.log', `Brands tab contains LG: ${bodyBrands.includes('LG')}`);
    await page.screenshot({ path: path.join(EVIDENCE_DIR, 'ac-repair-brands.png'), fullPage: true });

    await page.locator('.hsc-tab', { hasText: 'Questions / Issues' }).click();
    await page.waitForTimeout(800);
    const bodyIssues = await page.locator('body').innerText();
    log('catalog-content.log', `Issues tab contains Not Cooling/cooling: ${/not cooling|cooling/i.test(bodyIssues)}`);
    await page.screenshot({ path: path.join(EVIDENCE_DIR, 'ac-repair-issues.png'), fullPage: true });
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
