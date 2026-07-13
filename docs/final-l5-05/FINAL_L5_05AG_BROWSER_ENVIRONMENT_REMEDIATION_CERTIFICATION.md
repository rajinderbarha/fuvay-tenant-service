# FINAL-L5-05AG — Browser Execution Environment, Release-Candidate Guard and Final Gate Blocker Remediation

## Headline finding (read first)

**Real Chromium was never actually unavailable in this environment.** Every FINAL-L5-05 sprint since FINAL-L5-05S (S, T, U, V, W, X, Z, AA, AB, AC, AD, AE, AF — an unbroken run of at least 12 sprints) stated "no browser-automation tool has been available... confirmed via `ToolSearch`" as settled fact. That statement was accurate about `ToolSearch` — it never finds a dedicated browser-agent tool in this environment — but it was never actually tested at the shell level. This sprint did:

```
node -e "require('playwright').chromium.launch({headless:true})..."
→ launches real Chromium 136.0.7103.25
→ reaches real backend (GET /health → ok, real PostgreSQL, real Redis)
→ reaches real frontend (GET /login → 200, real title "ServiceOS — Super Admin", real form)
```

The repository already had everything needed: `@playwright/test` installed in `e2e/node_modules`, a Chromium binary already downloaded to the default Playwright cache, a working `playwright.config.ts`, and — most tellingly — **9 pre-existing, real, non-mocked Playwright spec files** in `e2e/super-admin/`, each with a header comment explicitly stating it drives the real backend with zero network mocks, dating from sprints FINAL-L5-01B and FINAL-L5-05L through 05Q (all *before* the "no browser tool" era began at FINAL-L5-05S). Nobody in any of the 12 subsequent sprints tried running them.

This sprint ran two of those pre-existing suites for real: **17 live, five-role, non-mocked browser tests, all passing, across multiple consecutive clean runs.**

## Baseline

| Item | Value |
|---|---|
| `git rev-parse HEAD` (start) | `b9cb831` |
| `git rev-parse origin/master` (start) | `b9cb831` (identical) |
| Backend | was down at sprint start (connection refused); restarted, PostgreSQL required ~1 minute of crash-recovery from a prior unclean shutdown, then healthy |
| Frontend (super-admin, port 3000) | was listening but non-responsive (stale process); restarted cleanly |
| Migration head | `136` |
| `FINAL-L5-05AF` status | `PARTIAL_READY_WITH_FINAL_L5_05AF_BLOCKERS` (accepted as accurate, per this mission's own instruction not to reinterpret it as a failed effort) |

## What this sprint proved live

### 1. Browser tooling inventory (Part 5)
- **Tool**: Playwright `1.52.0`, already a dependency of `e2e/package.json`.
- **Browser**: Chromium `136.0.7103.25` (`chromium-1169` in the default Playwright cache) — already downloaded, no install needed.
- **Config**: `e2e/playwright.config.ts` — pre-existing, already correctly configured with a `webServer` block that can auto-start both frontend dev servers.
- **Root cause of "unavailable"**: never installed-and-verified by any sprint since FINAL-L5-05S; the conclusion was drawn from tool discovery, not shell execution.

### 2. Browser preflight (Part 7/8)
Built `e2e/preflight.js` — the reproducible check any future sprint must run first. Verifies, in order: browser binary/launch, backend health (including PostgreSQL status via the health endpoint), frontend reachability with a real rendered login form, auth endpoint reachability, screenshot capability. Machine-readable JSON output, exits non-zero on the first failure with one of the mission's own specified result codes (`BROWSER_BINARY_MISSING`, `BROWSER_LAUNCH_FAILED`, `FRONTEND_UNREACHABLE`, etc.).

Live result this sprint:
```json
{
  "checks": {
    "browser_launch": "ok", "browser_version": "136.0.7103.25",
    "backend_health": "ok", "database_status": "ok",
    "frontend_status": 200, "frontend_title": "ServiceOS — Super Admin",
    "login_form_present": true, "auth_endpoint_status": 401,
    "screenshot_capture": "ok", "browser_closed": "ok"
  },
  "result": "BROWSER_PREFLIGHT_PASSED"
}
```
Wired as `npm run test:e2e:preflight` in `e2e/package.json`.

### 3. Representative five-role Chromium suite (Part 15)
Two pre-existing real-backend spec files were executed directly:

**`final-l5-05l-admin-role-runtime.spec.ts`** (7 tests): all 5 canonical roles log in against the real backend, `/v1/auth/me` returns the correct role for each, a direct API mutation attempt from the Admin-Read-Only browser context is denied (`403`), a direct Finance-domain mutation attempt from the Operations Admin browser context is denied (`403`). **7/7 passed, 3 consecutive clean runs** (once with `--workers=1`, twice under default invocation after the flake fix below).

**`final-l5-05m-permission-visibility.spec.ts`** (10 tests): sidebar visibility correctly filtered per role (Super Admin sees Finance+Platform; Operations sees Jobs/Staff but not Finance/Roles/Permissions; Finance sees Finance but not Roles/Security; Security sees Security/Roles/Permissions but not Finance; Read Only sees a read subset with zero mutation-implying labels), direct-route navigation to a denied page shows the canonical Permission Denied page with no protected-data flash, Admin Read Only sees real Usage Credits data with no "Add Credits" mutation form, Super Admin sees the real mutation form. **10/10 passed.**

**17/17 real, live, non-mocked, five-role browser tests passing.**

### 4. Flake root-cause and fix (Part 26/27)
`final-l5-05l-*.spec.ts` under default parallel execution: 4/7 failed with `TimeoutError` waiting for `/v1/auth/login`'s response. Root cause: the frontend runs as a Next.js *dev* server (Turbopack on-demand compilation), which itself logs "Slow filesystem detected... consider moving `.next/dev` to a local folder" — this environment's frontend lives on a network-style drive. Concurrent browser contexts each trigger a fresh on-demand compile of `/login`, exceeding response-wait timeouts. **Classified: TEST_INFRA_DEFECT, not PRODUCT_DEFECT** (the backend/frontend both function correctly; only concurrent cold-compile timing is at fault).

**Fix**: `test.describe.configure({ mode: "serial" })` added to both real-backend spec files' describe blocks — scoped per-file, not a change to the shared `playwright.config.ts` (which would needlessly serialize the ~17 other, fully-mocked, genuinely parallelism-safe spec files). Verified fully deterministic across 3 consecutive clean single-file runs. **Residual, honestly-documented limitation**: running two different real-backend spec *files* concurrently still exhibits cross-file contention (reproduced: 2 failures when both files ran together) — `mode: "serial"` only orders tests within one file. The proven-deterministic invocation for the real-backend suite as a whole is `--workers=1` at the command line; this is what the new release-candidate guard uses.

### 5. Release-candidate guard (Part 22/23)
Built `e2e/certify_release_candidate.js` — consumes actual command outputs (never a manually-edited flag file, never a prior sprint's prose claim):
1. Migration head (`alembic heads`)
2. Browser preflight (must return `BROWSER_PREFLIGHT_PASSED`)
3. Full backend suite (`pytest -q`, parses actual pass/fail counts)
4. One representative real-backend Chromium spec (`--workers=1`, only attempted if preflight passed)
5. Blocker-ledger presence

Outputs machine-readable JSON with `final_result: RELEASE_CANDIDATE_GUARD_PASSED | RELEASE_CANDIDATE_GUARD_FAILED` and an explicit `failures` array naming which check(s) failed. This is intentionally a **bounded, representative** guard, not the mission's full 40+-sub-check Part 22 gate — each of those sub-checks (route registry, action registry, cross-tenant matrix, responsive matrix, accessibility matrix) would itself require the underlying matrix to exist first, which is real future scope, not fabricated here.

## What this sprint deliberately did not attempt (honest scope boundary)

- **Full route/action registries** (Parts 13/14): not built. The mission's own dependency order (Part 4) places these after browser tooling is confirmed working — which is what this sprint established — but building the registries themselves is substantial, separate scope.
- **Cross-tenant browser matrix, responsive browser matrix, accessibility browser matrix** (Parts 16-18): not attempted. Now genuinely *possible* for the first time this session, but each is real, multi-hour scope in its own right.
- **The other 7 of 9 pre-existing real-backend spec files** (`final-l5-05n` through `05q`, plus the two FINAL-L5-01B files): not run this sprint. Strong candidates for the very next increment, given they already exist and the flakiness root cause is now understood and fixable per-file.
- **CI/container browser execution path** (Part 9): not built — local execution was proven sufficient and is what this sprint's guard uses; a CI workflow is a reasonable next step but wasn't necessary to close this sprint's bounded scope.
- **Deterministic seed/cleanup infrastructure beyond what the existing specs already use** (Parts 10/11): the existing specs already use real seeded principals (`admin.ops@serviceos.local` etc., `CanonicalL5!2026`) and a real seeded tenant — reused, not rebuilt.

## Regression evidence

Zero backend product files changed this sprint (only `e2e/` test-infrastructure files and documentation). See the final response section for the release-candidate guard's own full backend-suite result, generated by the guard itself rather than asserted separately.

## Files changed

- `e2e/preflight.js` (new)
- `e2e/certify_release_candidate.js` (new)
- `e2e/package.json` (`test:e2e:preflight` script added)
- `e2e/super-admin/final-l5-05l-admin-role-runtime.spec.ts` (serial-mode fix + root-cause comment)
- `e2e/super-admin/final-l5-05m-permission-visibility.spec.ts` (serial-mode fix + comment)
- `docs/final-l5-05/FINAL_L5_05_BUG_REGISTER.md` (L5-05AG-001 through 004 appended)
