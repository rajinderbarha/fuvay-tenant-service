import { test, expect } from "@playwright/test";
const CANON = "CanonicalL5!2026";
const RUNS = 5;

test("Technician redirect — repeated cold logins with proper waitForURL", async ({ browser }) => {
  const timings: number[] = [];
  const finalRoutes: string[] = [];
  const failures: string[] = [];

  for (let i = 0; i < RUNS; i++) {
    const context = await browser.newContext();
    const page = await context.newPage();
    const t0 = Date.now();
    try {
      await page.goto("http://localhost:3001/staff/login", { waitUntil: "domcontentloaded", timeout: 30000 });
      const emailInput = page.locator('input[type="email"], input[name="email"]').first();
      const passwordInput = page.locator('input[type="password"], input[name="password"]').first();
      await emailInput.fill("tech1@demo-ac-services.local");
      await passwordInput.fill(CANON);
      await page.locator('button[type="submit"]').first().click();
      await page.waitForURL(/\/staff\/dashboard/, { timeout: 15000 });
      const t1 = Date.now();
      timings.push(t1 - t0);
      finalRoutes.push(page.url());
    } catch (e) {
      failures.push(`run ${i}: ${(e as Error).message.slice(0, 100)}`);
      finalRoutes.push(page.url());
    }
    await context.close();
  }

  console.log("RUNS:", RUNS);
  console.log("TIMINGS_MS:", JSON.stringify(timings));
  console.log("MIN_MS:", Math.min(...timings) || -1);
  console.log("MAX_MS:", Math.max(...timings) || -1);
  console.log("MEDIAN_MS:", timings.length ? timings.sort((a,b)=>a-b)[Math.floor(timings.length/2)] : -1);
  console.log("FAILED_RUNS:", failures.length);
  console.log("FAILURES:", JSON.stringify(failures));
  console.log("FINAL_ROUTES:", JSON.stringify(finalRoutes));
});
