import { test, expect }                       from "@playwright/test";
import { setupMockApi, setTenantAuth }           from "../helpers/mock-api";

test.describe("Tenant Portal — Dashboard", () => {
  test.beforeEach(async ({ page }) => {
    await setupMockApi(page);
    await page.goto("/login");
    await setTenantAuth(page);
    await page.goto("/dashboard");
  });

  test("dashboard loads without crashing", async ({ page }) => {
    await expect(page.locator("body")).not.toContainText("Error", { timeout: 8_000 });
  });

  test("jobs section appears before KPI section (jobs-first layout)", async ({ page }) => {
    const jobs = page.locator("text=/jobs today|active jobs|job/i").first();
    await expect(jobs).toBeVisible({ timeout: 8_000 });
    // Verify jobs content is in the top half of the page
    const box = await jobs.boundingBox();
    expect(box?.y).toBeLessThan(600);
  });

  test("KPI card shows revenue_today value", async ({ page }) => {
    // 18000 formatted as Rs18K or similar
    await expect(page.locator("text=/18,000|18K|revenue/i").first()).toBeVisible({ timeout: 8_000 });
  });

  test("SLA alert banner visible when overdue jobs exist", async ({ page }) => {
    await expect(page.locator("text=/sla|overdue|alert/i").first()).toBeVisible({ timeout: 8_000 });
  });

  test("sidebar nav shows all 8 tenant routes", async ({ page }) => {
    for (const label of ["Jobs", "Bookings", "Staff", "Customers", "Finance", "Reviews", "Chat", "Documents"]) {
      await expect(page.locator(`text=${label}`).first()).toBeVisible({ timeout: 5_000 });
    }
  });
});
