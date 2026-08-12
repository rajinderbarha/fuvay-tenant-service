import { chromium, devices } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const auditDir = path.dirname(fileURLToPath(import.meta.url));
const baseURL = "http://localhost:3001";
const runId = Date.now().toString();
const account = {
  name: "Visual Audit Owner",
  email: `visual.audit.${runId}@example.com`,
  phone: `+9194${runId.slice(-8)}`,
  password: "VisualAudit!2026",
  business: "Visual Audit Home Services",
};

const results = {
  started_at: new Date().toISOString(),
  account: { email: account.email },
  screenshots: [],
  observations: [],
  accessibility: [],
  failed_responses: [],
  console_errors: [],
  legal_routes: {},
};

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({
  viewport: { width: 1440, height: 1000 },
  colorScheme: "light",
});
const page = await context.newPage();

page.on("response", response => {
  if (response.status() >= 400) {
    results.failed_responses.push({ status: response.status(), url: response.url() });
  }
});
page.on("console", message => {
  if (message.type() === "error") results.console_errors.push(message.text());
});

async function stable(target = page) {
  await target.waitForLoadState("domcontentloaded");
  await target.waitForTimeout(800);
}

async function capture(name, note, target = page) {
  await stable(target);
  const file = `${name}.png`;
  const filePath = path.join(auditDir, file);
  await target.screenshot({ path: filePath, fullPage: true });
  results.screenshots.push({
    file,
    url: target.url(),
    note,
    title: await target.title(),
    body_excerpt: (await target.locator("body").innerText()).slice(0, 1200),
  });
}

async function axe(name, target = page) {
  try {
    const analysis = await new AxeBuilder({ page: target }).analyze();
    results.accessibility.push({
      name,
      url: target.url(),
      violations: analysis.violations.map(v => ({
        id: v.id,
        impact: v.impact,
        description: v.description,
        nodes: v.nodes.length,
      })),
    });
  } catch (error) {
    results.accessibility.push({ name, url: target.url(), error: String(error) });
  }
}

async function recordFocusOrder(target, count = 12) {
  const order = [];
  for (let i = 0; i < count; i += 1) {
    await target.keyboard.press("Tab");
    order.push(await target.evaluate(() => {
      const el = document.activeElement;
      if (!el) return null;
      return {
        tag: el.tagName,
        text: (el.getAttribute("aria-label") || el.textContent || "").trim().slice(0, 100),
        placeholder: el.getAttribute("placeholder"),
        href: el.getAttribute("href"),
      };
    }));
  }
  results.observations.push({ name: "register_keyboard_focus_order", order });
}

try {
  await page.goto(`${baseURL}/register`);
  await stable();
  await recordFocusOrder(page);
  await capture("01-register-owner-account", "Initial owner-account step");
  await axe("register_owner_account");

  await page.getByRole("button", { name: /Continue to verification/i }).click();
  await page.getByText("Please complete the required fields before continuing.").waitFor();
  await capture("02-register-account-validation", "Empty-submit validation state");

  await page.getByPlaceholder("Enter your full name").fill(account.name);
  await page.getByPlaceholder("Enter mobile number").fill(account.phone);
  await page.getByPlaceholder("Enter your email address").fill(account.email);
  await page.getByPlaceholder("Create a password").fill(account.password);
  await page.getByPlaceholder("Re-enter your password").fill(account.password);
  await capture("03-register-account-filled", "Completed owner-account form");

  const ownerResponsePromise = page.waitForResponse(r =>
    r.url().includes("/v1/public/signup/owner-account") && r.request().method() === "POST"
  );
  await page.getByRole("button", { name: /Continue to verification/i }).click();
  const ownerResponse = await ownerResponsePromise;
  const ownerJson = await ownerResponse.json();
  const ownerData = ownerJson.data ?? ownerJson;
  const mobileOtp = ownerData.dev_otp_mobile ?? ownerData.dev_otps?.mobile;
  const emailOtp = ownerData.dev_otp_email ?? ownerData.dev_otps?.email;
  results.observations.push({
    name: "owner_account_contract",
    status: ownerResponse.status(),
    response_keys: Object.keys(ownerData),
    ui_development_alert_visible: await page.getByText("Development mode").isVisible().catch(() => false),
    flat_dev_codes_present: Boolean(ownerData.dev_otp_mobile && ownerData.dev_otp_email),
    nested_dev_codes_present: Boolean(ownerData.dev_otps),
  });
  await capture("04-register-verify-contact", "Verification step as rendered after account creation");
  await axe("register_verify_contact");

  if (!mobileOtp || !emailOtp) throw new Error("Audit cannot continue: no development OTPs were returned.");
  await page.locator('input[placeholder="Enter code"]').nth(0).fill(String(mobileOtp));
  await page.getByRole("button", { name: "Verify", exact: true }).nth(0).click();
  await page.getByText("Verified", { exact: true }).nth(0).waitFor();
  await page.locator('input[placeholder="Enter code"]').nth(0).fill(String(emailOtp));
  await page.getByRole("button", { name: "Verify", exact: true }).nth(0).click();
  await page.getByText("Verified", { exact: true }).nth(1).waitFor();
  await capture("05-register-contact-verified", "Both verification channels completed");

  await page.getByRole("button", { name: /^Continue/ }).click();
  await page.getByRole("heading", { name: "Business identity" }).waitFor();
  await capture("06-register-business-identity", "Business identity step before entry");
  await page.getByPlaceholder("e.g. Rahul AC Services").fill(account.business);
  await page.getByPlaceholder("e.g. Mumbai").fill("Bengaluru");
  await page.getByPlaceholder("e.g. Maharashtra").fill("Karnataka");
  await page.getByPlaceholder("A short description of the services you offer").fill("Reliable home appliance repair and maintenance.");
  await capture("07-register-business-identity-filled", "Completed business identity fields");
  await axe("register_business_identity");
  await page.getByRole("button", { name: /^Continue/ }).click();

  await page.getByRole("heading", { name: "Select your vertical" }).waitFor();
  await page.getByRole("button", { name: /Home Services/i }).waitFor();
  await capture("08-register-select-vertical", "Available vertical choices");
  await page.getByRole("button", { name: /Home Services/i }).click();
  await page.getByRole("button", { name: /^Continue/ }).click();

  await page.getByRole("heading", { name: /Review & consent/i }).waitFor();
  await capture("09-register-review-consent", "Review step before required consent");
  await axe("register_review_consent");
  await page.getByRole("button", { name: "Create workspace" }).click();
  await page.getByText("Please confirm both required checkboxes.").waitFor();
  await capture("10-register-review-validation", "Review validation after missing consent");

  for (const route of ["/terms", "/privacy", "/legal/terms", "/legal/privacy"]) {
    const response = await context.request.get(`${baseURL}${route}`);
    results.legal_routes[route] = response.status();
  }

  await page.locator('input[type="checkbox"]').nth(0).check();
  await page.locator('input[type="checkbox"]').nth(1).check();
  await capture("11-register-review-ready", "Review step with required consent selected");

  const completeResponsePromise = page.waitForResponse(r =>
    r.url().includes("/v1/public/signup/complete") && r.request().method() === "POST"
  );
  await page.getByRole("button", { name: "Create workspace" }).click();
  const completeResponse = await completeResponsePromise;
  let completeData = {};
  let completeBodyReadError = null;
  try {
    const completeJson = await completeResponse.json();
    completeData = completeJson.data ?? completeJson;
  } catch (error) {
    // A window.location navigation can release the response body before
    // Playwright reads it. The status and actual destination remain valid
    // audit evidence, so preserve the read failure and continue the flow.
    completeBodyReadError = String(error);
  }
  results.observations.push({
    name: "signup_complete_contract",
    status: completeResponse.status(),
    response_keys: Object.keys(completeData),
    vertical_key: completeData.vertical_key ?? null,
    enrollment_status: completeData.enrollment_status ?? null,
    body_read_error: completeBodyReadError,
  });
  await page.waitForURL(/\/(dashboard|tenant\/home-services\/setup\/overview)/, { timeout: 15000 });
  await capture("12-post-signup-destination", "Actual immediate destination after workspace creation");

  await page.goto(`${baseURL}/tenant/home-services/setup/overview`);
  await page.getByText("Setup progress", { exact: false }).first().waitFor({ timeout: 15000 }).catch(() => {});
  await capture("13-setup-overview", "Home Services setup overview");
  await axe("setup_overview");

  const setupPages = [
    ["14-setup-business-profile", "/tenant/home-services/setup/business-profile", "Business profile setup"],
    ["15-setup-documents", "/tenant/home-services/setup/documents", "Verification documents setup"],
    ["16-setup-services-pricing", "/tenant/home-services/setup/services-pricing", "Services and pricing setup"],
    ["17-setup-coverage-availability", "/tenant/home-services/setup/coverage-availability", "Coverage and availability setup"],
    ["18-setup-staff", "/tenant/home-services/setup/staff", "Staff and technicians setup"],
    ["19-setup-finance", "/tenant/home-services/setup/finance", "Finance readiness setup"],
    ["20-setup-review", "/tenant/home-services/setup/review", "Final review and submission"],
  ];
  for (const [name, route, note] of setupPages) {
    await page.goto(`${baseURL}${route}`);
    await stable();
    await capture(name, note);
    await axe(name);
  }

  const storageState = await context.storageState();
  const mobileContext = await browser.newContext({
    ...devices["Pixel 7"],
    storageState,
    colorScheme: "light",
  });
  const mobilePage = await mobileContext.newPage();
  await mobilePage.goto(`${baseURL}/register`);
  await capture("21-register-mobile", "Mobile owner-account layout", mobilePage);
  results.observations.push({
    name: "register_mobile_overflow",
    has_horizontal_overflow: await mobilePage.evaluate(() => document.documentElement.scrollWidth > window.innerWidth),
    scroll_width: await mobilePage.evaluate(() => document.documentElement.scrollWidth),
    viewport_width: await mobilePage.evaluate(() => window.innerWidth),
  });
  await mobilePage.goto(`${baseURL}/tenant/home-services/setup/overview`);
  await capture("22-setup-overview-mobile", "Mobile setup-overview layout", mobilePage);
  results.observations.push({
    name: "setup_mobile_overflow",
    has_horizontal_overflow: await mobilePage.evaluate(() => document.documentElement.scrollWidth > window.innerWidth),
    scroll_width: await mobilePage.evaluate(() => document.documentElement.scrollWidth),
    viewport_width: await mobilePage.evaluate(() => window.innerWidth),
  });
  await mobileContext.close();
} catch (error) {
  results.fatal_error = String(error?.stack ?? error);
} finally {
  results.finished_at = new Date().toISOString();
  await writeFile(path.join(auditDir, "audit-results.json"), JSON.stringify(results, null, 2));
  await context.close();
  await browser.close();
}

console.log(JSON.stringify({
  auditDir,
  screenshots: results.screenshots.length,
  observations: results.observations.length,
  accessibilityChecks: results.accessibility.length,
  fatal_error: results.fatal_error ?? null,
  account: results.account,
}, null, 2));
