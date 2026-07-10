import { test, expect }                   from "@playwright/test";
import { setupMockApi, clearAuth }         from "../helpers/mock-api";

test.describe("Super Admin — Auth", () => {
  test.beforeEach(async ({ page }) => {
    await setupMockApi(page);
    await page.goto("/");
    await clearAuth(page);
  });

  test("unauthenticated root redirects to /login", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveURL(/\/login/);
  });

  test("login page renders email + password fields and submit button", async ({ page }) => {
    await page.goto("/login");
    await expect(page.locator("input[type=email], input[placeholder*=email i]")).toBeVisible();
    await expect(page.locator("input[type=password]")).toBeVisible();
    await expect(page.locator("button[type=submit], button:has-text('Login'), button:has-text('Sign in')")).toBeVisible();
  });

  test("successful login navigates to /dashboard", async ({ page }) => {
    await page.goto("/login");
    await page.locator("input[type=email], input[placeholder*=email i]").fill("admin@serviceos.com");
    await page.locator("input[type=password]").fill("password123");
    await page.locator("button[type=submit], button:has-text('Login'), button:has-text('Sign in')").click();
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 10_000 });
  });

  test("login stores token in localStorage", async ({ page }) => {
    await page.goto("/login");
    await page.locator("input[type=email], input[placeholder*=email i]").fill("admin@serviceos.com");
    await page.locator("input[type=password]").fill("password123");
    await page.locator("button[type=submit], button:has-text('Login'), button:has-text('Sign in')").click();
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 10_000 });
    const token = await page.evaluate(() => localStorage.getItem("serviceos_admin_token"));
    expect(token).toBeTruthy();
  });

  test("wrong credentials shows error message", async ({ page }) => {
    await page.route("**/v1/auth/login", route =>
      route.fulfill({ status:401, contentType:"application/json",
        body: JSON.stringify({ error_code:"INVALID_CREDENTIALS", message:"Invalid email or password." }) })
    );
    await page.goto("/login");
    await page.locator("input[type=email], input[placeholder*=email i]").fill("wrong@example.com");
    await page.locator("input[type=password]").fill("badpass");
    await page.locator("button[type=submit], button:has-text('Login'), button:has-text('Sign in')").click();
    await expect(page.locator("text=Invalid email or password., text=error, [role=alert]").first()).toBeVisible({ timeout: 6_000 });
  });

  test("protected pages redirect to login when unauthenticated", async ({ page }) => {
    for (const path of ["/dashboard", "/tenants", "/operations", "/finance"]) {
      await page.goto(path);
      await expect(page).toHaveURL(/\/login/, { timeout: 6_000 });
    }
  });
});
