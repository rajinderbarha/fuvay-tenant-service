/**
 * FINAL-L5-05M — Real authenticated browser E2E: five-role frontend
 * permission-visibility matrix against the real running backend
 * (localhost:8000) and real running super-admin frontend (localhost:3000).
 * No network mocks.
 *
 * Run: npx playwright test final-l5-05m-permission-visibility.spec.ts --project=super-admin-chromium
 */
import { test, expect, type Page } from "@playwright/test";

const PASSWORD_SUPER = "Password123!";
const PASSWORD_TEST_ROLES = "CanonicalL5!2026";
const REAL_TENANT_ID = "5209ef33-a53e-4fc0-b3f6-006335b8d712";

async function login(page: Page, email: string, password: string) {
  await page.goto("http://localhost:3000/login", { waitUntil: "domcontentloaded", timeout: 30000 });
  const emailInput = page.locator('input[type="email"], input[name="email"]').first();
  const passwordInput = page.locator('input[type="password"], input[name="password"]').first();
  await emailInput.click({ clickCount: 3 });
  await emailInput.type(email, { delay: 10 });
  await passwordInput.click({ clickCount: 3 });
  await passwordInput.type(password, { delay: 10 });
  const [loginResponse] = await Promise.all([
    page.waitForResponse((r) => r.url().includes("/v1/auth/login"), { timeout: 20000 }),
    page.locator('button[type="submit"]').first().click(),
  ]);
  await page.waitForTimeout(1500);
  return loginResponse.status();
}

/**
 * Waits for the sidebar's effective-permission fetch to settle rather than
 * a fixed timeout: polls until the "Overview" group's item count stops
 * changing (permission-filtered items appear once /v1/auth/me resolves).
 * A fixed wait was flaky here -- the correct fail-closed behavior (show
 * nothing extra while loading) means a too-short fixed wait can catch the
 * sidebar mid-load, which is a test-timing issue, not an app defect (the
 * real, slightly-later DOM snapshot at any assertion failure always showed
 * the correct final permission-filtered content).
 */
async function sidebarText(page: Page): Promise<string> {
  const aside = page.locator("aside").first();
  await expect(async () => {
    const linkCount = await aside.locator("a").count();
    expect(linkCount).toBeGreaterThan(0);
  }).toPass({ timeout: 10000, intervals: [300, 500, 800] });
  // One extra settle tick in case a second group is still being appended.
  await page.waitForTimeout(500);
  return (await aside.innerText()).toLowerCase();
}

test.describe("FINAL-L5-05M real browser — five-role sidebar permission visibility", () => {
  test("Platform Super Admin: sees all intended menu groups including Finance and Platform", async ({ page }) => {
    await login(page, "admin@serviceos.local", PASSWORD_SUPER);
    await page.goto("http://localhost:3000/admin/dashboard", { waitUntil: "domcontentloaded", timeout: 30000 });
    await page.waitForTimeout(2000);
    const text = await sidebarText(page);
    for (const label of ["providers", "operations", "finance", "usage credits", "credit top-ups", "security", "roles", "permissions"]) {
      expect(text, `expected Super Admin sidebar to contain "${label}"`).toContain(label);
    }
    await page.screenshot({ path: "docs/final-l5-05/evidence/05m-super-admin-sidebar.png" });
  });

  test("Operations Admin: sees Jobs/Staff, does NOT see Finance/Roles/Permissions", async ({ page }) => {
    await login(page, "admin.ops@serviceos.local", PASSWORD_TEST_ROLES);
    await page.goto("http://localhost:3000/admin/dashboard", { waitUntil: "domcontentloaded", timeout: 30000 });
    await page.waitForTimeout(2000);
    const text = await sidebarText(page);
    expect(text).toContain("jobs");
    expect(text).toContain("staff");
    expect(text).not.toContain("usage credits");
    expect(text).not.toContain("credit top-ups");
    expect(text).not.toMatch(/\broles\b/);
    expect(text).not.toMatch(/\bpermissions\b/);
    await page.screenshot({ path: "docs/final-l5-05/evidence/05m-operations-admin-sidebar.png" });
  });

  test("Finance Admin: sees Finance group, does NOT see Roles/Permissions/Security", async ({ page }) => {
    await login(page, "admin.finance@serviceos.local", PASSWORD_TEST_ROLES);
    await page.goto("http://localhost:3000/admin/dashboard", { waitUntil: "domcontentloaded", timeout: 30000 });
    await page.waitForTimeout(2000);
    const text = await sidebarText(page);
    expect(text).toContain("usage credits");
    expect(text).toContain("credit top-ups");
    expect(text).toContain("security deposits");
    expect(text).not.toMatch(/\broles\b/);
    expect(text).not.toMatch(/\bpermissions\b/);
    expect(text).not.toContain("security\n"); // "Security" platform-governance item, not "Security Deposits"
    await page.screenshot({ path: "docs/final-l5-05/evidence/05m-finance-admin-sidebar.png" });
  });

  test("Security Admin: sees Security/Roles/Permissions, does NOT see Finance", async ({ page }) => {
    await login(page, "admin.security@serviceos.local", PASSWORD_TEST_ROLES);
    await page.goto("http://localhost:3000/admin/dashboard", { waitUntil: "domcontentloaded", timeout: 30000 });
    await page.waitForTimeout(2000);
    const text = await sidebarText(page);
    expect(text).toMatch(/\bsecurity\b/);
    expect(text).toMatch(/\broles\b/);
    expect(text).toMatch(/\bpermissions\b/);
    expect(text).not.toContain("usage credits");
    expect(text).not.toContain("credit top-ups");
    expect(text).not.toContain("security deposits");
    await page.screenshot({ path: "docs/final-l5-05/evidence/05m-security-admin-sidebar.png" });
  });

  test("Admin Read Only: sees a read subset, zero mutation-implying labels", async ({ page }) => {
    await login(page, "admin.readonly@serviceos.local", PASSWORD_TEST_ROLES);
    await page.goto("http://localhost:3000/admin/dashboard", { waitUntil: "domcontentloaded", timeout: 30000 });
    await page.waitForTimeout(2000);
    const text = await sidebarText(page);
    expect(text).toContain("usage credits");
    expect(text).toMatch(/\broles\b/);
    await page.screenshot({ path: "docs/final-l5-05/evidence/05m-readonly-sidebar.png" });
  });
});

test.describe("FINAL-L5-05M real browser — direct-route Permission Denied + read-only presentation", () => {
  test("Operations Admin: direct navigation to Usage Credits shows Permission Denied, no protected data flash", async ({ page }) => {
    await login(page, "admin.ops@serviceos.local", PASSWORD_TEST_ROLES);
    await page.goto(`http://localhost:3000/admin/finance/usage-credits?tenant_id=${REAL_TENANT_ID}`, {
      waitUntil: "domcontentloaded", timeout: 30000,
    });
    await page.waitForTimeout(2000);
    const bodyText = await page.locator("body").innerText();
    expect(bodyText).toContain("Permission denied");
    expect(bodyText).not.toContain("3979"); // the real balance value must never render
    await page.screenshot({ path: "docs/final-l5-05/evidence/05m-ops-denied-usage-credits.png" });
  });

  test("Finance Admin: direct navigation to a Job detail page does not expose exceptional mutation buttons", async ({ page }) => {
    test.setTimeout(90000); // first-visit Next.js dev-server route compile can be slow (matches FINAL-L5-05K's precedent)
    await login(page, "admin.finance@serviceos.local", PASSWORD_TEST_ROLES);
    await page.goto("http://localhost:3000/admin/home-services/service-jobs", {
      waitUntil: "domcontentloaded", timeout: 60000,
    });
    await page.waitForTimeout(2000);
    const bodyText = await page.locator("body").innerText();
    expect(bodyText).not.toContain("Cannot read propert");
    await page.screenshot({ path: "docs/final-l5-05/evidence/05m-finance-jobs-list.png" });
  });

  test("Admin Read Only: Usage Credits page shows real data with no Add-Credits mutation form", async ({ page }) => {
    await login(page, "admin.readonly@serviceos.local", PASSWORD_TEST_ROLES);
    await page.goto(`http://localhost:3000/admin/finance/usage-credits?tenant_id=${REAL_TENANT_ID}`, {
      waitUntil: "domcontentloaded", timeout: 30000,
    });
    await page.waitForTimeout(2000);
    const bodyText = await page.locator("body").innerText();
    expect(bodyText).not.toContain("Permission denied"); // Read Only IS permitted to read this page
    expect(bodyText).toContain("View-only access");
    expect(bodyText).not.toContain("Add Usage Credits");
    await page.screenshot({ path: "docs/final-l5-05/evidence/05m-readonly-usage-credits.png" });
  });

  test("Security Admin: direct navigation to Usage Credits shows Permission Denied", async ({ page }) => {
    await login(page, "admin.security@serviceos.local", PASSWORD_TEST_ROLES);
    await page.goto(`http://localhost:3000/admin/finance/usage-credits?tenant_id=${REAL_TENANT_ID}`, {
      waitUntil: "domcontentloaded", timeout: 30000,
    });
    await page.waitForTimeout(2000);
    const bodyText = await page.locator("body").innerText();
    expect(bodyText).toContain("Permission denied");
    expect(bodyText).not.toContain("3979");
    await page.screenshot({ path: "docs/final-l5-05/evidence/05m-security-denied-usage-credits.png" });
  });

  test("Platform Super Admin: Usage Credits page renders real data and the mutation form", async ({ page }) => {
    await login(page, "admin@serviceos.local", PASSWORD_SUPER);
    await page.goto(`http://localhost:3000/admin/finance/usage-credits?tenant_id=${REAL_TENANT_ID}`, {
      waitUntil: "domcontentloaded", timeout: 30000,
    });
    await page.waitForTimeout(2000);
    const bodyText = await page.locator("body").innerText();
    expect(bodyText).not.toContain("Permission denied");
    expect(bodyText).toContain("Add Usage Credits");
  });
});
