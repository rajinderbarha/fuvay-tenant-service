import { test, expect } from "@playwright/test";

async function waitHydrated(page: import("@playwright/test").Page) {
  await page.waitForFunction(() => {
    const el = document.querySelector('input[type="email"]') as HTMLInputElement | null;
    if (!el) return false;
    return Object.keys(el).some(k => k.startsWith("__reactProps") || k.startsWith("__reactFiber"));
  }, { timeout: 15000 });
}

test.describe("FINAL-L5-05E: canonical Jobs navigation migration", () => {
  test("real Chromium: primary Jobs sidebar link opens the canonical service_jobs page with summary + SLA", async ({ page }) => {
    const requests: string[] = [];
    page.on("request", req => requests.push(req.url()));

    await page.addInitScript(() => window.localStorage.setItem("serviceos_disable_tour_e2e", "true"));
    await page.goto("http://localhost:3000/login", { waitUntil: "networkidle", timeout: 20000 });
    await waitHydrated(page);
    await page.fill('input[type="email"]', "admin@serviceos.local");
    await page.fill('input[type="password"]', "Password123!");
    await page.click('button[type="submit"]');
    await page.waitForFunction(() => window.location.pathname.includes("/admin/dashboard"), { timeout: 10000 });

    await page.click('a:has-text("Jobs")');
    await page.waitForFunction(() => window.location.pathname.includes("/admin/home-services/service-jobs"), { timeout: 10000 });
    expect(page.url()).toContain("/admin/home-services/service-jobs");

    await page.waitForTimeout(1500);
    const body = await page.innerText("body");
    expect(body).toContain("Total");
    expect(body).toContain("Breached");

    const legacyRequests = requests.filter(u => u.includes("/v1/jobs"));
    expect(legacyRequests).toEqual([]);
  });

  test("real Chromium: /admin/operations redirects to canonical Jobs with no legacy API traffic", async ({ page }) => {
    const requests: string[] = [];
    page.on("request", req => requests.push(req.url()));

    await page.addInitScript(() => window.localStorage.setItem("serviceos_disable_tour_e2e", "true"));
    await page.goto("http://localhost:3000/login", { waitUntil: "networkidle", timeout: 20000 });
    await waitHydrated(page);
    await page.fill('input[type="email"]', "admin@serviceos.local");
    await page.fill('input[type="password"]', "Password123!");
    await page.click('button[type="submit"]');
    await page.waitForFunction(() => window.location.pathname.includes("/admin/dashboard"), { timeout: 10000 });

    await page.goto("http://localhost:3000/admin/operations", { waitUntil: "networkidle", timeout: 20000 });
    await page.waitForFunction(() => window.location.pathname.includes("/admin/home-services/service-jobs"), { timeout: 10000 });
    expect(page.url()).toContain("/admin/home-services/service-jobs");

    const legacyRequests = requests.filter(u => u.includes("/v1/jobs"));
    expect(legacyRequests).toEqual([]);
  });
});
