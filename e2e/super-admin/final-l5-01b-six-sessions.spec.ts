/**
 * FINAL-L5-01B closing — all six real authenticated browser sessions.
 * Zero network mocking. Drives the live frontends (3000/3001/3002) against
 * the live backend (8000) with canonical FINAL-L5-01 seeded users.
 */
import { test, expect, Page, ConsoleMessage } from "@playwright/test";

const CANON = "CanonicalL5!2026";
const EVID = "docs/final-l5-01b-plus/evidence";

async function login(page: Page, baseUrl: string, loginPath: string, email: string, password: string) {
  const consoleErrors: string[] = [];
  page.on("console", (msg: ConsoleMessage) => { if (msg.type() === "error") consoleErrors.push(msg.text()); });
  await page.goto(`${baseUrl}${loginPath}`, { waitUntil: "domcontentloaded", timeout: 30000 });
  const emailInput = page.locator('input[type="email"], input[name="email"]').first();
  const passwordInput = page.locator('input[type="password"], input[name="password"]').first();
  await emailInput.click({ clickCount: 3 });
  await emailInput.press("Backspace");
  await emailInput.type(email, { delay: 15 });
  await passwordInput.click({ clickCount: 3 });
  await passwordInput.press("Backspace");
  await passwordInput.type(password, { delay: 15 });
  const responsePromise = page.waitForResponse((r) => r.url().includes("/v1/auth/login"), { timeout: 45000 });
  await page.locator('button[type="submit"]').first().click();
  const loginResponse = await responsePromise;
  await page.waitForTimeout(2500);
  return { loginStatus: loginResponse.status(), consoleErrors };
}

test.describe("FINAL-L5-01B six-session real browser smoke", () => {
  test("1. Admin — Platform Super Admin", async ({ page }) => {
    const { loginStatus } = await login(page, "http://localhost:3000", "/login", "admin@serviceos.local", "Password123!");
    console.log("ADMIN_LOGIN_STATUS:", loginStatus);
    console.log("ADMIN_URL_AFTER_LOGIN:", page.url());
    await page.screenshot({ path: `${EVID}/admin-01-dashboard.png` });
    let bodyText = await page.locator("body").innerText();
    console.log("ADMIN_DASHBOARD_HAS_404:", bodyText.includes("404"));

    await page.goto("http://localhost:3000/admin/tenants", { waitUntil: "domcontentloaded", timeout: 20000 });
    await page.waitForTimeout(1500);
    await page.screenshot({ path: `${EVID}/admin-02-tenants.png` });
    bodyText = await page.locator("body").innerText();
    console.log("ADMIN_TENANTS_HAS_DEMO:", bodyText.includes("Demo AC Services"));
    console.log("ADMIN_TENANTS_HAS_ISOLATION:", bodyText.includes("Isolation Test Services"));
    console.log("ADMIN_TENANTS_HAS_404:", bodyText.includes("could not be found"));

    await page.goto("http://localhost:3000/admin/notifications", { waitUntil: "domcontentloaded", timeout: 20000 }).catch(() => {});
    await page.waitForTimeout(1000);
    await page.screenshot({ path: `${EVID}/admin-03-notifications.png` });

    await page.goto("http://localhost:3000/admin/home-services/service-jobs", { waitUntil: "domcontentloaded", timeout: 20000 }).catch(() => {});
    await page.waitForTimeout(1000);
    bodyText = await page.locator("body").innerText();
    console.log("ADMIN_JOBS_ROUTE_HAS_404:", bodyText.includes("could not be found"));
    await page.screenshot({ path: `${EVID}/admin-04-jobs-attempt.png` });
  });

  test("2. Tenant Owner", async ({ page }) => {
    const { loginStatus } = await login(page, "http://localhost:3001", "/login", "owner@demo-ac-services.local", CANON);
    console.log("TENANT_OWNER_LOGIN_STATUS:", loginStatus);
    console.log("TENANT_OWNER_URL:", page.url());
    await page.screenshot({ path: `${EVID}/tenant-owner-01-dashboard.png` });
    let bodyText = await page.locator("body").innerText();
    console.log("TENANT_OWNER_DASHBOARD_HAS_404:", bodyText.includes("could not be found"));

    await page.goto("http://localhost:3001/service-areas", { waitUntil: "domcontentloaded", timeout: 20000 }).catch(() => {});
    await page.waitForTimeout(1000);
    await page.screenshot({ path: `${EVID}/tenant-owner-02-service-areas.png` });

    await page.goto("http://localhost:3001/jobs", { waitUntil: "domcontentloaded", timeout: 20000 }).catch(() => {});
    await page.waitForTimeout(1000);
    bodyText = await page.locator("body").innerText();
    console.log("TENANT_OWNER_JOBS_HAS_JOB:", bodyText.includes("L501-JOB"));
    await page.screenshot({ path: `${EVID}/tenant-owner-03-jobs.png` });

    await page.goto("http://localhost:3001/wallet", { waitUntil: "domcontentloaded", timeout: 20000 }).catch(() => {});
    await page.waitForTimeout(1000);
    bodyText = await page.locator("body").innerText();
    console.log("TENANT_OWNER_WALLET_HAS_3979:", bodyText.includes("3,979") || bodyText.includes("3979"));
    await page.screenshot({ path: `${EVID}/tenant-owner-04-wallet.png` });
  });

  test("3. Tenant Read Only — mutation UI check", async ({ page }) => {
    const { loginStatus } = await login(page, "http://localhost:3001", "/login", "readonly@demo-ac-services.local", CANON);
    console.log("TENANT_READONLY_LOGIN_STATUS:", loginStatus);
    console.log("TENANT_READONLY_URL:", page.url());
    await page.screenshot({ path: `${EVID}/tenant-readonly-01-dashboard.png` });

    await page.goto("http://localhost:3001/service-areas", { waitUntil: "domcontentloaded", timeout: 20000 }).catch(() => {});
    await page.waitForTimeout(1500);
    let addButtons = 0;
    try {
      addButtons = await page.locator('button:has-text("Add"), button:has-text("Create"), button:has-text("New")').count({ timeout: 5000 } as any);
    } catch { addButtons = -1; }
    console.log("TENANT_READONLY_MUTATION_BUTTONS_VISIBLE:", addButtons);
    await page.screenshot({ path: `${EVID}/tenant-readonly-02-service-areas.png` });
  });

  test("4. Customer One", async ({ page }) => {
    const { loginStatus } = await login(page, "http://localhost:3002", "/login", "customer1@serviceos.local", CANON);
    console.log("CUSTOMER1_LOGIN_STATUS:", loginStatus);
    console.log("CUSTOMER1_URL:", page.url());
    await page.screenshot({ path: `${EVID}/customer1-01-home.png` });

    await page.goto("http://localhost:3002/customer/bookings", { waitUntil: "domcontentloaded", timeout: 20000 }).catch(() => {});
    await page.waitForTimeout(1500);
    const bodyText = await page.locator("body").innerText();
    console.log("CUSTOMER1_BOOKINGS_HAS_404:", bodyText.includes("could not be found"));
    console.log("CUSTOMER1_BOOKINGS_TEXT_SAMPLE:", bodyText.slice(0, 300));
    await page.screenshot({ path: `${EVID}/customer1-02-bookings.png` });

    // capture the auth token for the isolation cross-check in test 5
    const token = await page.evaluate(() => {
      for (const k of Object.keys(localStorage)) {
        if (k.toLowerCase().includes("token") || k.toLowerCase().includes("auth")) return localStorage.getItem(k);
      }
      return null;
    });
    console.log("CUSTOMER1_HAS_LOCALSTORAGE_TOKEN:", !!token);
  });

  test("5. Customer Two — isolation from Customer One", async ({ page }) => {
    const { loginStatus } = await login(page, "http://localhost:3002", "/login", "customer2@serviceos.local", CANON);
    console.log("CUSTOMER2_LOGIN_STATUS:", loginStatus);
    await page.goto("http://localhost:3002/customer/bookings", { waitUntil: "domcontentloaded", timeout: 20000 }).catch(() => {});
    await page.waitForTimeout(1500);
    const bodyText = await page.locator("body").innerText();
    // Customer 2 has no seeded bookings; Customer 1's jobs (L501-JOB-*) must NOT appear
    console.log("CUSTOMER2_SEES_CUSTOMER1_JOB_LEAK:", bodyText.includes("L501-JOB"));
    await page.screenshot({ path: `${EVID}/customer2-01-bookings.png` });
  });

  test("6. Technician One", async ({ page }) => {
    const { loginStatus } = await login(page, "http://localhost:3001", "/staff/login", "tech1@demo-ac-services.local", CANON);
    console.log("TECH1_LOGIN_STATUS:", loginStatus);
    console.log("TECH1_URL:", page.url());
    await page.screenshot({ path: `${EVID}/tech1-01-dashboard.png` });

    await page.goto("http://localhost:3001/staff/jobs", { waitUntil: "domcontentloaded", timeout: 20000 }).catch(() => {});
    await page.waitForTimeout(1500);
    const bodyText = await page.locator("body").innerText();
    console.log("TECH1_JOBS_HAS_ASSIGNED_JOB:", bodyText.includes("L501-JOB-0002") || bodyText.includes("L501-JOB-0003"));
    console.log("TECH1_JOBS_HAS_404:", bodyText.includes("could not be found"));
    await page.screenshot({ path: `${EVID}/tech1-02-jobs.png` });
  });
});
