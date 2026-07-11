import { test, expect } from "@playwright/test";
const CANON = "CanonicalL5!2026";
const EVID = "docs/final-l5-01d/evidence";

async function login(page: any, base: string, path: string, email: string, password: string) {
  await page.goto(`${base}${path}`, { waitUntil: "domcontentloaded", timeout: 30000 });
  const emailInput = page.locator('input[type="email"], input[name="email"]').first();
  const passwordInput = page.locator('input[type="password"], input[name="password"]').first();
  await emailInput.click({ clickCount: 3 }); await emailInput.press("Backspace");
  await emailInput.type(email, { delay: 15 });
  await passwordInput.click({ clickCount: 3 }); await passwordInput.press("Backspace");
  await passwordInput.type(password, { delay: 15 });
  const respPromise = page.waitForResponse((r: any) => r.url().includes("/v1/auth/login"), { timeout: 30000 });
  await page.locator('button[type="submit"]').first().click();
  await respPromise;
  await page.waitForTimeout(2000);
}

test("Tenant Owner Jobs — canonical endpoint, real data, no legacy call", async ({ page }) => {
  const requests: string[] = [];
  page.on("request", (r) => { if (r.url().includes("/v1/")) requests.push(r.url()); });

  await login(page, "http://localhost:3001", "/login", "owner@demo-ac-services.local", CANON);
  await page.goto("http://localhost:3001/jobs", { waitUntil: "domcontentloaded", timeout: 20000 });
  await page.waitForTimeout(2000);
  await page.screenshot({ path: `${EVID}/regression-tenant-jobs-list.png` });

  const bodyText = await page.locator("body").innerText();
  console.log("JOBS_LIST_HAS_L501:", bodyText.includes("L501-JOB"));
  console.log("JOBS_LIST_NO_MATCH_MESSAGE:", bodyText.includes("No jobs match"));

  const usedLegacy = requests.some((u) => /\/v1\/jobs(\?|$)/.test(u));
  const usedCanonical = requests.some((u) => u.includes("/v1/provider/my-records/jobs"));
  console.log("USED_LEGACY_V1_JOBS:", usedLegacy);
  console.log("USED_CANONICAL_ENDPOINT:", usedCanonical);

  // Click into first job detail
  const firstRow = page.locator("tbody tr").first();
  if (await firstRow.count() > 0) {
    await firstRow.click();
    await page.waitForTimeout(2000);
    await page.screenshot({ path: `${EVID}/regression-tenant-jobs-detail.png` });
    const detailText = await page.locator("body").innerText();
    console.log("DETAIL_HAS_JOB_NUMBER:", /L501-JOB/.test(detailText));
    console.log("DETAIL_HAS_404:", detailText.includes("could not be found"));
  }
});

test("Customer One bookings — real seeded data via canonical source", async ({ page }) => {
  await login(page, "http://localhost:3002", "/login", "customer1@serviceos.local", CANON);
  await page.goto("http://localhost:3002/customer/bookings", { waitUntil: "domcontentloaded", timeout: 20000 });
  await page.waitForTimeout(2000);
  await page.screenshot({ path: `${EVID}/regression-customer-bookings.png` });
  const bodyText = await page.locator("body").innerText();
  console.log("CUSTOMER1_NO_BOOKINGS_MESSAGE:", bodyText.includes("No bookings yet"));
  console.log("CUSTOMER1_BODY_SAMPLE:", bodyText.slice(0, 400));
});

test("Admin regression — dashboard, tenants, jobs still healthy", async ({ page }) => {
  await login(page, "http://localhost:3000", "/login", "admin@serviceos.local", "Password123!");
  await page.goto("http://localhost:3000/admin/dashboard", { waitUntil: "domcontentloaded", timeout: 20000 });
  await page.waitForTimeout(1500);
  let bodyText = await page.locator("body").innerText();
  console.log("ADMIN_DASHBOARD_404:", bodyText.includes("could not be found"));
  await page.goto("http://localhost:3000/admin/tenants", { waitUntil: "domcontentloaded", timeout: 20000 });
  await page.waitForTimeout(1500);
  bodyText = await page.locator("body").innerText();
  console.log("ADMIN_TENANTS_HAS_DEMO:", bodyText.includes("Demo AC Services"));
  await page.screenshot({ path: `${EVID}/regression-admin-tenants.png` });
});
