import { test, expect }                   from "@playwright/test";
import { setupMockApi, setAdminAuth }     from "../helpers/mock-api";

test.describe("Super Admin — Security SOC Overview", () => {
  test.beforeEach(async ({ page }) => {
    await setupMockApi(page);
    await page.goto("/login");
    await setAdminAuth(page);
    await page.goto("/admin/security");
  });

  test("security page loads with 7 tabs", async ({ page }) => {
    await expect(page.locator("text=Security & Threats").first()).toBeVisible({ timeout: 8_000 });
    for (const tab of ["Overview", "Threats", "Active Sessions", "IP Blocklist", "API Keys", "Audit Logs", "Security Policies"]) {
      await expect(page.locator(`button:has-text("${tab}")`).first()).toBeVisible();
    }
  });

  test("overview summary cards render", async ({ page }) => {
    await expect(page.locator("text=Open Threats").first()).toBeVisible({ timeout: 8_000 });
    await expect(page.locator("text=Blocked IPs").first()).toBeVisible();
    await expect(page.locator("text=Active API Keys").first()).toBeVisible();
  });

  test("recent threats panel shows a threat", async ({ page }) => {
    await expect(page.locator("text=Repeated failed logins detected").first()).toBeVisible({ timeout: 8_000 });
  });

  test("threats tab lists threats", async ({ page }) => {
    await page.locator('button:has-text("Threats")').first().click();
    await expect(page.locator("text=THR-abcd1234").first()).toBeVisible({ timeout: 8_000 });
  });

  test("active sessions tab lists sessions", async ({ page }) => {
    await page.locator('button:has-text("Active Sessions")').first().click();
    await expect(page.locator("text=provider@serviceos.in").first()).toBeVisible({ timeout: 8_000 });
  });

  test("audit logs tab shows append-only note", async ({ page }) => {
    await page.locator('button:has-text("Audit Logs")').first().click();
    await expect(page.locator("text=append-only").first()).toBeVisible({ timeout: 8_000 });
  });

  test("security policies tab lists a policy", async ({ page }) => {
    await page.locator('button:has-text("Security Policies")').first().click();
    await expect(page.locator("text=mfa_required_super_admin").first()).toBeVisible({ timeout: 8_000 });
  });
});
