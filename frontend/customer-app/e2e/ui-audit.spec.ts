import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';
import { loginViaUi } from './helpers/auth';
import { CUSTOMER_ONE } from './helpers/api';

// Read-only UI audit: captures each customer surface at a real phone
// viewport and records console errors + rendered text. Asserts nothing
// about business data -- its output is the evidence, not a pass/fail gate.
const DIR = path.join(__dirname, '..', 'evidence', 'ui-audit');
if (!fs.existsSync(DIR)) fs.mkdirSync(DIR, { recursive: true });

const ROUTES = [
  ['home', '/customer/home-services'],
  ['book', '/customer/home-services/book'],
  ['bookings', '/customer/bookings'],
  ['profile', '/customer/profile'],
  ['notifications', '/customer/notifications'],
  ['invoices', '/customer/invoices'],
  ['credits', '/customer/credits'],
  ['chat', '/customer/chat'],
  ['complaints', '/customer/complaints'],
  ['reviews', '/customer/reviews'],
  ['privacy', '/customer/privacy'],
];

test.use({ viewport: { width: 390, height: 844 } }); // iPhone 14 Pro

for (const [name, url] of ROUTES) {
  test(`capture ${name}`, async ({ page }) => {
    const consoleErrors: string[] = [];
    page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push(m.text()); });
    page.on('pageerror', (e) => consoleErrors.push(`PAGEERROR: ${e.message}`));

    await loginViaUi(page, CUSTOMER_ONE.email, CUSTOMER_ONE.password);
    const resp = await page.goto(url, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2500);
    await page.screenshot({ path: path.join(DIR, `${name}.png`), fullPage: true });
    const body = await page.locator('body').innerText();
    fs.writeFileSync(path.join(DIR, `${name}.txt`), [
      `### ${name}  (${url})`,
      `status=${resp?.status()}  textLen=${body.length}`,
      `consoleErrors=${consoleErrors.length ? JSON.stringify(consoleErrors, null, 2) : 'none'}`,
      `--- rendered text ---`,
      body,
    ].join('\n'));
    expect(resp?.status() ?? 0).toBeLessThan(400);
  });
}
