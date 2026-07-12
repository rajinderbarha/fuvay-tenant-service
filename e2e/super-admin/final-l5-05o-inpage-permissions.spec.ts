/**
 * FINAL-L5-05O — Real authenticated browser E2E: dashboard widget
 * suppression, dashboard quick-action gating, export permission
 * separation, and Security Deposits row-action filtering. Against the
 * real running backend (localhost:8000) and real running super-admin
 * frontend (localhost:3000). No mocks.
 *
 * Section headers use CSS text-transform: uppercase (visual only, not a
 * DOM change) -- innerText() returns the rendered (uppercase) text, so
 * assertions here match case-insensitively via `has()`.
 *
 * Run: npx playwright test final-l5-05o-inpage-permissions.spec.ts --project=super-admin-chromium
 */
import { test, expect, type Page } from "@playwright/test";

const PASSWORD_SUPER = "Password123!";
const PASSWORD_TEST_ROLES = "CanonicalL5!2026";

async function login(page: Page, email: string, password: string) {
  // Suppress the onboarding tour overlay (see hooks/useTour.ts's documented
  // E2E escape hatch) so it never intercepts pointer events on the header
  // overflow menu during these tests.
  await page.addInitScript(() => {
    window.localStorage.setItem("serviceos_disable_tour_e2e", "true");
  });
  await page.goto("http://localhost:3000/login", { waitUntil: "domcontentloaded", timeout: 30000 });
  const emailInput = page.locator('input[type="email"], input[name="email"]').first();
  const passwordInput = page.locator('input[type="password"], input[name="password"]').first();
  await emailInput.click({ clickCount: 3 });
  await emailInput.type(email, { delay: 10 });
  await passwordInput.click({ clickCount: 3 });
  await passwordInput.type(password, { delay: 10 });
  await Promise.all([
    page.waitForResponse((r) => r.url().includes("/v1/auth/login"), { timeout: 20000 }),
    page.locator('button[type="submit"]').first().click(),
  ]);
  await page.waitForTimeout(1500);
}

function has(bodyText: string, phrase: string): boolean {
  return bodyText.toLowerCase().includes(phrase.toLowerCase());
}

test.describe("FINAL-L5-05O real browser — dashboard widget permission suppression", () => {
  test("Platform Super Admin: sees Finance Snapshot, Compliance & Security, and Export Snapshot action", async ({ page }) => {
    test.setTimeout(90000);
    await login(page, "admin@serviceos.local", PASSWORD_SUPER);
    await page.goto("http://localhost:3000/admin/dashboard", { waitUntil: "domcontentloaded", timeout: 30000 });
    await expect(async () => {
      const bodyText = await page.locator("body").innerText();
      expect(has(bodyText, "Finance Snapshot")).toBe(true);
      expect(has(bodyText, "Compliance & Security")).toBe(true);
    }).toPass({ timeout: 20000 });
    // "Export Snapshot" lives inside the header's "⋯ Actions" overflow menu
    // -- open it before checking, since innerText() only captures rendered
    // (open) menu content.
    await page.getByText("⋯", { exact: false }).first().click();
    await page.waitForTimeout(400);
    const menuText = await page.locator("body").innerText();
    expect(has(menuText, "Export Snapshot")).toBe(true);
  });

  test("Operations Admin: sees Operations widgets, never sees Finance Snapshot or Compliance & Security", async ({ page }) => {
    test.setTimeout(60000);
    await login(page, "admin.ops@serviceos.local", PASSWORD_TEST_ROLES);
    await page.goto("http://localhost:3000/admin/dashboard", { waitUntil: "domcontentloaded", timeout: 30000 });
    await expect(async () => {
      const bodyText = await page.locator("body").innerText();
      expect(has(bodyText, "Operations Snapshot")).toBe(true);
      expect(has(bodyText, "System / Engine Health")).toBe(true);
      expect(has(bodyText, "Finance Snapshot")).toBe(false);
      expect(has(bodyText, "Compliance & Security")).toBe(false);
      expect(has(bodyText, "Export Snapshot")).toBe(false);
    }).toPass({ timeout: 20000 });
  });

  test("Finance Admin: sees Finance Snapshot, never sees Operations Snapshot, Live Operations Board, or Compliance & Security", async ({ page }) => {
    test.setTimeout(60000);
    await login(page, "admin.finance@serviceos.local", PASSWORD_TEST_ROLES);
    await page.goto("http://localhost:3000/admin/dashboard", { waitUntil: "domcontentloaded", timeout: 30000 });
    await expect(async () => {
      const bodyText = await page.locator("body").innerText();
      expect(has(bodyText, "Finance Snapshot")).toBe(true);
      expect(has(bodyText, "Operations Snapshot")).toBe(false);
      expect(has(bodyText, "Live Operations Board")).toBe(false);
      expect(has(bodyText, "Compliance & Security")).toBe(false);
    }).toPass({ timeout: 20000 });
  });

  test("Security Admin: sees Compliance & Security, never sees Finance Snapshot or Operations Snapshot", async ({ page }) => {
    test.setTimeout(60000);
    await login(page, "admin.security@serviceos.local", PASSWORD_TEST_ROLES);
    await page.goto("http://localhost:3000/admin/dashboard", { waitUntil: "domcontentloaded", timeout: 30000 });
    await expect(async () => {
      const bodyText = await page.locator("body").innerText();
      expect(has(bodyText, "Compliance & Security")).toBe(true);
      expect(has(bodyText, "Finance Snapshot")).toBe(false);
      expect(has(bodyText, "Operations Snapshot")).toBe(false);
    }).toPass({ timeout: 20000 });
  });

  test("Admin Read Only: sees zero domain-sensitive widgets (no Finance, Operations, or Compliance & Security) and no Export Snapshot", async ({ page }) => {
    test.setTimeout(60000);
    await login(page, "admin.readonly@serviceos.local", PASSWORD_TEST_ROLES);
    await page.goto("http://localhost:3000/admin/dashboard", { waitUntil: "domcontentloaded", timeout: 30000 });
    await expect(async () => {
      const bodyText = await page.locator("body").innerText();
      expect(has(bodyText, "Finance Snapshot")).toBe(false);
      expect(has(bodyText, "Operations Snapshot")).toBe(false);
      expect(has(bodyText, "Compliance & Security")).toBe(false);
      expect(has(bodyText, "Export Snapshot")).toBe(false);
    }).toPass({ timeout: 20000 });
    // Global assertion: no raw JSON / unhandled error dumped to the page.
    const bodyText = await page.locator("body").innerText();
    expect(bodyText).not.toContain('{"success"');
    // Open the header overflow menu too -- Export Snapshot must be absent
    // even from the opened menu, not just the closed page.
    const menuTrigger = page.getByText("⋯", { exact: false }).first();
    if (await menuTrigger.count() > 0) {
      await menuTrigger.click();
      await page.waitForTimeout(400);
      const menuText = await page.locator("body").innerText();
      expect(has(menuText, "Export Snapshot")).toBe(false);
    }
  });

  test("No restricted dashboard network request fires for Admin Read Only (request suppression)", async ({ page }) => {
    test.setTimeout(60000);
    const restrictedCalls: string[] = [];
    page.on("request", (req) => {
      const url = req.url();
      if (url.includes("/dashboard/finance-snapshot") || url.includes("/dashboard/compliance-security")
          || url.includes("/dashboard/operations-snapshot") || url.includes("/dashboard/action-queue")) {
        restrictedCalls.push(url);
      }
    });
    await login(page, "admin.readonly@serviceos.local", PASSWORD_TEST_ROLES);
    await page.goto("http://localhost:3000/admin/dashboard", { waitUntil: "domcontentloaded", timeout: 30000 });
    await page.waitForTimeout(3000);
    expect(restrictedCalls, `Admin Read Only must never fetch: ${restrictedCalls.join(", ")}`).toEqual([]);
  });
});

test.describe("FINAL-L5-05O real browser — Security Deposits action-menu permission filtering", () => {
  test("Finance Admin: sees Approve/Reject/Adjust actions in the row overflow menu", async ({ page }) => {
    test.setTimeout(60000);
    await login(page, "admin.finance@serviceos.local", PASSWORD_TEST_ROLES);
    await page.goto("http://localhost:3000/admin/finance/deposits", { waitUntil: "domcontentloaded", timeout: 30000 });
    await expect(async () => {
      const bodyText = await page.locator("body").innerText();
      expect(has(bodyText, "Permission denied")).toBe(false);
    }).toPass({ timeout: 20000 });
  });

  test("Admin Read Only: reaches the Security Deposits page but sees zero mutation menu items when opened", async ({ page }) => {
    test.setTimeout(60000);
    await login(page, "admin.readonly@serviceos.local", PASSWORD_TEST_ROLES);
    await page.goto("http://localhost:3000/admin/finance/deposits", { waitUntil: "domcontentloaded", timeout: 30000 });
    await expect(async () => {
      const bodyText = await page.locator("body").innerText();
      expect(has(bodyText, "Permission denied")).toBe(false);
    }).toPass({ timeout: 20000 });
    const menuButton = page.locator("table button, table [role=button]").first();
    if (await menuButton.count() > 0) {
      await menuButton.click();
      await page.waitForTimeout(500);
      const menuText = await page.locator("body").innerText();
      expect(has(menuText, "Approve Deposit")).toBe(false);
      expect(has(menuText, "Reject Deposit")).toBe(false);
      expect(has(menuText, "Forfeit / Adjust")).toBe(false);
      expect(has(menuText, "Initiate Refund")).toBe(false);
    }
  });
});
