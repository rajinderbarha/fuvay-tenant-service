import { test, expect } from "@playwright/test";
import path from "path";

test("reproduce PDF upload Failed to fetch", async ({ page }) => {
  const consoleErrors: string[] = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") consoleErrors.push(msg.text());
  });
  page.on("pageerror", (err) => consoleErrors.push("PAGEERROR: " + err.message));
  page.on("requestfailed", (req) => {
    console.log("REQUEST_FAILED:", req.url(), req.failure()?.errorText);
  });
  page.on("response", (res) => {
    if (res.url().includes("extraction/upload")) {
      console.log("RESPONSE:", res.status(), res.url());
    }
  });

  await page.goto("http://localhost:3001/login");
  await page.fill('input[type="email"], input[name="email"]', "provider@serviceos.local");
  await page.fill('input[type="password"], input[name="password"]', "Password123!");
  await page.click('button[type="submit"]');
  await page.waitForURL(/dashboard|inventory/, { timeout: 15000 }).catch(() => {});

  await page.goto("http://localhost:3001/inventory");
  await page.waitForTimeout(2000);

  const fileInput = page.locator('input[type="file"]');
  const testPdf = path.resolve("C:\\Users\\AIVIQT~1\\AppData\\Local\\Temp\\claude\\g--serviceos\\3d0d814f-3406-4825-90db-9014ed13c522\\scratchpad\\test_idempotency.pdf");
  await fileInput.setInputFiles(testPdf);

  await page.waitForTimeout(8000);

  console.log("CONSOLE_ERRORS:", JSON.stringify(consoleErrors, null, 2));
  const bodyText = await page.locator("body").innerText();
  console.log("PAGE_TEXT_SNIPPET:", bodyText.slice(0, 2000));
});
