import { chromium } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
const page = await context.newPage();

async function inspect(name, url) {
  await page.goto(url);
  await page.waitForLoadState("domcontentloaded");
  await page.waitForTimeout(800);
  const result = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze();
  return {
    name,
    url: page.url(),
    violations: result.violations.map(v => ({
      id: v.id,
      impact: v.impact,
      nodes: v.nodes.map(n => ({ target: n.target, html: n.html, failureSummary: n.failureSummary })),
    })),
  };
}

const output = [];
output.push(await inspect("register", "http://localhost:3001/register"));

await page.goto("http://localhost:3001/login");
await page.getByPlaceholder("Enter your email or mobile number").fill("visual.audit.1786461955262@example.com");
await page.getByPlaceholder("Enter your password").fill("VisualAudit!2026");
await page.getByRole("button", { name: /sign in/i }).click();
await page.waitForTimeout(1200);

for (const [name, path] of [
  ["overview", "/tenant/home-services/setup/overview"],
  ["review", "/tenant/home-services/setup/review"],
  ["services", "/tenant/home-services/setup/services-pricing"],
  ["finance", "/tenant/home-services/setup/finance"],
]) {
  output.push(await inspect(name, `http://localhost:3001${path}`));
}

console.log(JSON.stringify(output, null, 2));
await context.close();
await browser.close();
