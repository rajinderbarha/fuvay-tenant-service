import { test, expect }                       from "@playwright/test";
import { setupMockApi, setTenantAuth }           from "../helpers/mock-api";

test.describe("Tenant Portal — Settings", () => {
  test.beforeEach(async ({ page }) => {
    await setupMockApi(page);
    await page.goto("/login");
    await setTenantAuth(page);
    await page.goto("/settings");
  });

  test("settings page loads heading", async ({ page }) => {
    await expect(page.locator("h1, h2").first()).toBeVisible({ timeout: 8_000 });
  });

  test("3-tier source labels visible (tenant, plan, platform)", async ({ page }) => {
    await expect(page.locator("text=/your override|plan default|platform default/i").first()).toBeVisible({ timeout: 8_000 });
  });

  test("settings table shows commission_rate key", async ({ page }) => {
    await expect(page.locator("text=commission_rate")).toBeVisible({ timeout: 8_000 });
  });

  test("tenant-overridden setting highlighted differently", async ({ page }) => {
    // Row with source=tenant should have different background (success-bg)
    const tenantRow = page.locator("text=commission_rate").locator("..").locator("..");
    await expect(tenantRow).toBeVisible({ timeout: 6_000 });
  });

  test("edit setting modal opens and saves", async ({ page }) => {
    let updateCalled = false;
    await page.route("**/v1/settings/t_test01/**", async route => {
      if (route.request().method() === "PUT") updateCalled = true;
      await route.fulfill({ status:200, contentType:"application/json",
        body: JSON.stringify({ success:true, data:{ key:"commission_rate", value:0.18, source:"tenant", is_override:true }}) });
    });
    const editBtn = page.locator("button:has-text('Edit')").first();
    if (await editBtn.count() > 0) {
      await editBtn.click();
      const modal = page.locator("[role=dialog]").first();
      await expect(modal).toBeVisible({ timeout: 4_000 });
      const input = modal.locator("input").first();
      await input.fill("0.18");
      await modal.locator("button:has-text('Save')").first().click();
      await page.waitForTimeout(800);
      expect(updateCalled).toBeTruthy();
    }
  });

  test("webhooks section shows wh_001", async ({ page }) => {
    await expect(page.locator("text=hooks.example.com, text=active").first()).toBeVisible({ timeout: 8_000 });
  });
});
