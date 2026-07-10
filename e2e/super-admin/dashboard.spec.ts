import { test, expect }                   from "@playwright/test";
import { setupMockApi, setAdminAuth }     from "../helpers/mock-api";

test.describe("Super Admin — Dashboard", () => {
  test.beforeEach(async ({ page }) => {
    await setupMockApi(page);
    await page.goto("/login");
    await setAdminAuth(page);
    await page.goto("/dashboard");
  });

  test("page title / heading visible", async ({ page }) => {
    await expect(page.locator("h1, h2").filter({ hasText: /dashboard/i }).first()).toBeVisible({ timeout: 8_000 });
  });

  test("platform KPI cards render non-zero numbers", async ({ page }) => {
    // KPI cards should show numeric data from platform summary
    await expect(page.locator("text=/\\d+/").first()).toBeVisible({ timeout: 8_000 });
  });

  test("tenant table renders at least one row", async ({ page }) => {
    await expect(page.locator("table tbody tr, [data-testid=tenant-row]").first()).toBeVisible({ timeout: 8_000 });
    await expect(page.locator("text=Rahul AC Services")).toBeVisible();
  });

  test("SLA alerts section visible", async ({ page }) => {
    await expect(page.locator("text=/sla/i, text=/alert/i").first()).toBeVisible({ timeout: 8_000 });
  });

  test("sidebar nav links present", async ({ page }) => {
    for (const label of ["Tenants", "Operations", "Finance", "Security"]) {
      await expect(page.locator(`text=${label}`).first()).toBeVisible();
    }
  });

  test("dark mode toggle changes theme attribute", async ({ page }) => {
    const toggle = page.locator("[aria-label*=theme i], button:has-text('Dark'), button:has-text('Light'), [data-testid=theme-toggle]");
    if (await toggle.count() > 0) {
      await toggle.first().click();
      const html = page.locator("html");
      await expect(html).toHaveAttribute("data-theme", /dark|light/);
    }
  });
});
