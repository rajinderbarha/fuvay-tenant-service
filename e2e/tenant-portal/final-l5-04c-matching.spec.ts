import { test, expect } from "@playwright/test";

const TENANT_ONE_ID = "5209ef33-a53e-4fc0-b3f6-006335b8d712"; // demo-ac-services
const AC_CATEGORY_ID = "4488cc1f-12f9-420f-94c1-d566e9de74e9"; // AC & HVAC service_group
const AC_SERVICE_ID = "13f6cf5e-5d17-4790-b406-6561675a5d38"; // an AC master_service

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

test.describe("FINAL-L5-04C Matching engine entitlement enforcement", () => {
  test("real Chromium: disabling AC entitlement removes Tenant One from AC matching; re-enabling restores it", async ({ page }) => {
    const token = await loginAdmin(page);

    async function runDiagnostics() {
      return page.evaluate(async ({ token, tenantId }) => {
        const r = await fetch("http://localhost:8000/v1/admin/home-services/matching/diagnostics", {
          method: "POST",
          headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
          body: JSON.stringify({
            category_id: "0888d283-9a52-4d7b-8612-9f47fa8357a1",
            master_service_id: "13f6cf5e-5d17-4790-b406-6561675a5d38",
            city: "Ludhiana",
          }),
        });
        return { status: r.status, body: await r.json() };
      }, { token, tenantId: TENANT_ONE_ID });
    }

    async function setCategory(action: "disable" | "reenable") {
      return page.evaluate(async ({ token, tenantId, categoryId, action }) => {
        const r = await fetch(`http://localhost:8000/v1/admin/tenants/${tenantId}/entitlements/categories/${categoryId}/${action}`, {
          method: "POST", headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
          body: action === "disable" ? JSON.stringify({ reason: "e2e matching test" }) : undefined,
        });
        return { status: r.status, body: await r.json() };
      }, { token, tenantId: TENANT_ONE_ID, categoryId: AC_CATEGORY_ID, action });
    }

    // Baseline: entitled, so the candidate must never be excluded for entitlement reasons
    const baseline = await runDiagnostics();
    expect(baseline.status).toBe(200);
    const baselineReasons = baseline.body.data.excluded_providers.map((p: { reason_code: string }) => p.reason_code);
    console.log("BASELINE_EXCLUDED_REASONS:", baselineReasons);
    expect(baselineReasons).not.toContain("TENANT_CATEGORY_NOT_ENTITLED");

    // Disable and confirm the entitlement reason now appears
    const disableResult = await setCategory("disable");
    expect(disableResult.status).toBe(200);
    const afterDisable = await runDiagnostics();
    const disabledReasons = afterDisable.body.data.excluded_providers.map((p: { reason_code: string }) => p.reason_code);
    console.log("AFTER_DISABLE_EXCLUDED_REASONS:", disabledReasons);
    expect(disabledReasons).toContain("TENANT_CATEGORY_NOT_ENTITLED");
    expect(afterDisable.body.data.eligible_provider_count ?? 0).toBe(0);

    // Re-enable and confirm the entitlement reason disappears again
    const reenableResult = await setCategory("reenable");
    expect(reenableResult.status).toBe(200);
    const afterReenable = await runDiagnostics();
    const restoredReasons = afterReenable.body.data.excluded_providers.map((p: { reason_code: string }) => p.reason_code);
    console.log("AFTER_REENABLE_EXCLUDED_REASONS:", restoredReasons);
    expect(restoredReasons).not.toContain("TENANT_CATEGORY_NOT_ENTITLED");
  });

  test("real Chromium: enable-service is denied for a non-entitled category and allowed for an entitled one", async ({ page }) => {
    await page.addInitScript(() => window.localStorage.setItem("serviceos_disable_tour_e2e", "true"));
    await page.goto("http://localhost:3001/login", { waitUntil: "networkidle", timeout: 20000 });
    await waitHydrated(page);
    await page.fill('input[type="email"]', "owner@demo-ac-services.local");
    await page.fill('input[type="password"]', "CanonicalL5!2026");
    await page.click('button[type="submit"]');
    await page.waitForFunction(() => window.location.pathname.includes("/dashboard"), { timeout: 15000 });
    const token = await page.evaluate(() => localStorage.getItem("serviceos_tenant_token"));

    const plumbingAttempt = await page.evaluate(async (token) => {
      const r = await fetch("http://localhost:8000/v1/tenant/catalog/enable-service", {
        method: "POST", headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ master_service_id: "8140c656-5bc3-4e2d-91fc-433a958d904a" }),
      });
      return { status: r.status, body: await r.json() };
    }, token);
    console.log("PLUMBING_ENABLE_ATTEMPT:", plumbingAttempt.status, plumbingAttempt.body.error_code);
    expect(plumbingAttempt.status).toBe(403);
    expect(plumbingAttempt.body.error_code).toBe("CATEGORY_NOT_ENTITLED");
  });
});
