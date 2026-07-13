// MODULE-L5-00: bounded, source-derived zero-unknown guard.
// Fails when the real, current repository disagrees with the committed
// module/application inventory -- i.e. detects registry drift, per Part 38
// and Part 39 of the MODULE-L5-00 mission.
//
// This is intentionally scoped to what an inventory gate can mechanically
// check: application directory presence, and the module registry's own
// UNKNOWN count. It does not (and cannot, at this gate) verify deep
// per-module layer completeness -- that is explicitly future scope.
const fs = require("fs");
const path = require("path");
const { execSync } = require("child_process");

const ROOT = path.join(__dirname, "..");

const EXPECTED_APPLICATIONS = [
  { id: "super_admin", path: "frontend/super-admin" },
  { id: "tenant_portal", path: "frontend/tenant-portal" },
  { id: "customer_app_web", path: "frontend/customer-app" },
  { id: "customer_app_mobile", path: "mobile/customer-app" },
  { id: "staff_app_mobile", path: "mobile/staff-app" },
];

function fail(reason, extra) {
  console.log(JSON.stringify({ result: "MODULE_ZERO_UNKNOWN_GUARD_FAILED", reason, ...extra }, null, 2));
  process.exit(1);
}

function main() {
  const findings = [];

  // 1. Every expected application directory must still exist.
  for (const app of EXPECTED_APPLICATIONS) {
    if (!fs.existsSync(path.join(ROOT, app.path))) {
      findings.push({ severity: "CRITICAL", area: "application", reason: `expected application '${app.id}' not found at ${app.path}` });
    }
  }

  // 2. No new top-level application directory should appear under
  // frontend/ or mobile/ without being added to EXPECTED_APPLICATIONS.
  for (const base of ["frontend", "mobile"]) {
    const baseDir = path.join(ROOT, base);
    if (!fs.existsSync(baseDir)) continue;
    const found = fs.readdirSync(baseDir, { withFileTypes: true })
      .filter(d => d.isDirectory())
      .map(d => `${base}/${d.name}`);
    for (const dir of found) {
      if (dir === "frontend/e2e-admin-tenant") continue; // known test harness, not a product app
      const known = EXPECTED_APPLICATIONS.some(app => app.path === dir);
      if (!known) {
        findings.push({ severity: "HIGH", area: "application", reason: `undocumented application directory found: ${dir} -- add to the application registry or this guard's EXPECTED_APPLICATIONS list` });
      }
    }
  }

  // 3. Re-run the module inventory scanner and check its own unknown count.
  let registryJson;
  try {
    execSync(`python "${path.join(__dirname, "module_inventory_scan.py")}"`, { cwd: ROOT, stdio: "pipe" });
    registryJson = JSON.parse(fs.readFileSync(path.join(ROOT, "docs", "module-l5", "03-module-registry.json"), "utf8"));
  } catch (e) {
    fail(`module inventory scanner failed to run: ${e.message}`);
    return;
  }

  const unknown = registryJson.summary.unknown_modules || [];
  // vertical_billing is a manually-investigated, documented exception
  // (confirmed dead scaffold, not an active module -- see 30-gap-register.md
  // MODULE-L5-00-002). Any OTHER unknown module is a real, unexplained gap.
  const documentedExceptions = new Set(["vertical_billing"]);
  const trulyUnknown = unknown.filter(m => !documentedExceptions.has(m));
  if (trulyUnknown.length > 0) {
    findings.push({ severity: "CRITICAL", area: "module", reason: `undocumented UNKNOWN modules: ${trulyUnknown.join(", ")}` });
  }

  const result = {
    applications_checked: EXPECTED_APPLICATIONS.length,
    modules_scanned: registryJson.summary.total_modules,
    modules_unknown_raw: unknown,
    modules_unknown_documented_exceptions: [...documentedExceptions],
    modules_unknown_undocumented: trulyUnknown,
    findings,
    result: findings.length === 0 ? "MODULE_ZERO_UNKNOWN_GUARD_PASSED" : "MODULE_ZERO_UNKNOWN_GUARD_FAILED",
  };
  console.log(JSON.stringify(result, null, 2));
  process.exit(findings.length === 0 ? 0 : 1);
}

main();
