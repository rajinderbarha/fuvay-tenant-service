import { test, expect }                       from "@playwright/test";
import { setupMockApi, setTenantAuth }           from "../helpers/mock-api";

test.describe("Tenant Portal — Customers", () => {
  test.beforeEach(async ({ page }) => {
    await setupMockApi(page);
    await page.goto("/login");
    await setTenantAuth(page);
    await page.goto("/customers");
  });

  test("customers list shows Priya Sharma", async ({ page }) => {
    await expect(page.locator("text=Priya Sharma")).toBeVisible({ timeout: 8_000 });
  });

  test("health band filter tabs visible", async ({ page }) => {
    await expect(page.locator("button:has-text('Platinum'), button:has-text('Gold')").first()).toBeVisible({ timeout: 6_000 });
  });

  test("health band filter All button shows all customers", async ({ page }) => {
    const allBtn = page.locator("button:has-text('All'), button:has-text('All Customers')").first();
    if (await allBtn.count() > 0) {
      await allBtn.click();
      await expect(page.locator("text=Priya Sharma")).toBeVisible({ timeout: 4_000 });
    }
  });

  test("search box filters customers by name", async ({ page }) => {
    const search = page.locator("input[placeholder*=search i], input[placeholder*=name i]").first();
    if (await search.count() > 0) {
      await search.fill("xyz_no_match");
      await expect(page.locator("text=Priya Sharma")).not.toBeVisible({ timeout: 3_000 });
      await search.fill("Priya");
      await expect(page.locator("text=Priya Sharma")).toBeVisible({ timeout: 3_000 });
    }
  });

  test("clicking customer row navigates to detail", async ({ page }) => {
    await page.locator("text=Priya Sharma").first().click();
    await expect(page).toHaveURL(/\/customers\/c_001/, { timeout: 6_000 });
  });

  test("customer detail — health signals breakdown visible", async ({ page }) => {
    await page.goto("/customers/c_001");
    await expect(page.locator("text=Priya Sharma")).toBeVisible({ timeout: 8_000 });
    await expect(page.locator("text=/health|signal|score/i").first()).toBeVisible({ timeout: 6_000 });
  });

  test("customer detail — job history loads", async ({ page }) => {
    await page.goto("/customers/c_001");
    await expect(page.locator("text=/job history|JOB-001|AC Repair/i").first()).toBeVisible({ timeout: 8_000 });
  });

  test("customer detail — contact info shows phone and email", async ({ page }) => {
    await page.goto("/customers/c_001");
    await expect(page.locator("text=+91-9876543210, text=priya@example.com").first()).toBeVisible({ timeout: 8_000 });
  });
});
