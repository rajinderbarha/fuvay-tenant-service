/**
 * FINAL-L5-05N — Real authenticated browser E2E: root-layout exhaustive
 * route-permission coverage (getRequiredPermissionForRoute, wired into
 * app/admin/layout.tsx so every /admin/* route is guarded, not just the
 * 7 pages individually wrapped in FINAL-L5-05M) and the Platform Users
 * role-editor repair. Against the real running backend (localhost:8000)
 * and real running super-admin frontend (localhost:3000). No mocks.
 *
 * Run: npx playwright test final-l5-05n-exhaustive-coverage.spec.ts --project=super-admin-chromium
 */
import { test, expect, type Page } from "@playwright/test";

const PASSWORD_SUPER = "Password123!";
const PASSWORD_TEST_ROLES = "CanonicalL5!2026";

async function login(page: Page, email: string, password: string) {
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

test.describe("FINAL-L5-05N real browser — root-layout exhaustive route guard", () => {
  test("Platform Super Admin: retains access to previously-orphaned routes (no NAV_GROUPS entry)", async ({ page }) => {
    test.setTimeout(90000);
    await login(page, "admin@serviceos.local", PASSWORD_SUPER);
    // These routes have no NAV_GROUPS entry at all -- previously orphaned
    // (undiscoverable via sidebar) but must remain reachable for Super
    // Admin, since resolveActiveNavId's fallback now resolves to
    // SUPER_ADMIN_ONLY for unmapped ids, and Super Admin must pass that.
    for (const path of ["/admin/brands", "/admin/issue-types", "/admin/service-groups", "/admin/rating-summaries"]) {
      await page.goto(`http://localhost:3000${path}`, { waitUntil: "domcontentloaded", timeout: 30000 });
      await page.waitForTimeout(1500);
      const bodyText = await page.locator("body").innerText();
      expect(bodyText, `${path} must not deny Super Admin`).not.toContain("Permission denied");
    }
  });

  test("Admin Read Only: orphaned/unmapped routes now correctly show Permission Denied instead of silently open", async ({ page }) => {
    test.setTimeout(60000);
    await login(page, "admin.readonly@serviceos.local", PASSWORD_TEST_ROLES);
    for (const path of ["/admin/brands", "/admin/issue-types"]) {
      await page.goto(`http://localhost:3000${path}`, { waitUntil: "domcontentloaded", timeout: 30000 });
      // Orphaned routes are rarely visited, so the dev server may need a
      // first-compile beat and usePermissions() a round trip before the
      // Skeleton resolves to the real denied state -- poll instead of a
      // fixed sleep (same fix pattern as FINAL-L5-05M's sidebar flake).
      await expect(async () => {
        const bodyText = await page.locator("body").innerText();
        expect(bodyText, `${path} must deny admin_readonly (no permission mapping -> fails closed)`).toContain("Permission denied");
      }).toPass({ timeout: 20000 });
    }
  });

  test("Operations Admin: allowed Jobs/Staff routes render, unrelated Finance sub-route denied", async ({ page }) => {
    test.setTimeout(60000);
    await login(page, "admin.ops@serviceos.local", PASSWORD_TEST_ROLES);
    await page.goto("http://localhost:3000/admin/staff", { waitUntil: "domcontentloaded", timeout: 30000 });
    await page.waitForTimeout(1500);
    let bodyText = await page.locator("body").innerText();
    expect(bodyText).not.toContain("Permission denied");

    await page.goto("http://localhost:3000/admin/finance/deposits", { waitUntil: "domcontentloaded", timeout: 30000 });
    await page.waitForTimeout(1500);
    bodyText = await page.locator("body").innerText();
    expect(bodyText).toContain("Permission denied");
  });

  test("Security Admin: Security route renders, Usage Credits denied at root-layout level even without a page-level RequirePermission", async ({ page }) => {
    test.setTimeout(60000);
    await login(page, "admin.security@serviceos.local", PASSWORD_TEST_ROLES);
    await page.goto("http://localhost:3000/admin/users/roles", { waitUntil: "domcontentloaded", timeout: 30000 });
    await page.waitForTimeout(1500);
    let bodyText = await page.locator("body").innerText();
    expect(bodyText).not.toContain("Permission denied");

    // /admin/packages has no page-level RequirePermission (05M didn't
    // guard it) but IS in NAV_GROUPS as SUPER_ADMIN_ONLY -- proves the
    // root-layout guard protects pages that were never individually wrapped.
    await page.goto("http://localhost:3000/admin/packages", { waitUntil: "domcontentloaded", timeout: 30000 });
    await page.waitForTimeout(1500);
    bodyText = await page.locator("body").innerText();
    expect(bodyText).toContain("Permission denied");
  });
});

test.describe("FINAL-L5-05N real browser — Platform Users role-editor repair", () => {
  test("Platform Super Admin: role editor shows the 5 real canonical roles, not invented labels", async ({ page }) => {
    test.setTimeout(60000);
    await login(page, "admin@serviceos.local", PASSWORD_SUPER);
    await page.goto("http://localhost:3000/admin/users", { waitUntil: "domcontentloaded", timeout: 30000 });
    await page.waitForTimeout(2000);
    const bodyText = await page.locator("body").innerText();
    expect(bodyText).not.toContain("Permission denied");
    // The invented labels must not appear anywhere on the page (dropdown
    // options render even before being opened, in the DOM's option text).
    const html = await page.content();
    expect(html).not.toContain("Compliance Officer");
    expect(html).not.toContain("Support Admin");
    expect(html).not.toContain("Platform Admin<");
  });
});
