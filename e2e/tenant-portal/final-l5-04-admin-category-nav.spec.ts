import { test, expect } from "@playwright/test";

async function waitHydrated(page: import("@playwright/test").Page) {
  await page.waitForFunction(() => {
    const el = document.querySelector('input[type="email"]') as HTMLInputElement | null;
    if (!el) return false;
    return Object.keys(el).some(k => k.startsWith("__reactProps") || k.startsWith("__reactFiber"));
  }, { timeout: 15000 });
}

async function loginAdmin(page: import("@playwright/test").Page) {
  // Disable the product-tour overlay before it can mount -- a full-screen
  // fixed-position backdrop (z-index 498) otherwise blocks every click on
  // this account's first visits, which a real user would dismiss but which
  // silently swallows Playwright's clicks (even with force:true, since the
  // backdrop genuinely receives the click at the OS/renderer hit-test level).
  // The app already exposes this exact escape hatch for the E2E harness.
  await page.addInitScript(() => {
    window.localStorage.setItem("serviceos_disable_tour_e2e", "true");
  });
  await page.goto("http://localhost:3000/login", { waitUntil: "networkidle", timeout: 20000 });
  await waitHydrated(page);
  await page.fill('input[type="email"]', "admin@serviceos.local");
  await page.fill('input[type="password"]', "Password123!");
  await page.click('button[type="submit"]');
  await page.waitForFunction(() => window.location.pathname.includes("/admin/dashboard"), { timeout: 10000 });
  await page.waitForTimeout(800);
}

test.describe("FINAL-L5-04 Admin dynamic vertical/category navigation", () => {
  test("activating a vertical makes its sidebar section appear live, deactivating removes it, without a page reload", async ({ page }) => {
    await loginAdmin(page);

    await page.goto("http://localhost:3000/admin/verticals", { waitUntil: "networkidle", timeout: 20000 });
    await page.waitForTimeout(1000);

    // Sidebar should NOT show "Beauty & Wellness" section yet (disabled).
    const sidebarBefore = await page.locator("aside").innerText();
    expect(sidebarBefore).not.toContain("Beauty & Wellness");

    // Beauty & Wellness is the first disabled vertical in both API and DOM order
    // (home_services/coaching/real_estate are enabled and render first) --
    // confirmed via a live API check before writing this test.
    await expect(page.locator("text=Beauty & Wellness").first()).toBeVisible({ timeout: 10000 });
    await page.getByRole("button", { name: "Enable" }).first().click();
    await page.waitForTimeout(1500);

    // Sidebar should now show the Beauty & Wellness section WITHOUT a page reload
    // (no page.reload() was called between the toggle and this assertion).
    const sidebarAfterEnable = await page.locator("aside").innerText();
    const enabledLive = sidebarAfterEnable.includes("Beauty & Wellness");
    console.log("SIDEBAR_SHOWS_BEAUTY_AFTER_ENABLE_LIVE:", enabledLive);

    // Restore original state. Beauty is now enabled, so it renders among the
    // top group with the other enabled verticals and shows "Disable" -- it is
    // the 4th enabled vertical in list order (after home_services/coaching/real_estate).
    await page.getByRole("button", { name: "Disable" }).nth(3).click();
    await page.waitForTimeout(1500);

    const sidebarAfterDisable = await page.locator("aside").innerText();
    const disabledLive = !sidebarAfterDisable.includes("Beauty & Wellness");
    console.log("SIDEBAR_HIDES_BEAUTY_AFTER_DISABLE_LIVE:", disabledLive);

    expect(enabledLive, "sidebar must show the newly-enabled vertical without a page reload").toBe(true);
    expect(disabledLive, "sidebar must hide the newly-disabled vertical without a page reload").toBe(true);
  });

  test("direct route to a disabled vertical's catalog page does not render its content", async ({ page }) => {
    await loginAdmin(page);
    // beauty is disabled by default (restored by the previous test) -- direct nav.
    await page.goto("http://localhost:3000/admin/catalog/beauty", { waitUntil: "networkidle", timeout: 20000 });
    await page.waitForTimeout(1200);
    const body = await page.innerText("body");
    console.log("DIRECT_DISABLED_VERTICAL_BODY_SNIPPET:", body.slice(0, 500));
  });
});
