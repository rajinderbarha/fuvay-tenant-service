import { test, expect } from "@playwright/test";

async function waitHydrated(page: import("@playwright/test").Page) {
  await page.waitForFunction(() => {
    const el = document.querySelector('input[type="email"]') as HTMLInputElement | null;
    if (!el) return false;
    return Object.keys(el).some(k => k.startsWith("__reactProps") || k.startsWith("__reactFiber"));
  }, { timeout: 15000 });
}

test("real Chromium: Home Services Overview nav item now points to the real overview page, not a duplicate", async ({ page }) => {
  await page.addInitScript(() => window.localStorage.setItem("serviceos_disable_tour_e2e", "true"));
  await page.goto("http://localhost:3000/login", { waitUntil: "networkidle", timeout: 20000 });
  await waitHydrated(page);
  await page.fill('input[type="email"]', "admin@serviceos.local");
  await page.fill('input[type="password"]', "Password123!");
  await page.click('button[type="submit"]');
  await page.waitForFunction(() => window.location.pathname.includes("/admin/dashboard"), { timeout: 10000 });

  await page.getByRole("link", { name: "Overview", exact: true }).click();
  await page.waitForFunction(() => window.location.pathname === "/admin/home-services/overview", { timeout: 10000 });
  await page.waitForTimeout(1000);
  const body = await page.innerText("body");
  console.log("HS_OVERVIEW_PAGE_SNIPPET:", body.slice(0, 300));
  expect(page.url()).toContain("/admin/home-services/overview");

  // Distinct from Customer Price Experience, which must still work independently
  await page.getByRole("link", { name: "Customer Price Experience" }).click();
  await page.waitForFunction(() => window.location.pathname === "/admin/home-services/price-experience", { timeout: 10000 });
  expect(page.url()).toContain("/admin/home-services/price-experience");
});

test("real Chromium: forbidden terminology no longer appears on Finance Hub or Settings pages", async ({ page }) => {
  await page.addInitScript(() => window.localStorage.setItem("serviceos_disable_tour_e2e", "true"));
  await page.goto("http://localhost:3000/login", { waitUntil: "networkidle", timeout: 20000 });
  await waitHydrated(page);
  await page.fill('input[type="email"]', "admin@serviceos.local");
  await page.fill('input[type="password"]', "Password123!");
  await page.click('button[type="submit"]');
  await page.waitForFunction(() => window.location.pathname.includes("/admin/dashboard"), { timeout: 10000 });

  await page.goto("http://localhost:3000/admin/finance", { waitUntil: "networkidle", timeout: 20000 });
  await page.waitForTimeout(1000);
  let body = await page.innerText("body");
  expect(body).not.toContain("Wallet Balance");

  await page.goto("http://localhost:3000/admin/settings", { waitUntil: "networkidle", timeout: 20000 });
  await page.waitForTimeout(1000);
  body = await page.innerText("body");
  expect(body).not.toContain("Tenant Payouts");
  console.log("SETTINGS_FORBIDDEN_TERM_CHECK_PASSED");
});

test("real Chromium: newly-added Usage Credits and Reports nav items are reachable and real", async ({ page }) => {
  await page.addInitScript(() => window.localStorage.setItem("serviceos_disable_tour_e2e", "true"));
  await page.goto("http://localhost:3000/login", { waitUntil: "networkidle", timeout: 20000 });
  await waitHydrated(page);
  await page.fill('input[type="email"]', "admin@serviceos.local");
  await page.fill('input[type="password"]', "Password123!");
  await page.click('button[type="submit"]');
  await page.waitForFunction(() => window.location.pathname.includes("/admin/dashboard"), { timeout: 10000 });

  await page.getByRole("link", { name: "Usage Credits", exact: true }).click();
  await page.waitForFunction(() => window.location.pathname === "/admin/finance/usage-credits", { timeout: 10000 });
  await page.waitForTimeout(1000);
  let body = await page.innerText("body");
  console.log("USAGE_CREDITS_PAGE_SNIPPET:", body.slice(0, 200));
  expect(body.length).toBeGreaterThan(50);

  await page.getByRole("link", { name: "Reports", exact: true }).click();
  await page.waitForFunction(() => window.location.pathname === "/admin/reports", { timeout: 10000 });
  await page.waitForTimeout(1000);
  body = await page.innerText("body");
  console.log("REPORTS_PAGE_SNIPPET:", body.slice(0, 200));
  expect(body.length).toBeGreaterThan(50);
});
