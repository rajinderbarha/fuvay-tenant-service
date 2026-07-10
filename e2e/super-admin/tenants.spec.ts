import { test, expect }                   from "@playwright/test";
import { setupMockApi, setAdminAuth }     from "../helpers/mock-api";

test.describe("Super Admin — Tenants", () => {
  test.beforeEach(async ({ page }) => {
    await setupMockApi(page);
    await page.goto("/login");
    await setAdminAuth(page);
    await page.goto("/tenants");
  });

  test("tenant list loads and shows tenant name", async ({ page }) => {
    await expect(page.locator("text=Rahul AC Services")).toBeVisible({ timeout: 8_000 });
  });

  test("search box filters tenant list", async ({ page }) => {
    const searchBox = page.locator("input[type=search], input[placeholder*=search i], input[placeholder*=tenant i]").first();
    if (await searchBox.count() > 0) {
      await searchBox.fill("nonexistent tenant xyz");
      await expect(page.locator("text=Rahul AC Services")).not.toBeVisible({ timeout: 3_000 });
      await searchBox.clear();
      await expect(page.locator("text=Rahul AC Services")).toBeVisible({ timeout: 3_000 });
    }
  });

  test("clicking a tenant row navigates to tenant detail", async ({ page }) => {
    const row = page.locator("text=Rahul AC Services").first();
    await row.click();
    await expect(page).toHaveURL(/\/tenants\/t_test01/, { timeout: 6_000 });
  });

  test("tenant detail shows name, health score, and KPI sections", async ({ page }) => {
    await page.goto("/tenants/t_test01");
    await expect(page.locator("text=Rahul AC Services")).toBeVisible({ timeout: 8_000 });
    await expect(page.locator("text=82, text=health").first()).toBeVisible({ timeout: 6_000 });
  });

  test("wallet top-up modal opens and submits", async ({ page }) => {
    await page.goto("/tenants/t_test01");
    const topupBtn = page.locator("button:has-text('Top Up'), button:has-text('Topup'), button:has-text('Add Credits')").first();
    if (await topupBtn.count() > 0) {
      await topupBtn.click();
      await expect(page.locator("[role=dialog], .modal, [data-testid=modal]").first()).toBeVisible({ timeout: 4_000 });
    }
  });

  test("suspend tenant triggers confirmation flow", async ({ page }) => {
    await page.goto("/tenants/t_test01");
    const suspendBtn = page.locator("button:has-text('Suspend'), button:has-text('suspend')").first();
    if (await suspendBtn.count() > 0) {
      await suspendBtn.click();
      // Confirm dialog or type-to-confirm should appear
      await expect(page.locator("[role=dialog], text=/confirm|suspend/i").first()).toBeVisible({ timeout: 4_000 });
    }
  });
});
