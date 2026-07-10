import { test, expect }                       from "@playwright/test";
import { setupMockApi, clearAuth, setTenantAuth } from "../helpers/mock-api";

test.describe("Tenant Portal — Auth", () => {
  test.beforeEach(async ({ page }) => {
    await setupMockApi(page);
    await clearAuth(page);
  });

  test("unauthenticated root redirects to /login", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveURL(/\/login/);
  });

  test("login page renders email + password + submit", async ({ page }) => {
    await page.goto("/login");
    await expect(page.locator("input[type=email], input[placeholder*=email i]")).toBeVisible();
    await expect(page.locator("input[type=password]")).toBeVisible();
    await expect(page.locator("button[type=submit], button:has-text('Login'), button:has-text('Sign in')")).toBeVisible();
  });

  test("successful login navigates to /dashboard", async ({ page }) => {
    await page.goto("/login");
    await page.locator("input[type=email], input[placeholder*=email i]").fill("owner@rahulac.com");
    await page.locator("input[type=password]").fill("password123");
    await page.locator("button[type=submit], button:has-text('Login'), button:has-text('Sign in')").click();
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 10_000 });
  });

  test("login stores all 6 tenant context keys in localStorage", async ({ page }) => {
    await page.goto("/login");
    await page.locator("input[type=email], input[placeholder*=email i]").fill("owner@rahulac.com");
    await page.locator("input[type=password]").fill("password123");
    await page.locator("button[type=submit], button:has-text('Login'), button:has-text('Sign in')").click();
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 10_000 });
    const keys = await page.evaluate(() => {
      const required = ["serviceos_tenant_token","serviceos_tenant_id","serviceos_tenant_name",
        "serviceos_vertical","serviceos_plan_type","serviceos_user_id"];
      return required.filter(k => !!localStorage.getItem(k));
    });
    expect(keys).toHaveLength(6);
  });

  test("all protected routes redirect to login when unauthenticated", async ({ page }) => {
    for (const path of ["/dashboard", "/jobs", "/bookings", "/staff", "/customers", "/finance", "/reviews"]) {
      await page.goto(path);
      await expect(page).toHaveURL(/\/login/, { timeout: 6_000 });
    }
  });
});
