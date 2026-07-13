import { test, expect } from "@playwright/test";

async function login(page, email, password) {
  await page.goto("http://localhost:3000/login");
  await page.fill('input[type="email"]', email);
  await page.fill('input[type="password"]', password);
  await Promise.all([
    page.waitForResponse(r => r.url().includes("/v1/auth/login") && r.status() === 200, { timeout: 30000 }),
    page.click('button[type="submit"]'),
  ]);
  await page.waitForTimeout(1500);
}

async function gotoPoliciesTab(page) {
  await page.goto("http://localhost:3000/admin/security");
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(3000);
  await page.evaluate(() => {
    const btns = Array.from(document.querySelectorAll('button'));
    const target = btns.find(b => b.textContent && b.textContent.includes('Security Policies'));
    if (target) (target as HTMLElement).click();
  });
  await page.waitForTimeout(3000);
}

test("admin_security does NOT see Policy Edit button", async ({ page }) => {
  test.setTimeout(60000);
  await login(page, "admin.security@serviceos.local", "CanonicalL5!2026");
  await gotoPoliciesTab(page);
  const editButtons = await page.locator('button:has-text("Edit")').count();
  console.log("admin_security Edit button count:", editButtons);
  expect(editButtons).toBe(0);
});

test("super_admin DOES see Policy Edit button", async ({ page }) => {
  test.setTimeout(60000);
  await login(page, "admin@serviceos.local", "Password123!");
  await gotoPoliciesTab(page);
  const editButtons = await page.locator('button:has-text("Edit")').count();
  console.log("super_admin Edit button count:", editButtons);
  expect(editButtons).toBeGreaterThan(0);
});

test("admin_operations does NOT see Policy Edit button", async ({ page }) => {
  test.setTimeout(60000);
  await login(page, "admin.ops@serviceos.local", "CanonicalL5!2026");
  await gotoPoliciesTab(page);
  const editButtons = await page.locator('button:has-text("Edit")').count();
  console.log("admin_operations Edit button count:", editButtons);
  expect(editButtons).toBe(0);
});

test("admin_finance does NOT see Policy Edit button", async ({ page }) => {
  test.setTimeout(60000);
  await login(page, "admin.finance@serviceos.local", "CanonicalL5!2026");
  await gotoPoliciesTab(page);
  const editButtons = await page.locator('button:has-text("Edit")').count();
  console.log("admin_finance Edit button count:", editButtons);
  expect(editButtons).toBe(0);
});

test("admin_readonly does NOT see Policy Edit button", async ({ page }) => {
  test.setTimeout(60000);
  await login(page, "admin.readonly@serviceos.local", "CanonicalL5!2026");
  await gotoPoliciesTab(page);
  const editButtons = await page.locator('button:has-text("Edit")').count();
  console.log("admin_readonly Edit button count:", editButtons);
  expect(editButtons).toBe(0);
});
