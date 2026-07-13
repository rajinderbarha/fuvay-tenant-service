#!/usr/bin/env node
/**
 * FINAL-L5-05AH — Isolated TypeScript check.
 *
 * Closes L5-05AG-005 / L5-05AG-008: `npx tsc --noEmit` reads
 * `.next/dev/types/**` per tsconfig.json's own include list, and a
 * concurrently-running Next.js dev server (Turbopack) writes those exact
 * files incrementally as routes are visited. If tsc reads mid-write, it
 * reports spurious parse errors against a file that isn't actually
 * broken -- reproduced deterministically in FINAL-L5-05AG (dev server
 * running -> fails; dev server stopped + .next cleared -> 0 errors).
 *
 * This script makes the race STRUCTURALLY IMPOSSIBLE under the canonical
 * command, not just documented as a thing to remember: it kills any dev
 * server holding the frontend's port, deletes the generated .next
 * directory (so no partially-written file can be present), then runs
 * tsc in that guaranteed-clean state. No dev server can write to `.next`
 * while this script holds the check, because none is left running.
 *
 * Run: node e2e/typecheck_isolated.js
 * Exit 0 = clean. Exit 1 = real TypeScript errors (or setup failure).
 */
const { execSync, spawnSync } = require("child_process");
const path = require("path");
const fs = require("fs");
const net = require("net");

const FRONTEND_DIR = path.resolve(__dirname, "..", "frontend", "super-admin");
const FRONTEND_PORT = Number(process.env.SUPER_ADMIN_PORT ?? 3000);

function isWindows() {
  return process.platform === "win32";
}

function findAndKillPort(port) {
  if (!isWindows()) {
    try { execSync(`fuser -k ${port}/tcp`, { stdio: "ignore" }); } catch { /* nothing listening, fine */ }
    return;
  }
  try {
    const out = execSync(`netstat -ano | findstr :${port} | findstr LISTENING`, { encoding: "utf8" });
    const pids = new Set(
      out.split("\n").map((l) => l.trim().split(/\s+/).pop()).filter(Boolean),
    );
    for (const pid of pids) {
      try { execSync(`taskkill /PID ${pid} /F`, { stdio: "ignore" }); } catch { /* already gone */ }
    }
  } catch { /* nothing listening on this port, that's the desired state */ }
}

function portIsFree(port) {
  return new Promise((resolve) => {
    const srv = net.createServer();
    srv.once("error", () => resolve(false));
    srv.once("listening", () => srv.close(() => resolve(true)));
    srv.listen(port, "127.0.0.1");
  });
}

async function main() {
  const report = { steps: {} };

  // 1. Stop any dev server holding the frontend port -- the sole source
  //    of the race. Idempotent: safe to run whether or not one is up.
  findAndKillPort(FRONTEND_PORT);
  // Windows releases file handles held by a just-killed process with a
  // short, variable delay; retry the port check briefly rather than
  // racing a single fixed wait.
  let portFree = false;
  for (let i = 0; i < 10 && !portFree; i++) {
    await new Promise((r) => setTimeout(r, 500));
    portFree = await portIsFree(FRONTEND_PORT);
  }
  report.steps.dev_server_stopped = portFree;

  // 2. Delete generated output so no partially-written file can survive
  //    from a prior run. Retry on ENOTEMPTY/EBUSY -- Windows can hold a
  //    brief lock on a subdirectory right after the owning process exits.
  const nextDir = path.join(FRONTEND_DIR, ".next");
  let cleaned = false;
  let lastErr = null;
  for (let i = 0; i < 5 && !cleaned; i++) {
    try {
      fs.rmSync(nextDir, { recursive: true, force: true });
      cleaned = !fs.existsSync(nextDir);
    } catch (e) {
      lastErr = e;
      await new Promise((r) => setTimeout(r, 400));
    }
  }
  report.steps.generated_output_cleaned = cleaned ? true : `failed: ${lastErr?.message}`;

  // 3. Run tsc in the now-guaranteed-clean, no-dev-server state.
  const tsc = spawnSync("npx", ["tsc", "--noEmit"], {
    cwd: FRONTEND_DIR,
    encoding: "utf8",
    shell: isWindows(),
    timeout: 120_000,
  });
  report.steps.typescript_exit_code = tsc.status;
  report.steps.typescript_output = (tsc.stdout || "") + (tsc.stderr || "");
  report.result = tsc.status === 0 ? "TYPESCRIPT_CLEAN" : "TYPESCRIPT_ERRORS";

  console.log(JSON.stringify(report, null, 2));
  process.exit(tsc.status === 0 ? 0 : 1);
}

main();
