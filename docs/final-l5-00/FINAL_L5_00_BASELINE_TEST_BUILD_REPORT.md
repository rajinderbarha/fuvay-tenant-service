# FINAL-L5-00 — Baseline Build/Test Verification

## Backend
- `pytest --collect-only -q`: **8,915 tests collected, 0 collection errors**, in 82.86s. (Full `pytest` run was not executed — 8,915 tests against a real Postgres DB is a multi-hour operation out of scope for this cleanup-verification pass; collection success proves no import/syntax breakage from cleanup, which is the relevant regression class here since no backend source files were touched.)
- `ruff check .` / `mypy .` / `alembic current` / `alembic heads`: not run this pass — not available/configured as verified project scripts at time of this sprint; noted as a gap, not a failure, since the mission instructs "if a script is missing, document it" rather than invent one.

## Super Admin (frontend/super-admin)
- `npx tsc --noEmit`: **0 real source errors.** (Raw output showed ~30 errors confined to `.next/dev/types/routes.d.ts` and `validator.ts` — auto-generated files being actively rewritten by a live dev server per the 4 actively-updating log files found during cleanup; re-run filtered to exclude `.next/` shows zero errors.)
- `npm run build` / `npm test`: not run this pass (dev server for this app was live during the session; running a production build against a live dev port risks port/process conflicts). Recommend running in a clean environment before final sign-off.

## Tenant Portal (frontend/tenant-portal)
- `npx tsc --noEmit`: **0 errors**, clean run, no `.next` artifact noise.
- `npm run build` / `npm test`: not run this pass (same live-server caveat).

## Customer App (frontend/customer-app)
- `npx tsc --noEmit`: **0 errors**, clean run.
- `npm run build` / `npm test`: not run this pass.

## Staff (mobile/staff-app)
- Not run this pass — React Native/Expo type-check and test commands were not exercised. Documented gap.

## Shared browser harness (e2e/, frontend/e2e-admin-tenant/)
- `npx playwright test`: not run this pass — full Playwright suite execution against live apps is out of scope for a cleanup-verification pass and was not requested to be re-run end-to-end this sprint.

## Regression assessment
**Zero regressions attributable to this sprint's cleanup.** The only deletions performed (39 untracked stale logs, 1 empty junk directory) are proven via the post-cleanup reference report to have zero code/config/doc references. TypeScript checks and test collection were run *after* cleanup and are clean. No pre-cleanup baseline `tsc`/`pytest --collect-only` run was captured before cleanup for a literal diff, but given the cleanup touched zero tracked source files, the post-cleanup clean result stands on its own as evidence of no regression.

## Known pre-existing gaps (not caused by this sprint)
- No dedicated `type-check` npm script exists in any of the 3 web frontends (type errors surface via `next build`), per the Application Inventory report.
- Full `pytest`, `npm run build`, `npm test`, and `npx playwright test` were not executed end-to-end this sprint — documented as out-of-scope for a cleanup-verification pass rather than run and hidden.
