import { chromium } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const auditDir = path.dirname(fileURLToPath(import.meta.url));
const phase = process.env.REFERENCE_PHASE ?? "draft";
const email = "visual.audit.1786461955262@example.com";
const password = "VisualAudit!2026";

const pagesByPhase = {
  approved: [
    { key: "activation", route: "/onboarding/activation-center", heading: "Activation center", features: ["Your setup has been approved", "Activation checklist", "Activation progress", "Finance policy", "What goes live"] },
    { key: "application-approved", route: "/onboarding/application-status", heading: "Application status", features: ["Submitted setup", "Submission details", "What happens next"] },
  ],
  draft: [
    { key: "setup-overview", route: "/tenant/home-services/setup/overview", heading: /Welcome to ServiceOS/, features: ["Home Services setup", "Workspace status", "What happens next?", "Contact support"] },
    { key: "business-profile", route: "/tenant/home-services/setup/business-profile", heading: "Business profile", features: ["Business details", "Registered address", "Profile readiness", "Business identity", "Save & continue"] },
    { key: "documents", route: "/tenant/home-services/setup/documents", heading: "Verification documents", features: ["Required documents", "Upload guidelines", "Additional documents", "Save & continue"] },
    { key: "services-pricing", route: "/tenant/home-services/setup/services-pricing", heading: "Services & pricing", features: ["Service groups", "Offer this service", "Pricing hierarchy", "Admin blueprint", "Save & continue"] },
    { key: "coverage", route: "/tenant/home-services/setup/coverage-availability", heading: "Coverage & availability", features: ["Service coverage", "Weekly business hours", "Booking controls", "Schedule exceptions", "Save & continue"] },
    { key: "staff", route: "/tenant/home-services/setup/staff", heading: "Staff & technicians", features: ["Team roster", "Team readiness", "Add team member"] },
    { key: "finance-readiness", route: "/tenant/home-services/setup/finance", heading: "Finance readiness", features: ["Customer payment collection", "Business invoice details", "Home Services policy", "Save & continue"] },
    { key: "review-submit", route: "/tenant/home-services/setup/review", heading: "Review & submit", features: ["Setup review", "Declarations", "Submission summary", "Submit for review"] },
    { key: "onboarding-help", route: "/help", heading: "Help & support", features: ["Create a support request", "Reviewer feedback and requests", "Activation requirements"] },
  ],
  active: [
    { key: "home-services-finance", route: "/home-services/finance", heading: "Home Services Finance", features: ["Finance readiness", "Usage Credits", "Security Deposit", "Policy & Audit", "Buy Usage Credits"] },
    { key: "help-support", route: "/help-support", heading: "Help & Support", features: ["Create support request", "Quick help", "My Support Requests"] },
  ],
};

const selectedPages = pagesByPhase[phase];
if (!selectedPages) throw new Error(`Unknown REFERENCE_PHASE: ${phase}`);

const results = { phase, started_at: new Date().toISOString(), pages: [], failed_responses: [], console_errors: [] };
let currentPageKey = "login";
const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
const page = await context.newPage();
page.on("response", response => {
  if (response.status() >= 400) results.failed_responses.push({ page: currentPageKey, status: response.status(), url: response.url() });
});
page.on("console", message => {
  if (message.type() === "error") results.console_errors.push({ page: currentPageKey, text: message.text() });
});

try {
  await page.goto("http://localhost:3001/login", { waitUntil: "networkidle" });
  await page.getByPlaceholder("Enter your email or mobile number").fill(email);
  await page.getByPlaceholder("Enter your password").fill(password);
  await page.getByRole("button", { name: /Sign in/ }).click();
  await page.waitForURL(url => url.pathname !== "/login", { timeout: 30_000 });
  // The product tour is valid for first-time users, but it obscures the
  // page under test. This is a documented product flag, not DOM removal.
  await page.evaluate(() => localStorage.setItem("serviceos-tenant-tour-done", "true"));

  for (let i = 0; i < selectedPages.length; i += 1) {
    const spec = selectedPages[i];
    currentPageKey = spec.key;
    await page.goto(`http://localhost:3001${spec.route}`, { waitUntil: "domcontentloaded" });
    const heading = page.getByRole("heading", { level: 1, name: spec.heading });
    await heading.waitFor({ timeout: 30_000 });
    await page.waitForLoadState("networkidle").catch(() => {});
    await page.waitForTimeout(300);
    const featureVisibility = {};
    for (const feature of spec.features) {
      featureVisibility[feature] = await page.getByText(feature, { exact: false }).first().isVisible().catch(() => false);
    }
    const accessibility = await new AxeBuilder({ page }).analyze();
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
    const filename = `reference-${phase}-${String(i + 1).padStart(2, "0")}-${spec.key}.png`;
    await page.screenshot({ path: path.join(auditDir, filename), fullPage: true });
    results.pages.push({
      key: spec.key,
      route: spec.route,
      final_pathname: new URL(page.url()).pathname,
      features: featureVisibility,
      axe_violations: accessibility.violations.map(v => ({
        id: v.id,
        impact: v.impact,
        nodes: v.nodes.length,
        targets: v.nodes.map(node => node.target),
      })),
      horizontal_overflow: overflow,
      screenshot: filename,
    });
  }
  results.passed = results.pages.every(item =>
    item.final_pathname === selectedPages.find(spec => spec.key === item.key).route
    && Object.values(item.features).every(Boolean)
    && !item.horizontal_overflow)
    && results.failed_responses.length === 0
    && results.console_errors.length === 0;
} catch (error) {
  results.passed = false;
  results.error = error instanceof Error ? error.stack : String(error);
  throw error;
} finally {
  results.finished_at = new Date().toISOString();
  await writeFile(path.join(auditDir, `reference-${phase}-results.json`), JSON.stringify(results, null, 2));
  await browser.close();
}
