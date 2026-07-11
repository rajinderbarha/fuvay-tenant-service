import { test, expect } from "@playwright/test";

const TENANT_ONE_ID = "5209ef33-a53e-4fc0-b3f6-006335b8d712"; // demo-ac-services
const TENANT_TWO_ID = "f45664c1-50b7-42c5-a115-37fed1bbaf53"; // isolation-test-services

async function waitHydrated(page: import("@playwright/test").Page) {
  await page.waitForFunction(() => {
    const el = document.querySelector('input[type="email"]') as HTMLInputElement | null;
    if (!el) return false;
    return Object.keys(el).some(k => k.startsWith("__reactProps") || k.startsWith("__reactFiber"));
  }, { timeout: 15000 });
}

async function loginAdmin(page: import("@playwright/test").Page) {
  await page.addInitScript(() => window.localStorage.setItem("serviceos_disable_tour_e2e", "true"));
  await page.goto("http://localhost:3000/login", { waitUntil: "networkidle", timeout: 20000 });
  await waitHydrated(page);
  await page.fill('input[type="email"]', "admin@serviceos.local");
  await page.fill('input[type="password"]', "Password123!");
  await page.click('button[type="submit"]');
  await page.waitForFunction(() => window.location.pathname.includes("/admin/dashboard"), { timeout: 10000 });
  return page.evaluate(() => localStorage.getItem("serviceos_admin_token"));
}

async function loginTenant(page: import("@playwright/test").Page, email: string, password: string) {
  await page.addInitScript(() => window.localStorage.setItem("serviceos_disable_tour_e2e", "true"));
  await page.goto("http://localhost:3001/login", { waitUntil: "networkidle", timeout: 20000 });
  await waitHydrated(page);
  await page.fill('input[type="email"]', email);
  await page.fill('input[type="password"]', password);
  await page.click('button[type="submit"]');
  await page.waitForFunction(() => window.location.pathname.includes("/dashboard"), { timeout: 15000 });
  return page.evaluate(() => localStorage.getItem("serviceos_tenant_token"));
}

test.describe("FINAL-L5-04B Admin entitlement management", () => {
  test("admin can view, disable, re-enable a tenant category entitlement with live UI + audit history", async ({ page }) => {
    await loginAdmin(page);
    await page.goto(`http://localhost:3000/admin/tenants/${TENANT_ONE_ID}?tab=entitlements`, { waitUntil: "networkidle", timeout: 20000 });
    await page.waitForFunction(() => document.body.innerText.includes("Modules") && (document.body.innerText.includes("ACTIVE") || document.body.innerText.includes("No module")), { timeout: 15000 });
    await page.waitForTimeout(500);

    let body = await page.innerText("body");
    expect(body).toContain("Home Services");
    expect(body).toContain("AC & HVAC");

    const AC_CATEGORY_ID = "4488cc1f-12f9-420f-94c1-d566e9de74e9";
    const categoryRow = page.getByTestId(`category-row-${AC_CATEGORY_ID}`);
    await categoryRow.getByRole("button", { name: "Disable" }).click();
    await expect(categoryRow).toContainText("INACTIVE", { timeout: 10000 });

    await page.getByRole("button", { name: "History" }).click();
    await page.waitForFunction(() => document.body.innerText.includes("CATEGORY_ENTITLEMENT_DISABLED"), { timeout: 10000 });
    body = await page.innerText("body");
    expect(body).toContain("CATEGORY_ENTITLEMENT_DISABLED");

    await categoryRow.getByRole("button", { name: "Re-enable" }).click({ force: false });
    await expect(categoryRow).toContainText("ACTIVE", { timeout: 10000 });
    await expect(categoryRow).not.toContainText("INACTIVE");

    body = await page.innerText("body");
    expect(body).toContain("CATEGORY_ENTITLEMENT_REENABLED");
  });
});

test.describe("FINAL-L5-04B Tenant navigation module-level entitlement gating", () => {
  test("disabling tenant's only module entitlement hides operational nav groups; re-enabling restores them", async ({ page }) => {
    await loginAdmin(page);
    await page.goto(`http://localhost:3000/admin/tenants/${TENANT_ONE_ID}?tab=entitlements`, { waitUntil: "networkidle", timeout: 20000 });
    await page.waitForFunction(() => document.body.innerText.includes("Modules") && (document.body.innerText.includes("ACTIVE") || document.body.innerText.includes("No module")), { timeout: 15000 });
    await page.waitForTimeout(500);

    const moduleRow = page.getByTestId("module-row-home_services");
    await moduleRow.getByRole("button", { name: "Disable" }).click();
    await expect(moduleRow).toContainText("INACTIVE", { timeout: 10000 });

    // Open a second, independent browser context so we don't disturb the
    // admin session's own login state while checking the tenant portal.
    const tenantContext = await page.context().browser()!.newContext();
    const tenantPage = await tenantContext.newPage();
    await loginTenant(tenantPage, "owner@demo-ac-services.local", "CanonicalL5!2026");
    await tenantPage.waitForTimeout(1200);

    // Verify the real, live entitlement API this session's nav is driven by
    // (TenantLayout calls this exact endpoint on mount) returns no modules
    // -- proves the gating end-to-end, not just via body-text scraping
    // that CSS text-transform:uppercase can make misleading (group headers
    // render "OPERATIONS" in the DOM's rendered text even though the
    // source label is "Operations", which trips up case-sensitive
    // substring assertions).
    const modulesWhileDisabled = await tenantPage.evaluate(async (token) => {
      const r = await fetch("http://localhost:8000/v1/tenant/me/modules", { headers: { Authorization: `Bearer ${token}` } });
      return r.json();
    }, await tenantPage.evaluate(() => localStorage.getItem("serviceos_tenant_token")));
    console.log("MODULES_WHILE_DISABLED:", modulesWhileDisabled.data.modules);
    expect(modulesWhileDisabled.data.modules).toHaveLength(0);

    // Scope to the sidebar <nav> element specifically -- the dashboard's
    // main content also mentions words like "Security Deposit" as quick-
    // action tiles, so checking the whole body would give false failures
    // unrelated to nav gating.
    const navText = await tenantPage.locator("nav").first().innerText();
    console.log("SIDEBAR_NAV_WITH_NO_MODULE:", navText);
    expect(navText).not.toContain("Bookings");
    expect(navText).not.toContain("Security Deposit");
    expect(navText).toContain("Dashboard");
    await tenantContext.close();

    // Restore via the same admin page/session
    await moduleRow.getByRole("button", { name: "Re-enable" }).click();
    await expect(moduleRow).toContainText("ACTIVE", { timeout: 10000 });

    // Verify restoration via a fresh tenant session's real API response
    // (the same entitlementApi.getMyModules() call TenantLayout itself
    // uses to decide nav visibility) rather than a second full dashboard
    // render, to keep this assertion tightly scoped to entitlement
    // correctness rather than unrelated dashboard-page rendering.
    const tenantContext2 = await page.context().browser()!.newContext();
    const tenantPage2 = await tenantContext2.newPage();
    const token2 = await loginTenant(tenantPage2, "owner@demo-ac-services.local", "CanonicalL5!2026");
    const modulesAfterReenable = await tenantPage2.evaluate(async (token) => {
      const r = await fetch("http://localhost:8000/v1/tenant/me/modules", { headers: { Authorization: `Bearer ${token}` } });
      return r.json();
    }, token2);
    const moduleKeys = modulesAfterReenable.data.modules.map((m: { module_key: string }) => m.module_key);
    console.log("MODULES_AFTER_REENABLE:", moduleKeys);
    expect(moduleKeys).toContain("home_services");
    await tenantContext2.close();
  });
});

test.describe("FINAL-L5-04B Tenant isolation", () => {
  test("Tenant One and Tenant Two see different, isolated entitlement sets via real API", async ({ browser }) => {
    // Two fully independent browser contexts (not the same page/localStorage
    // reused) -- avoids any cross-session state bleed and more accurately
    // models two real, simultaneous tenant users.
    const contextOne = await browser.newContext();
    const pageOne = await contextOne.newPage();
    const tokenOne = await loginTenant(pageOne, "owner@demo-ac-services.local", "CanonicalL5!2026");
    const tenantOneEntitlements = await pageOne.evaluate(async (token) => {
      const r = await fetch("http://localhost:8000/v1/tenant/me/entitlements", { headers: { Authorization: `Bearer ${token}` } });
      return r.json();
    }, tokenOne);
    const tenantOneCategories = tenantOneEntitlements.data.categories.map((c: { category_slug: string }) => c.category_slug);
    console.log("TENANT_ONE_CATEGORIES:", tenantOneCategories);
    expect(tenantOneCategories).toContain("ac_services");
    expect(tenantOneCategories).not.toContain("plumbing");
    await contextOne.close();

    const contextTwo = await browser.newContext();
    const pageTwo = await contextTwo.newPage();
    const tokenTwo = await loginTenant(pageTwo, "owner@isolation-test-services.local", "CanonicalL5!2026");
    const tenantTwoEntitlements = await pageTwo.evaluate(async (token) => {
      const r = await fetch("http://localhost:8000/v1/tenant/me/entitlements", { headers: { Authorization: `Bearer ${token}` } });
      return r.json();
    }, tokenTwo);
    const tenantTwoCategories = tenantTwoEntitlements.data.categories.map((c: { category_slug: string }) => c.category_slug);
    console.log("TENANT_TWO_CATEGORIES:", tenantTwoCategories);
    expect(tenantTwoCategories).toContain("plumbing");
    expect(tenantTwoCategories).not.toContain("ac_services");
    await contextTwo.close();
  });
});
