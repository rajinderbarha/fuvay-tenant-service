import { test } from "@playwright/test";

test("single diagnostic login", async ({ page }) => {
  test.setTimeout(45000);
  page.on("console", (msg) => console.log("[console]", msg.type(), msg.text()));
  page.on("pageerror", (err) => console.log("[pageerror]", err.message));
  page.on("requestfailed", (req) => console.log("[requestfailed]", req.url(), req.failure()?.errorText));
  page.on("response", (res) => {
    if (res.url().includes("/v1/")) console.log("[response]", res.status(), res.url());
  });

  console.log("t0 goto");
  await page.goto("http://localhost:3001/staff/login?authTimeline=1", { waitUntil: "networkidle", timeout: 20000 });
  console.log("t1 goto done, url=", page.url());
  // Wait for React hydration to actually attach before typing, to rule out
  // a hydration race (pre-hydration DOM writes getting wiped when React
  // reconciles its initial empty controlled-input state).
  await page.waitForFunction(() => {
    const el = document.querySelector('input[type="email"]') as HTMLInputElement | null;
    if (!el) return false;
    const keys = Object.keys(el);
    return keys.some(k => k.startsWith("__reactProps") || k.startsWith("__reactFiber"));
  }, { timeout: 15000 });
  console.log("t1b hydrated");

  await page.fill('input[type="email"]', "tech1@demo-ac-services.local");
  await page.fill('input[type="password"]', "CanonicalL5!2026");
  console.log("t2 filled");

  await page.click('button[type="submit"]', { timeout: 10000 });
  console.log("t3 clicked");

  await page.waitForTimeout(4000);
  console.log("t4 after wait, url=", page.url());
  const body = await page.innerText("body");
  console.log("t5 body snippet:", body.slice(0, 300));
});
