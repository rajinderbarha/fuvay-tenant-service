#!/usr/bin/env node
/**
 * FINAL-L5-05AH — Release-candidate guard (safe execution order).
 *
 * Consumes ACTUAL command outputs (exit codes + parsed stdout) from the
 * real backend suite, an isolated TypeScript check, browser preflight and
 * representative real-backend Chromium suites. It never reads a
 * manually-edited "READY" flag file and never infers success from a
 * prior sprint's prose report -- every field in the output is derived
 * from a command this script itself just ran.
 *
 * FINAL-L5-05AH closes L5-05AG-008: TypeScript now runs via
 * `typecheck_isolated.js`, which kills any dev server on the frontend
 * port and deletes generated output BEFORE invoking tsc -- the race
 * between tsc and a dev server writing `.next/dev/types/**` is
 * structurally impossible under this script's own execution order,
 * not merely documented as a thing to remember. The frontend dev server
 * needed by the later browser steps is started fresh AFTER the
 * TypeScript check completes, per the mission's required safe order:
 *
 *   1. TypeScript (isolated -- no dev server running)
 *   2. Production build
 *   3. Start dev server for the browser steps that need it
 *   4. Browser preflight
 *   5. Backend suite
 *   6. Representative Chromium suites
 *   7. Blocker-ledger presence
 *
 * This is intentionally a BOUNDED, representative guard (backend suite +
 * isolated TypeScript + browser preflight + 3 representative real-backend
 * Chromium specs), not the full 40+-suite gate the mission's Part 22-36
 * describe -- building that exhaustively (full route/action registries,
 * cross-tenant/responsive/accessibility Chromium matrices) is real,
 * substantial future scope. What exists here is real, executable and
 * fails closed on every check it performs.
 *
 * Run: node e2e/certify_release_candidate.js
 * Exit 0 = RELEASE_CANDIDATE_GUARD_PASSED. Exit 1 = ...GUARD_FAILED.
 */
const { execSync, spawn } = require("child_process");
const path = require("path");
const fs = require("fs");
const http = require("http");

const REPO_ROOT = path.resolve(__dirname, "..");
const FRONTEND_DIR = path.join(REPO_ROOT, "frontend", "super-admin");
const FRONTEND_PORT = 3000;

function run(cmd, cwd, timeoutMs) {
  try {
    const out = execSync(cmd, { cwd: cwd ?? REPO_ROOT, encoding: "utf8", stdio: ["ignore", "pipe", "pipe"], timeout: timeoutMs });
    return { ok: true, output: out };
  } catch (e) {
    return { ok: false, output: (e.stdout ?? "") + (e.stderr ?? ""), code: e.status };
  }
}

function gitInfo() {
  const commit = run("git rev-parse HEAD").output.trim();
  const branch = run("git rev-parse --abbrev-ref HEAD").output.trim();
  return { commit, branch };
}

function httpOk(url, timeoutMs = 2000) {
  return new Promise((resolve) => {
    const req = http.get(url, { timeout: timeoutMs }, (res) => { res.resume(); resolve(res.statusCode < 500); });
    req.on("error", () => resolve(false));
    req.on("timeout", () => { req.destroy(); resolve(false); });
  });
}

async function ensureFrontendRunning(maxWaitMs = 120_000) {
  if (await httpOk(`http://localhost:${FRONTEND_PORT}/login`)) return "already_running";
  const child = spawn("npm", ["run", "dev"], {
    cwd: FRONTEND_DIR, detached: true, stdio: "ignore", shell: true,
  });
  child.unref();
  const start = Date.now();
  while (Date.now() - start < maxWaitMs) {
    if (await httpOk(`http://localhost:${FRONTEND_PORT}/login`)) return "started_fresh";
    await new Promise((r) => setTimeout(r, 3000));
  }
  return "failed_to_start";
}

async function main() {
  const manifest = {
    timestamp: new Date().toISOString(),
    ...gitInfo(),
    checks: {},
  };

  // 1. Migration head.
  const alembic = run("alembic heads");
  manifest.checks.migration_head = alembic.ok ? alembic.output.trim() : `UNAVAILABLE: ${alembic.output.trim().slice(0, 200)}`;

  // 2. Isolated TypeScript check -- MUST run before any dev server is
  //    started by this script (structural fix for the tsc/dev-server race).
  const tsc = run("node typecheck_isolated.js", path.join(REPO_ROOT, "e2e"), 150_000);
  let tscReport = null;
  try { tscReport = JSON.parse(tsc.output); } catch { /* leave null */ }
  manifest.checks.typescript_result = tscReport?.result ?? "UNPARSEABLE";

  // 3. Production build (also runs with no dev server active, avoiding
  //    any similar generated-output collision).
  // FINAL-L5-05AH: 300s was measured too short on this environment's
  // slow (network-drive) filesystem -- static generation for 133 pages
  // alone can exceed 5 minutes, causing execSync's timeout to kill the
  // process mid-build and get misread as a build failure rather than a
  // timeout. 900s gives comfortable headroom (a real build failure still
  // fails fast, well under this ceiling).
  const build = run("npm run build", FRONTEND_DIR, 900_000);
  manifest.checks.production_build_result = build.ok ? "PASSED" : "FAILED";

  // 4. Backend suite -- BEFORE the dev server starts. The suite's own
  //    tests/test_p0_engine_management_enterprise.py::test_no_typescript_errors
  //    shells out to `npx tsc --noEmit` itself; if a dev server is
  //    already running when this test executes, it hits the identical
  //    generated-types race `typecheck_isolated.js` was built to prevent
  //    (confirmed: this exact ordering bug caused this guard's own first
  //    full run to report a false backend failure). Running the full
  //    suite here, before step 5 starts any dev server, makes that race
  //    impossible for this embedded test too, not just this script's own
  //    direct TypeScript step.
  const backend = run("python -m pytest -q --tb=no", REPO_ROOT, 900_000);
  const backendMatch = backend.output.match(/(\d+) passed(?:, (\d+) skipped)?(?:, (\d+) failed)?/);
  manifest.checks.backend_passed = backendMatch ? Number(backendMatch[1]) : null;
  manifest.checks.backend_skipped = backendMatch && backendMatch[2] ? Number(backendMatch[2]) : 0;
  manifest.checks.backend_failed = backend.output.includes(" failed") ? (backend.output.match(/(\d+) failed/) || [])[1] ?? "unknown" : 0;
  manifest.checks.backend_result = backend.ok ? "PASSED" : "FAILED";

  // 5. Now start the dev server the remaining browser steps need.
  manifest.checks.frontend_startup = await ensureFrontendRunning();

  // 6. Browser preflight.
  const preflight = run("node preflight.js", path.join(REPO_ROOT, "e2e"));
  let preflightResult = "UNPARSEABLE";
  try { preflightResult = JSON.parse(preflight.output).result; } catch { /* leave as UNPARSEABLE */ }
  manifest.checks.browser_preflight_result = preflightResult;

  // 7. Representative real-backend Chromium suites. FINAL-L5-05AH found
  //    that even at --workers=1, passing MULTIPLE real-backend spec files
  //    to a single `playwright test` invocation is unreliable on this
  //    environment (reproduced: final-l5-05m/05p each pass 100% of the
  //    time run alone, but intermittently fail specific tests -- a
  //    transient 404, a slow-to-render header action -- when combined
  //    into one command, even serially). Each spec is therefore invoked
  //    as its OWN separate `playwright test` process, sequentially --
  //    the only invocation pattern proven reliable across every repeat
  //    run this sprint.
  const REPRESENTATIVE_SPECS = [
    "final-l5-05l-admin-role-runtime.spec.ts",
    "final-l5-05m-permission-visibility.spec.ts",
    "final-l5-05p-tenant-provider-staff.spec.ts",
  ];
  if (preflightResult === "BROWSER_PREFLIGHT_PASSED") {
    let allOk = true;
    let totalPassed = 0;
    const perSpec = {};
    for (const spec of REPRESENTATIVE_SPECS) {
      const result = run(
        `npx playwright test ${spec} --project=super-admin-chromium --workers=1 --reporter=list`,
        path.join(REPO_ROOT, "e2e"),
        300_000,
      );
      const passMatch = result.output.match(/(\d+) passed/);
      const passed = passMatch ? Number(passMatch[1]) : 0;
      perSpec[spec] = { ok: result.ok, passed };
      totalPassed += passed;
      if (!result.ok) allOk = false;
    }
    manifest.checks.chromium_per_spec = perSpec;
    manifest.checks.chromium_result = allOk ? "PASSED" : "FAILED";
    manifest.checks.chromium_passed = totalPassed;
  } else {
    manifest.checks.chromium_result = "SKIPPED_PREFLIGHT_FAILED";
    manifest.checks.chromium_passed = 0;
  }

  // 8. Blocker-ledger presence.
  const ledgerPath = path.join(REPO_ROOT, "docs", "final-l5-05", "FINAL_L5_05AE_MASTER_BLOCKER_LEDGER.md");
  manifest.checks.blocker_ledger_present = fs.existsSync(ledgerPath);

  // ── Final verdict ──────────────────────────────────────────────────
  const failures = [];
  if (manifest.checks.typescript_result !== "TYPESCRIPT_CLEAN") failures.push("typescript");
  if (manifest.checks.production_build_result !== "PASSED") failures.push("production_build");
  if (manifest.checks.browser_preflight_result !== "BROWSER_PREFLIGHT_PASSED") failures.push("browser_preflight");
  if (manifest.checks.backend_result !== "PASSED") failures.push("backend_suite");
  if (Number(manifest.checks.backend_failed) > 0) failures.push("backend_failures_nonzero");
  if (manifest.checks.chromium_result !== "PASSED") failures.push("chromium_suite");
  if (!manifest.checks.blocker_ledger_present) failures.push("blocker_ledger_missing");

  manifest.failures = failures;
  manifest.final_result = failures.length === 0 ? "RELEASE_CANDIDATE_GUARD_PASSED" : "RELEASE_CANDIDATE_GUARD_FAILED";

  console.log(JSON.stringify(manifest, null, 2));
  process.exit(failures.length === 0 ? 0 : 1);
}

main();
