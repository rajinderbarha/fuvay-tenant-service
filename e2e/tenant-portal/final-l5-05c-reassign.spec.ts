import { test, expect } from "@playwright/test";

async function waitHydrated(page: import("@playwright/test").Page) {
  await page.waitForFunction(() => {
    const el = document.querySelector('input[type="email"]') as HTMLInputElement | null;
    if (!el) return false;
    return Object.keys(el).some(k => k.startsWith("__reactProps") || k.startsWith("__reactFiber"));
  }, { timeout: 15000 });
}

test("real Chromium: super admin can reassign a canonical service job to a different technician", async ({ page }) => {
  await page.addInitScript(() => window.localStorage.setItem("serviceos_disable_tour_e2e", "true"));
  await page.goto("http://localhost:3000/login", { waitUntil: "networkidle", timeout: 20000 });
  await waitHydrated(page);
  await page.fill('input[type="email"]', "admin@serviceos.local");
  await page.fill('input[type="password"]', "Password123!");
  await page.click('button[type="submit"]');
  await page.waitForFunction(() => window.location.pathname.includes("/admin/dashboard"), { timeout: 10000 });

  await page.goto("http://localhost:3000/admin/home-services/service-jobs/7caeb8fd-2c6d-4629-be31-e60d940a56a2", { waitUntil: "networkidle", timeout: 20000 });
  await page.waitForTimeout(1000);

  await page.click('button:has-text("Reassign Technician")');
  await page.waitForSelector('text=Reassign Technician >> visible=true');

  const select = page.locator("select");
  await select.waitFor({ state: "visible", timeout: 10000 });
  const optionCount = await select.locator("option").count();
  expect(optionCount).toBeGreaterThan(1); // real technicians loaded, not empty

  await select.selectOption({ index: 1 });
  const chosenTechnician = await select.locator("option:checked").innerText();
  await page.fill("textarea", "FINAL-L5-05C real Chromium E2E reassignment");
  await page.click('button:has-text("Confirm Reassignment")');

  // Modal closes only on a real successful mutation (onDone callback) --
  // this is the real success signal, not a fixed sleep.
  await page.waitForSelector("textarea", { state: "detached", timeout: 15000 });

  const errorText = await page.locator("text=/JOB_|TECHNICIAN_|forbidden/i").count();
  expect(errorText).toBe(0);

  await page.waitForTimeout(500);
  const body = await page.innerText("body");
  expect(body).toContain("assignment_created"); // new timeline event rendered
  console.log("Reassigned to:", chosenTechnician);
});
