import { test, expect } from "@playwright/test";

async function waitHydrated(page: import("@playwright/test").Page) {
  await page.waitForFunction(() => {
    const el = document.querySelector('input[type="email"]') as HTMLInputElement | null;
    if (!el) return false;
    return Object.keys(el).some(k => k.startsWith("__reactProps") || k.startsWith("__reactFiber"));
  }, { timeout: 15000 });
}

test("real Chromium: canonical service-jobs detail page now shows Timeline & Notes section, no error", async ({ page }) => {
  await page.addInitScript(() => window.localStorage.setItem("serviceos_disable_tour_e2e", "true"));
  await page.goto("http://localhost:3000/login", { waitUntil: "networkidle", timeout: 20000 });
  await waitHydrated(page);
  await page.fill('input[type="email"]', "admin@serviceos.local");
  await page.fill('input[type="password"]', "Password123!");
  await page.click('button[type="submit"]');
  await page.waitForFunction(() => window.location.pathname.includes("/admin/dashboard"), { timeout: 10000 });

  await page.goto("http://localhost:3000/admin/home-services/service-jobs/7caeb8fd-2c6d-4629-be31-e60d940a56a2", { waitUntil: "networkidle", timeout: 20000 });
  await page.waitForTimeout(1500);
  const body = await page.innerText("body");
  console.log("JOB_DETAIL_SNIPPET:", body.slice(body.indexOf("Timeline"), body.indexOf("Timeline") + 200));
  expect(body.toLowerCase()).toContain("timeline & notes");
  expect(body).toContain("No timeline events recorded for this job.");
});
