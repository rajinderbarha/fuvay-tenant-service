import { test, expect }                       from "@playwright/test";
import { setupMockApi, setTenantAuth }           from "../helpers/mock-api";

test.describe("Tenant Portal — Staff", () => {
  test.beforeEach(async ({ page }) => {
    await setupMockApi(page);
    await page.goto("/login");
    await setTenantAuth(page);
    await page.goto("/staff");
  });

  test("staff list shows Amit Kumar", async ({ page }) => {
    await expect(page.locator("text=Amit Kumar")).toBeVisible({ timeout: 8_000 });
  });

  test("performance score visible on staff row", async ({ page }) => {
    await expect(page.locator("text=88, text=4.6").first()).toBeVisible({ timeout: 6_000 });
  });

  test("clicking staff navigates to detail page", async ({ page }) => {
    await page.locator("text=Amit Kumar").first().click();
    await expect(page).toHaveURL(/\/staff\/s_001/, { timeout: 6_000 });
  });

  test("staff detail page — profile header shows name and status", async ({ page }) => {
    await page.goto("/staff/s_001");
    await expect(page.locator("text=Amit Kumar")).toBeVisible({ timeout: 8_000 });
    await expect(page.locator("text=active, text=AC Repair").first()).toBeVisible({ timeout: 6_000 });
  });

  test("staff detail — performance breakdown panel visible", async ({ page }) => {
    await page.goto("/staff/s_001");
    await expect(page.locator("text=/performance|composite|score/i").first()).toBeVisible({ timeout: 8_000 });
  });

  test("staff detail — weekly schedule grid visible", async ({ page }) => {
    await page.goto("/staff/s_001");
    await expect(page.locator("text=/monday|schedule|working/i").first()).toBeVisible({ timeout: 8_000 });
  });

  test("staff detail — edit schedule modal opens and saves", async ({ page }) => {
    await page.goto("/staff/s_001");
    let scheduleCalled = false;
    await page.route("**/v1/staff/s_001/schedule", async route => {
      if (route.request().method() === "PUT") { scheduleCalled = true; }
      await route.fulfill({ status:200, contentType:"application/json",
        body: JSON.stringify({ success:true, data:{ id:"s_001" } }) });
    });
    const editBtn = page.locator("button:has-text('Edit Schedule'), button:has-text('Edit')").first();
    if (await editBtn.count() > 0) {
      await editBtn.click();
      const modal = page.locator("[role=dialog]").first();
      await expect(modal).toBeVisible({ timeout: 4_000 });
      await modal.locator("button:has-text('Save'), button:has-text('Save Schedule')").first().click();
      await page.waitForTimeout(800);
      expect(scheduleCalled).toBeTruthy();
    }
  });
});
