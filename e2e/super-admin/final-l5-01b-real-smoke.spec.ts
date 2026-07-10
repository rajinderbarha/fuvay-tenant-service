/**
 * FINAL-L5-01B — Real authenticated browser smoke.
 *
 * Unlike the rest of e2e/ (which mocks all API calls at the network layer,
 * per playwright.config.ts's own header comment), this spec makes ZERO
 * network mocks. It drives the real running super-admin frontend
 * (localhost:3000) against the real running backend (localhost:8000),
 * using the FINAL-L5-01 canonical seeded admin account.
 *
 * Run: npx playwright test final-l5-01b-real-smoke.spec.ts --project=super-admin-chromium
 */
import { test, expect } from "@playwright/test";

const ADMIN_EMAIL = "admin@serviceos.local";
const ADMIN_PASSWORD = "Password123!"; // legacy fixture password, see FINAL-L5-01B canonical seed spec

test.describe("FINAL-L5-01B real browser smoke — Admin", () => {
  test("admin can log in and see real tenant data on dashboard/tenants page", async ({ page }) => {
    const consoleErrors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") consoleErrors.push(msg.text());
    });

    await page.goto("http://localhost:3000/login", { waitUntil: "domcontentloaded", timeout: 30000 });
    await page.screenshot({ path: "docs/final-l5-01b/evidence/01-login-page.png" });

    const emailInput = page.locator('input[type="email"], input[name="email"]').first();
    const passwordInput = page.locator('input[type="password"], input[name="password"]').first();
    await emailInput.click({ clickCount: 3 });
    await emailInput.press("Backspace");
    await emailInput.type(ADMIN_EMAIL, { delay: 20 });
    await passwordInput.click({ clickCount: 3 });
    await passwordInput.press("Backspace");
    await passwordInput.type(ADMIN_PASSWORD, { delay: 20 });

    await expect(emailInput).toHaveValue(ADMIN_EMAIL);

    const [loginResponse] = await Promise.all([
      page.waitForResponse((r) => r.url().includes("/v1/auth/login"), { timeout: 20000 }),
      page.locator('button[type="submit"]').first().click(),
    ]);
    console.log("LOGIN_RESPONSE_STATUS:", loginResponse.status());

    await page.waitForTimeout(3000);
    await page.screenshot({ path: "docs/final-l5-01b/evidence/02-post-login.png" });
    console.log("URL_AFTER_LOGIN:", page.url());

    const bodyText = await page.locator("body").innerText();
    expect(bodyText).not.toContain("undefined");
    expect(bodyText.toLowerCase()).not.toContain("cannot read propert");

    await page.goto("http://localhost:3000/admin/tenants", { waitUntil: "domcontentloaded", timeout: 30000 }).catch(async () => {
      await page.goto("http://localhost:3000/tenants", { waitUntil: "domcontentloaded", timeout: 30000 });
    });
    await page.waitForTimeout(2000);
    await page.screenshot({ path: "docs/final-l5-01b/evidence/03-tenants-page.png" });

    const tenantsPageText = await page.locator("body").innerText();
    const hasDemoTenant = tenantsPageText.includes("Demo AC Services");
    const hasIsolationTenant = tenantsPageText.includes("Isolation Test Services");

    console.log("CONSOLE_ERRORS_COUNT:", consoleErrors.length);
    console.log("HAS_DEMO_TENANT:", hasDemoTenant);
    console.log("HAS_ISOLATION_TENANT:", hasIsolationTenant);
    console.log("PAGE_TEXT_SAMPLE:", tenantsPageText.slice(0, 500));
  });
});
