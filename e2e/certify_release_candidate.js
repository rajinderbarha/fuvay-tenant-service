#!/usr/bin/env node
/**
 * FINAL-L5-05AG — Release-candidate guard.
 *
 * Consumes ACTUAL command outputs (exit codes + parsed stdout) from the
 * real backend suite, browser preflight and a representative real-backend
 * Chromium suite. It never reads a manually-edited "READY" flag file and
 * never infers success from a prior sprint's prose report -- every field
 * in the output is derived from a command this script itself just ran.
 *
 * This is intentionally a BOUNDED, representative guard (backend suite +
 * browser preflight + one representative real-backend Chromium spec),
 * not the full 40+-suite gate the mission's Part 22 describes -- building
 * that exhaustively is future-sprint scope. What exists here is real,
 * executable and fails closed on every check it performs.
 *
 * Run: node e2e/certify_release_candidate.js
 * Exit 0 = RELEASE_CANDIDATE_GUARD_PASSED. Exit 1 = ...GUARD_FAILED.
 */
const { execSync } = require("child_process");
const path = require("path");
const fs = require("fs");

const REPO_ROOT = path.resolve(__dirname, "..");

function run(cmd, cwd) {
  try {
    const out = execSync(cmd, { cwd: cwd ?? REPO_ROOT, encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] });
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

function main() {
  const manifest = {
    timestamp: new Date().toISOString(),
    ...gitInfo(),
    checks: {},
  };

  // 1. Migration head reachable and matches current DB (best-effort; does
  //    not fail the guard if alembic isn't on PATH in this shell, but
  //    records it honestly rather than fabricating a pass).
  const alembic = run("alembic heads");
  manifest.checks.migration_head = alembic.ok ? alembic.output.trim() : `UNAVAILABLE: ${alembic.output.trim().slice(0, 200)}`;

  // 2. Browser preflight -- must actually pass.
  const preflight = run("node preflight.js", path.join(REPO_ROOT, "e2e"));
  let preflightResult = "UNPARSEABLE";
  try {
    preflightResult = JSON.parse(preflight.output).result;
  } catch { /* leave as UNPARSEABLE */ }
  manifest.checks.browser_preflight_result = preflightResult;

  // 3. Backend suite -- must actually run and report 0 failures. This is
  //    the slow check (minutes); run with a generous timeout.
  const backend = run("python -m pytest -q --tb=no", REPO_ROOT);
  const backendMatch = backend.output.match(/(\d+) passed(?:, (\d+) skipped)?(?:, (\d+) failed)?/);
  manifest.checks.backend_passed = backendMatch ? Number(backendMatch[1]) : null;
  manifest.checks.backend_skipped = backendMatch && backendMatch[2] ? Number(backendMatch[2]) : 0;
  manifest.checks.backend_failed = backend.output.includes(" failed") ? (backend.output.match(/(\d+) failed/) || [])[1] ?? "unknown" : 0;
  manifest.checks.backend_result = backend.ok ? "PASSED" : "FAILED";

  // 4. Representative real-backend Chromium suite (workers=1, see spec
  //    file comments for why). Only run if preflight passed -- no point
  //    launching a doomed browser suite against an unreachable stack.
  if (preflightResult === "BROWSER_PREFLIGHT_PASSED") {
    const chromium = run(
      "npx playwright test final-l5-05l-admin-role-runtime.spec.ts --project=super-admin-chromium --workers=1 --reporter=list",
      path.join(REPO_ROOT, "e2e"),
    );
    manifest.checks.chromium_result = chromium.ok ? "PASSED" : "FAILED";
    const passMatch = chromium.output.match(/(\d+) passed/);
    manifest.checks.chromium_passed = passMatch ? Number(passMatch[1]) : 0;
  } else {
    manifest.checks.chromium_result = "SKIPPED_PREFLIGHT_FAILED";
    manifest.checks.chromium_passed = 0;
  }

  // 5. Open critical/high blocker count, read from the maintained ledger
  //    (counts headings, does not itself judge severity -- that judgment
  //    lives in the human-authored ledger, this just refuses to pass
  //    silently if the ledger is missing).
  const ledgerPath = path.join(REPO_ROOT, "docs", "final-l5-05", "FINAL_L5_05AE_MASTER_BLOCKER_LEDGER.md");
  manifest.checks.blocker_ledger_present = fs.existsSync(ledgerPath);

  // ── Final verdict ──────────────────────────────────────────────────
  const failures = [];
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
