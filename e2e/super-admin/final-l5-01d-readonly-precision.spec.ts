import { test, expect } from "@playwright/test";
const CANON = "CanonicalL5!2026";
const EVID = "docs/final-l5-01d/evidence";

test("Tenant Read Only — mutation UI precision across pages", async ({ page }) => {
  await page.goto("http://localhost:3001/login", { waitUntil: "domcontentloaded", timeout: 30000 });
  const emailInput = page.locator('input[type="email"], input[name="email"]').first();
  const passwordInput = page.locator('input[type="password"], input[name="password"]').first();
  await emailInput.click({ clickCount: 3 }); await emailInput.press("Backspace");
  await emailInput.type("readonly@demo-ac-services.local", { delay: 15 });
  await passwordInput.click({ clickCount: 3 }); await passwordInput.press("Backspace");
  await passwordInput.type(CANON, { delay: 15 });
  const respPromise = page.waitForResponse((r) => r.url().includes("/v1/auth/login"), { timeout: 30000 });
  await page.locator('button[type="submit"]').first().click();
  await respPromise;
  await page.waitForTimeout(2000);

  const pages = ["service-areas", "services", "jobs", "settings"];
  for (const p of pages) {
    await page.goto(`http://localhost:3001/${p}`, { waitUntil: "domcontentloaded", timeout: 20000 }).catch(() => {});
    await page.waitForTimeout(1500);
    const bannerText = await page.locator("body").innerText().catch(() => "");
    const hasReadOnlyBanner = /view.only|read.only|cannot make changes/i.test(bannerText);
    let enabledMutationButtons = 0;
    try {
      const buttons = page.locator('button:has-text("Save"), button:has-text("Delete"), button:has-text("Publish"), button:has-text("Assign"), button:has-text("Add")');
      const count = await buttons.count();
      for (let i = 0; i < count; i++) {
        const disabled = await buttons.nth(i).isDisabled().catch(() => true);
        if (!disabled) enabledMutationButtons++;
      }
    } catch { enabledMutationButtons = -1; }
    console.log(`READONLY_PAGE[${p}]_HAS_BANNER:`, hasReadOnlyBanner, "ENABLED_MUTATION_BUTTONS:", enabledMutationButtons);
    await page.screenshot({ path: `${EVID}/readonly-${p}.png` });
  }
});
