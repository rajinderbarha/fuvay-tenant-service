/**
 * Diagnostic probe for the reported "some menu shows then hide" on refresh,
 * tenant portal.
 *
 * Unlike the admin sidebar (which fails CLOSED while permissions load, so
 * items pop IN), TenantLayout's itemVisible() fails OPEN --
 * `if (verticalCapabilities === null) return true` -- so items render first
 * and are then REMOVED once capabilities resolve. This samples the link set
 * to prove/measure that vanish.
 *
 * Run with E2E_APP=tenant.
 */
import { test, expect } from '@playwright/test';
import { loginAsTenantOwner } from './helpers/tenant-auth';

test('probe: tenant sidebar link set over time after reload', async ({ page }) => {
  await loginAsTenantOwner(page);
  await page.goto('/dashboard');

  const samples: { t: number; links: string[] }[] = [];
  for (let i = 0; i < 12; i++) {
    const links = await page.locator('aside a').evaluateAll(
      els => els.map(e => (e as HTMLAnchorElement).getAttribute('href') || '').filter(Boolean),
    );
    samples.push({ t: i * 400, links });
    await page.waitForTimeout(400);
  }

  for (const s of samples) {
    console.log(`  t=${String(s.t).padStart(4)}ms  count=${String(s.links.length).padStart(3)}`);
  }

  const peak = samples.reduce((a, b) => (b.links.length > a.links.length ? b : a), samples[0]);
  const last = samples[samples.length - 1];
  const vanished = peak.links.filter(h => !last.links.includes(h));

  console.log(`\n  peak sample:  t=${peak.t}ms count=${peak.links.length}`);
  console.log(`  final sample: t=${last.t}ms count=${last.links.length}`);
  console.log(`\n  VANISHED after peak (shown then hidden) [${vanished.length}]:`);
  vanished.forEach(h => console.log(`     - ${h}`));

  expect(last.links.length).toBeGreaterThan(0);
});
