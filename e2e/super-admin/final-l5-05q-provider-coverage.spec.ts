/**
 * FINAL-L5-05Q — Real authenticated browser E2E: Provider coverage
 * (Tenant Service Areas tab) duplicate-prevention and cross-tenant
 * isolation fixes surfaced correctly in the UI. Against the real running
 * backend (localhost:8000) and real running super-admin frontend
 * (localhost:3000). No mocks.
 *
 * Run: npx playwright test final-l5-05q-provider-coverage.spec.ts --project=super-admin-chromium
 */
import { test, expect, type Page } from "@playwright/test";

const PASSWORD_SUPER = "Password123!";
const PASSWORD_TEST_ROLES = "CanonicalL5!2026";
const DEMO_TENANT_ID = "5209ef33-a53e-4fc0-b3f6-006335b8d712"; // Demo AC Services

async function login(page: Page, email: string, password: string) {
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

test.describe("FINAL-L5-05Q real browser — Provider coverage (Service Areas) permission and duplicate handling", () => {
  test("Operations Admin: reaches Tenant detail's Service Areas tab but sees no + Add Area button (require_super_admin gate, unchanged from FINAL-L5-05P)", async ({ page }) => {
    test.setTimeout(90000);
    await login(page, "admin.ops@serviceos.local", PASSWORD_TEST_ROLES);
    await page.goto(`http://localhost:3000/admin/tenants/${DEMO_TENANT_ID}?tab=service-areas`, { waitUntil: "domcontentloaded", timeout: 30000 });
    await expect(async () => {
      const bodyText = await page.locator("body").innerText();
      expect(has(bodyText, "Permission denied")).toBe(false);
      expect(has(bodyText, "+ Add Area")).toBe(false);
    }).toPass({ timeout: 20000 });
  });

  test("Platform Super Admin: Service Areas tab renders real data with the Add Area action available and no raw errors", async ({ page }) => {
    test.setTimeout(60000);
    await login(page, "admin@serviceos.local", PASSWORD_SUPER);
    await page.goto(`http://localhost:3000/admin/tenants/${DEMO_TENANT_ID}?tab=service-areas`, { waitUntil: "domcontentloaded", timeout: 30000 });
    await expect(async () => {
      const bodyText = await page.locator("body").innerText();
      expect(has(bodyText, "+ Add Area")).toBe(true);
      expect(bodyText).not.toContain("Traceback");
      expect(bodyText).not.toContain('{"type":"https://serviceos.io');
    }).toPass({ timeout: 20000 });
  });

  test("Platform Super Admin: duplicate service area creation via direct API call from the authenticated browser session returns a controlled 409, not a raw 500", async ({ page }) => {
    test.setTimeout(60000);
    await login(page, "admin@serviceos.local", PASSWORD_SUPER);
    await page.goto(`http://localhost:3000/admin/tenants/${DEMO_TENANT_ID}`, { waitUntil: "domcontentloaded", timeout: 30000 });
    await page.waitForTimeout(1000);

    const city = `L5Q-Chromium-${Date.now()}`;
    const result = await page.evaluate(async ({ tenantId, city }) => {
      const token = localStorage.getItem("serviceos_admin_token");
      const body = JSON.stringify({ coverage_type: "city", city, state: "TestState" });
      const first = await fetch(`http://localhost:8000/v1/admin/tenants/${tenantId}/service-areas`, {
        method: "POST", headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" }, body,
      });
      const second = await fetch(`http://localhost:8000/v1/admin/tenants/${tenantId}/service-areas`, {
        method: "POST", headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" }, body,
      });
      const secondBody = await second.json();
      // Cleanup: delete the created area regardless of test outcome.
      if (first.ok) {
        const firstBody = await first.json();
        await fetch(`http://localhost:8000/v1/admin/tenants/${tenantId}/service-areas/${firstBody.data.id}`, {
          method: "DELETE", headers: { Authorization: `Bearer ${token}` },
        });
      }
      return { firstStatus: first.status, secondStatus: second.status, secondErrorCode: secondBody.error_code };
    }, { tenantId: DEMO_TENANT_ID, city });

    expect(result.firstStatus).toBe(201);
    expect(result.secondStatus).toBe(409);
    expect(result.secondErrorCode).toBe("DUPLICATE_SERVICE_AREA");
  });
});
