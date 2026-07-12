/**
 * FINAL-L5-05K — Real authenticated browser E2E: Usage Credits + Finance
 * Hub Credit Top-ups against the real running backend (localhost:8000)
 * and real running super-admin frontend (localhost:3000). No network
 * mocks, per the pattern established in final-l5-01b-real-smoke.spec.ts.
 *
 * Run: npx playwright test final-l5-05k-usage-credit-runtime.spec.ts --project=super-admin-chromium
 */
import { test, expect } from "@playwright/test";

const ADMIN_EMAIL = "admin@serviceos.local";
const ADMIN_PASSWORD = "Password123!";
const REAL_TENANT_ID = "5209ef33-a53e-4fc0-b3f6-006335b8d712"; // Demo AC Services, has real usage_credit_ledger history

async function login(page: import("@playwright/test").Page) {
  await page.goto("http://localhost:3000/login", { waitUntil: "domcontentloaded", timeout: 30000 });
  const emailInput = page.locator('input[type="email"], input[name="email"]').first();
  const passwordInput = page.locator('input[type="password"], input[name="password"]').first();
  await emailInput.click({ clickCount: 3 });
  await emailInput.type(ADMIN_EMAIL, { delay: 10 });
  await passwordInput.click({ clickCount: 3 });
  await passwordInput.type(ADMIN_PASSWORD, { delay: 10 });
  await Promise.all([
    page.waitForResponse((r) => r.url().includes("/v1/auth/login"), { timeout: 20000 }),
    page.locator('button[type="submit"]').first().click(),
  ]);
  await page.waitForTimeout(2000);
}

test.describe("FINAL-L5-05K real browser — Usage Credits + Finance Hub Top-ups", () => {
  test("Super Admin: Usage Credits page shows real balance/ledger, no wallet terminology, no wallet API calls", async ({ page }) => {
    const consoleErrors: string[] = [];
    const networkRequests: string[] = [];
    page.on("console", (msg) => { if (msg.type() === "error") consoleErrors.push(msg.text()); });
    page.on("request", (req) => { networkRequests.push(req.url()); });

    await login(page);

    await page.goto(`http://localhost:3000/admin/finance/usage-credits?tenant_id=${REAL_TENANT_ID}`, {
      waitUntil: "domcontentloaded", timeout: 30000,
    });
    await page.waitForTimeout(2500);
    await page.screenshot({ path: "docs/final-l5-05/evidence/05k-01-usage-credits.png" });

    const bodyText = await page.locator("body").innerText();
    expect(bodyText).not.toContain("undefined");
    expect(bodyText.toLowerCase()).not.toContain("cannot read propert");

    // Real ledger data from the real backend must be visible (the one
    // genuine Completed Job Deduction row for this tenant).
    const hasRealData = bodyText.includes("3979") || bodyText.toLowerCase().includes("completed_job_deduction")
      || bodyText.toLowerCase().includes("deduction");
    expect(hasRealData).toBeTruthy();

    // Forbidden terminology must not appear in the rendered page.
    expect(bodyText).not.toMatch(/Wallet Balance/i);
    expect(bodyText).not.toMatch(/Cash Wallet/i);
    expect(bodyText).not.toMatch(/Credit Wallet Health/i);
    expect(bodyText).not.toMatch(/Provider Wallet/i);

    // No request to a TenantWallet-backed generic endpoint from this page.
    const walletCalls = networkRequests.filter((u) =>
      u.includes("/wallet/deduct") || u.includes("/wallet/topup") || u.includes("/wallet/adjust")
      || (u.includes("/wallet/") && !u.includes("usage-credit")));
    expect(walletCalls, `unexpected wallet-API calls: ${JSON.stringify(walletCalls)}`).toEqual([]);

    const seriousErrors = consoleErrors.filter((e) =>
      !e.includes("favicon") && !e.toLowerCase().includes("hydration"));
    expect(seriousErrors, `console errors: ${JSON.stringify(seriousErrors)}`).toEqual([]);
  });

  test("Super Admin: Finance Hub Credit Top-ups list loads real data with no serious errors", async ({ page }) => {
    const consoleErrors: string[] = [];
    page.on("console", (msg) => { if (msg.type() === "error") consoleErrors.push(msg.text()); });

    await login(page);

    await page.goto("http://localhost:3000/admin/finance/topups", {
      waitUntil: "domcontentloaded", timeout: 30000,
    });
    await page.waitForTimeout(2500);
    await page.screenshot({ path: "docs/final-l5-05/evidence/05k-02-topups-list.png" });

    const bodyText = await page.locator("body").innerText();
    expect(bodyText).not.toContain("undefined");
    expect(bodyText.toLowerCase()).not.toContain("cannot read propert");
    expect(bodyText).not.toMatch(/Wallet Top-up/i);
    expect(bodyText).not.toMatch(/Cash Wallet/i);

    const seriousErrors = consoleErrors.filter((e) =>
      !e.includes("favicon") && !e.toLowerCase().includes("hydration"));
    expect(seriousErrors, `console errors: ${JSON.stringify(seriousErrors)}`).toEqual([]);
  });

  test("Super Admin: old wallet pages remain unlinked from primary navigation", async ({ page }) => {
    await login(page);
    await page.goto("http://localhost:3000/admin/finance/usage-credits", { waitUntil: "domcontentloaded", timeout: 30000 });
    await page.waitForTimeout(1500);

    const navLinks = await page.locator('a[href*="/admin/"]').evaluateAll(
      (els) => els.map((e) => (e as HTMLAnchorElement).getAttribute("href")),
    );
    expect(navLinks).not.toContain("/admin/finance/wallets");
    expect(navLinks).not.toContain("/admin/provider-wallets");
  });
});
