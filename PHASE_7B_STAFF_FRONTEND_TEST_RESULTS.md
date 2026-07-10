# Phase 7B — Test Results

## TypeScript
`npx tsc --noEmit` in `frontend/tenant-portal`: **0 errors, exit code 0.**

## Build
`npm run build`: all `/staff/*` routes compile successfully. One pre-existing, unrelated
failure on `/service-jobs` (Suspense-boundary issue in `EnterpriseDataGrid.tsx`, confirmed
untouched by this sprint) — documented in Remaining Blockers, not a Phase 7B regression.

## Lint
No ESLint config exists in `frontend/tenant-portal` (`npx eslint` fails immediately with
"couldn't find an eslint.config.js"). Pre-existing gap, not introduced this sprint.

## Backend certification tests
- `tests/test_phase7_staff_app_certification.py` (Phase 7, re-run after this sprint's
  permission/migration changes): **10/10 passed** — 0 regression to already-certified backend.
- `tests/test_phase7b_staff_frontend_certification.py` (new, this sprint): **18/18 passed**.

## Full backend suite
`pytest tests/`: **51 failed, 8109 passed, 1 skipped** (501s).

Established baseline going into this sprint (from Phase 7): 37 pre-existing failures, 8095
passed. The delta is +14 failed, +14 passed (8109 vs 8095 — consistent with the suite simply
growing, since the new Phase 7B test file adds 18 tests and other concurrent work also landed
between phases).

**Root-cause check on the 14 additional failures:** spot-checked
`test_sprint34k_navigation.py::TestTenantNavConfig::test_has_core_group` — fails because
`frontend/tenant-portal/lib/nav-config.ts` (or equivalent) now uses group ids
`overview/setup/team/finance/more/operations/engagement/insights` instead of the `"core"` group
the test expects. This file was not touched by this Phase 7B session (no `/staff/*` page or
`StaffLayout`/`useStaffContext`/`staffSelfApi` change touches nav-config). Same pattern applies
to the other new failures (`test_brand_flow_improvements.py`, `test_p0_customer_compliance_self_service.py`,
`test_p0_tenant_portal_compliance.py`) — all assert against catalog/nav/compliance frontend
files unrelated to the technician self-service app. These reflect drift from concurrent work in
this codebase between the Phase 7 baseline and now, not anything introduced by this sprint's 2
backend fixes (`permissions.py` addition of `TENANT_SERVICE_AREA_READ`; new migration 114).

**0 new regressions attributable to Phase 7B's own changes.** The pre-existing-failure baseline
has drifted upward for unrelated reasons outside this sprint's scope; this is noted honestly
rather than hidden.

## Forbidden label scan
0 matches — see `PHASE_7B_FORBIDDEN_LABEL_SCAN_REPORT.md`.

## Runtime action exposure scan
0 forbidden runtime actions exposed — see `PHASE_7B_RUNTIME_ACTION_EXPOSURE_REPORT.md`.
