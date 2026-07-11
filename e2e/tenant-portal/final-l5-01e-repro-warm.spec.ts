import { test, chromium } from "@playwright/test";
import path from "path";

const BASE = "http://localhost:3001";
const EMAIL = "tech1@demo-ac-services.local";
const PASSWORD = "CanonicalL5!2026";
const RUNS = 20;
const OUT_PATH = path.join(__dirname, "../../docs/final-l5-01e/evidence/warm-login-repro-batch.json");

async function waitHydrated(page: import("@playwright/test").Page) {
  await page.waitForFunction(() => {
    const el = document.querySelector('input[type="email"]') as HTMLInputElement | null;
    if (!el) return false;
    return Object.keys(el).some(k => k.startsWith("__reactProps") || k.startsWith("__reactFiber"));
  }, { timeout: 15000 });
}

/** "Warm" = single long-lived browser/tab reused across repeated login
 * attempts (session storage cleared between each, but no fresh browser
 * process/context) -- distinct from the cold-login batch's fresh context
 * per run. Exercises repeated navigation within one already-warmed
 * Turbopack/React runtime instance. */
test("FINAL-L5-01E warm login reproduction batch", async () => {
  test.setTimeout(10 * 60 * 1000);
  const fs = require("fs");
  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();
  const results: Array<Record<string, unknown>> = [];

  for (let i = 1; i <= RUNS; i++) {
    const start = Date.now();
    let outcome = "UNKNOWN";
    let finalUrl = "";
    let errorText = "";
    try {
      await page.goto(`${BASE}/staff/login`, { waitUntil: "networkidle", timeout: 20000 });
      await page.evaluate(() => localStorage.clear());
      await waitHydrated(page);
      await page.fill('input[type="email"]', EMAIL);
      await page.fill('input[type="password"]', PASSWORD);
      await page.click('button[type="submit"]');
      await page.waitForFunction(
        () => window.location.pathname === "/staff/dashboard" || document.body.innerText.includes("sign in"),
        { timeout: 10000 }
      ).catch(() => {});
      await page.waitForTimeout(1200);
      finalUrl = page.url();
      if (finalUrl.includes("/staff/dashboard")) {
        const bodyText = await page.innerText("body");
        outcome = bodyText.includes("My Dashboard") ? "SUCCESS" : "LANDED_BUT_UNKNOWN_CONTENT";
      } else {
        outcome = "DID_NOT_REACH_DASHBOARD_URL";
      }
    } catch (e) {
      outcome = "EXCEPTION";
      errorText = e instanceof Error ? e.message : String(e);
    }
    const elapsed = Date.now() - start;
    results.push({ run: i, outcome, elapsedMs: elapsed, finalUrl, errorText });
    console.log(`run ${i}: ${outcome} (${elapsed}ms)`);
    fs.writeFileSync(OUT_PATH, JSON.stringify(results, null, 2));
  }

  await context.close();
  await browser.close();
  const successCount = results.filter(r => r.outcome === "SUCCESS").length;
  console.log(`SUCCESS: ${successCount}/${RUNS}`);
});
