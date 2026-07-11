import { test, expect, chromium } from "@playwright/test";

const BASE = "http://localhost:3001";
const EMAIL = "tech1@demo-ac-services.local";
const PASSWORD = "CanonicalL5!2026";
const RUNS = 20;
const path = require("path");
const OUT_PATH = path.join(__dirname, "../../docs/final-l5-01e/evidence/cold-login-repro-batch.json");

test("FINAL-L5-01E cold login reproduction batch", async () => {
  test.setTimeout(10 * 60 * 1000);
  const fs = require("fs");
  const results: Array<Record<string, unknown>> = [];

  for (let i = 1; i <= RUNS; i++) {
    const browser = await chromium.launch();
    const context = await browser.newContext();
    const page = await context.newPage();

    const timeline: string[] = [];
    page.on("console", (msg) => {
      const t = msg.text();
      if (t.includes("[auth-timeline]")) timeline.push(t);
    });
    const networkLog: string[] = [];
    page.on("response", (res) => {
      const u = res.url();
      if (u.includes("/v1/auth/") || u.includes("/v1/provider/") || u.includes("/v1/staff/")) {
        networkLog.push(`${res.status()} ${res.request().method()} ${u.replace(BASE.replace("3001","8000"),"")}`);
      }
    });

    const start = Date.now();
    let outcome = "UNKNOWN";
    let finalUrl = "";
    let errorText = "";

    try {
      await page.goto(`${BASE}/staff/login?authTimeline=1`, { waitUntil: "networkidle", timeout: 20000 });
      // Wait for React hydration to attach event handlers before interacting
      // -- filling/clicking a controlled input before hydration completes
      // races React's reconciliation and can silently wipe the typed value.
      await page.waitForFunction(() => {
        const el = document.querySelector('input[type="email"]') as HTMLInputElement | null;
        if (!el) return false;
        return Object.keys(el).some(k => k.startsWith("__reactProps") || k.startsWith("__reactFiber"));
      }, { timeout: 15000 });
      await page.fill('input[type="email"]', EMAIL);
      await page.fill('input[type="password"]', PASSWORD);
      await page.click('button[type="submit"]');

      await page.waitForFunction(
        () => window.location.pathname === "/staff/dashboard" || document.body.innerText.includes("sign in") || document.body.innerText.includes("for staff/technician accounts only"),
        { timeout: 10000 }
      ).catch(() => {});

      await page.waitForTimeout(1500);
      finalUrl = page.url();

      if (finalUrl.includes("/staff/dashboard")) {
        const bodyText = await page.innerText("body");
        if (bodyText.includes("Please sign in") || bodyText.includes("staff/technician accounts only")) {
          outcome = "LANDED_BUT_SHOWS_SIGNIN";
        } else if (bodyText.includes("My Dashboard")) {
          outcome = "SUCCESS";
        } else {
          outcome = "LANDED_BUT_UNKNOWN_CONTENT";
        }
      } else {
        outcome = "DID_NOT_REACH_DASHBOARD_URL";
      }
    } catch (e) {
      outcome = "EXCEPTION";
      errorText = e instanceof Error ? e.message : String(e);
    }

    const elapsed = Date.now() - start;
    results.push({ run: i, outcome, elapsedMs: elapsed, finalUrl, errorText, timeline, networkLog });
    await context.close();
    await browser.close();
    console.log(`run ${i}: ${outcome} (${elapsed}ms)`);
    fs.writeFileSync(OUT_PATH, JSON.stringify(results, null, 2));
  }

  fs.writeFileSync(OUT_PATH, JSON.stringify(results, null, 2));

  const successCount = results.filter(r => r.outcome === "SUCCESS").length;
  console.log(`SUCCESS: ${successCount}/${RUNS}`);
  for (const r of results) {
    console.log(`run ${r.run}: ${r.outcome} (${r.elapsedMs}ms)`);
  }
});
