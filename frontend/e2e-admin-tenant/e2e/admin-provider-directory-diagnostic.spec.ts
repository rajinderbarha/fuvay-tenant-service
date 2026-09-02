import { test, expect } from "@playwright/test";

test("provider directory settles with live records", async ({ page }) => {
  test.setTimeout(90_000);
  const responses: string[] = [];
  page.on("response", response => {
    if (response.url().includes("/v1/admin/home-services/providers")) {
      responses.push(`${response.status()} ${response.url()}`);
    }
  });

  await page.goto("http://localhost:3000/login", { waitUntil: "domcontentloaded" });
  await expect(page.getByText(/Platform operational|Platform status unavailable/)).toBeVisible({ timeout: 20_000 });
  await page.locator('input[type="email"]').fill("admin@serviceos.in");
  await page.locator('input[type="password"]').fill("Password123!");
  await page.locator('button[type="submit"]').click();
  await page.waitForURL(url => !url.pathname.includes("/login"), { timeout: 30_000 });
  await page.goto("http://localhost:3000/admin/home-services/providers", { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(20_000);

  const body = await page.locator("body").innerText();
  const skeletons = await page.locator(".ds-skeleton").count();
  console.log(JSON.stringify({ responses, skeletons, body: body.slice(0, 2500) }, null, 2));
  expect(responses.some(item => item.startsWith("200 ") && item.includes("/summary"))).toBeTruthy();
  expect(responses.some(item => item.startsWith("200 ") && item.includes("?page="))).toBeTruthy();
  await expect(page.getByText("Barha auto store")).toBeVisible();
  expect(skeletons).toBe(0);
});
