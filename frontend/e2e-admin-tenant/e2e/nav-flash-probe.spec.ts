/**
 * Diagnostic probe (not an assertion suite): samples the admin sidebar's
 * link set over the first seconds after a hard load, to identify menu items
 * that appear and then DISAPPEAR (reported symptom: "some menu shows then
 * hide" on refresh).
 *
 * Prints a timeline plus, explicitly, the set difference between the
 * earliest and final samples so a vanish is unambiguous rather than
 * inferred from counts.
 */
import { test, expect } from '@playwright/test';
import { loginAsSuperAdmin } from './helpers/admin-auth';

test('probe: admin sidebar link set over time after reload', async ({ page }) => {
  await loginAsSuperAdmin(page);
  await page.goto('/admin/dashboard');

  const samples: { t: number; links: string[] }[] = [];
  for (let i = 0; i < 12; i++) {
    const links = await page.locator('aside a[href^="/admin"]').evaluateAll(
      els => els.map(e => (e as HTMLAnchorElement).getAttribute('href') || '').filter(Boolean),
    );
    samples.push({ t: i * 400, links });
    await page.waitForTimeout(400);
  }

  for (const s of samples) {
    console.log(`  t=${String(s.t).padStart(4)}ms  count=${String(s.links.length).padStart(3)}`);
  }

  const first = samples.find(s => s.links.length > 0);
  const last = samples[samples.length - 1];
  if (first) {
    const vanished = first.links.filter(h => !last.links.includes(h));
    const appeared = last.links.filter(h => !first.links.includes(h));
    console.log(`\n  first non-empty sample: t=${first.t}ms count=${first.links.length}`);
    console.log(`  final sample:           t=${last.t}ms count=${last.links.length}`);
    console.log(`\n  VANISHED (shown then hidden) [${vanished.length}]:`);
    vanished.forEach(h => console.log(`     - ${h}`));
    console.log(`\n  APPEARED (hidden then shown) [${appeared.length}]:`);
    appeared.forEach(h => console.log(`     + ${h}`));
  }

  expect(last.links.length).toBeGreaterThan(0);
});
