import { test, chromium } from "@playwright/test";
import path from "path";

const BASE = "http://localhost:3001";
const EMAIL = "tech1@demo-ac-services.local";
const PASSWORD = "CanonicalL5!2026";
const RUNS = 5;
const AUTH_OUT = path.join(__dirname, "../../docs/final-l5-01e/evidence/authorized-deeplink-repro-batch.json");
const UNAUTH_OUT = path.join(__dirname, "../../docs/final-l5-01e/evidence/unauthorized-deeplink-repro-batch.json");

async function waitHydrated(page: import("@playwright/test").Page) {
  await page.waitForFunction(() => {
    const el = document.querySelector('input[type="email"]') as HTMLInputElement | null;
    if (!el) return false;
    return Object.keys(el).some(k => k.startsWith("__reactProps") || k.startsWith("__reactFiber"));
  }, { timeout: 15000 });
}

async function login(page: import("@playwright/test").Page) {
  await page.goto(`${BASE}/staff/login`, { waitUntil: "networkidle", timeout: 20000 });
  await waitHydrated(page);
  await page.fill('input[type="email"]', EMAIL);
  await page.fill('input[type="password"]', PASSWORD);
  await page.click('button[type="submit"]');
  await page.waitForFunction(() => window.location.pathname === "/staff/dashboard", { timeout: 10000 });
  await page.waitForTimeout(1000);
}

const fs = require("fs");

test("FINAL-L5-01E authorized deep-link batch", async () => {
  test.setTimeout(5 * 60 * 1000);
  const results: Array<Record<string, unknown>> = [];
  for (let i = 1; i <= RUNS; i++) {
    const browser = await chromium.launch();
    const context = await browser.newContext();
    const page = await context.newPage();
    let outcome = "UNKNOWN", finalUrl = "", errorText = "";
    const start = Date.now();
    try {
      await login(page);
      // Deep-link directly to a non-dashboard protected staff page while
      // already holding a valid technician session.
      await page.goto(`${BASE}/staff/jobs`, { waitUntil: "networkidle", timeout: 20000 });
      await page.waitForTimeout(1000);
      finalUrl = page.url();
      const bodyText = await page.innerText("body");
      outcome = finalUrl.includes("/staff/jobs") && !bodyText.includes("Please sign in") ? "SUCCESS" : "BLOCKED_OR_REDIRECTED";
    } catch (e) {
      outcome = "EXCEPTION"; errorText = e instanceof Error ? e.message : String(e);
    }
    const elapsed = Date.now() - start;
    results.push({ run: i, outcome, elapsedMs: elapsed, finalUrl, errorText });
    console.log(`authorized-deeplink run ${i}: ${outcome} (${elapsed}ms)`);
    await context.close(); await browser.close();
    fs.writeFileSync(AUTH_OUT, JSON.stringify(results, null, 2));
  }
  console.log(`AUTH_DEEPLINK SUCCESS: ${results.filter(r => r.outcome === "SUCCESS").length}/${RUNS}`);
});

test("FINAL-L5-01E unauthorized deep-link batch", async () => {
  test.setTimeout(5 * 60 * 1000);
  const results: Array<Record<string, unknown>> = [];
  for (let i = 1; i <= RUNS; i++) {
    const browser = await chromium.launch();
    const context = await browser.newContext();
    const page = await context.newPage();
    let outcome = "UNKNOWN", finalUrl = "", errorText = "";
    const start = Date.now();
    try {
      // No login at all -- deep-link straight to a protected staff page
      // with zero session state.
      await page.goto(`${BASE}/staff/jobs`, { waitUntil: "networkidle", timeout: 20000 });
      await page.waitForTimeout(1500);
      finalUrl = page.url();
      const bodyText = await page.innerText("body");
      const blocked = bodyText.includes("Please sign in") || bodyText.includes("Not logged in");
      outcome = blocked ? "SUCCESS_BLOCKED" : "LEAK_SHOWED_PROTECTED_CONTENT";
    } catch (e) {
      outcome = "EXCEPTION"; errorText = e instanceof Error ? e.message : String(e);
    }
    const elapsed = Date.now() - start;
    results.push({ run: i, outcome, elapsedMs: elapsed, finalUrl, errorText });
    console.log(`unauthorized-deeplink run ${i}: ${outcome} (${elapsed}ms)`);
    await context.close(); await browser.close();
    fs.writeFileSync(UNAUTH_OUT, JSON.stringify(results, null, 2));
  }
  console.log(`UNAUTH_DEEPLINK SUCCESS: ${results.filter(r => r.outcome === "SUCCESS_BLOCKED").length}/${RUNS}`);
});
