import { test, expect } from "@playwright/test";

async function waitHydrated(page: import("@playwright/test").Page) {
  await page.waitForFunction(() => {
    const el = document.querySelector('input[type="email"]') as HTMLInputElement | null;
    if (!el) return false;
    return Object.keys(el).some(k => k.startsWith("__reactProps") || k.startsWith("__reactFiber"));
  }, { timeout: 15000 });
}

test("real Chromium: super admin can override a canonical service job's status with a required reason", async ({ page }) => {
  await page.addInitScript(() => window.localStorage.setItem("serviceos_disable_tour_e2e", "true"));
  await page.goto("http://localhost:3000/login", { waitUntil: "networkidle", timeout: 20000 });
  await waitHydrated(page);
  await page.fill('input[type="email"]', "admin@serviceos.local");
  await page.fill('input[type="password"]', "Password123!");
  await page.click('button[type="submit"]');
  await page.waitForFunction(() => window.location.pathname.includes("/admin/dashboard"), { timeout: 10000 });

  await page.goto("http://localhost:3000/admin/home-services/service-jobs/7caeb8fd-2c6d-4629-be31-e60d940a56a2", { waitUntil: "networkidle", timeout: 20000 });
  await page.waitForTimeout(1000);

  // Status override -- real allowed-targets endpoint, real reason required, real confirmation.
  await page.click('button:has-text("Override Status")');
  const select = page.locator("select");
  await select.waitFor({ state: "visible", timeout: 10000 });
  const optionCount = await select.locator("option").count();
  expect(optionCount).toBeGreaterThan(1); // real allowed-override-targets loaded, not empty

  await select.selectOption({ index: 1 });
  await page.fill("textarea", "FINAL-L5-05D Chromium: override status to cancelled (stuck job)");
  await page.click('button:has-text("Confirm Override")');
  await page.waitForSelector('button:has-text("Confirm Override")', { state: "detached", timeout: 15000 });

  const body = await page.innerText("body");
  expect(body).not.toContain("JOB_STATUS_CONFLICT");
  expect(body.toLowerCase()).toContain("cancelled");
});
