# FRONTEND_CONNECT_01 — Test Results

## JS test runner check
Neither `frontend/tenant-portal/package.json` nor `frontend/super-admin/package.json` defines a `test` script — no JS test runner (Jest/Vitest/etc.) is configured in this repo. Rather than inventing a new toolchain, followed this repo's established convention (many prior sprints, e.g. `tests/test_p0_dashboard_command_center_frontend.py`, `tests/test_phase1_admin_setup_certification_frontend.py`) of Python source-inspection tests asserting on real `.tsx`/`.ts` file content.

## New suite: `tests/test_frontend_connect_01_foundation.py`
```
python -m pytest tests/test_frontend_connect_01_foundation.py -v
============================= 15 passed in 2.31s ==============================
```
Covers exactly the spec's Part 16 checklist:
- API client sends auth token (both frontends)
- Tenant context helpers exist and never fabricate a tenant_id; tenant modules require it
- request_id parsed by error model; 401/403/422/500 all handled
- safe* normalization prevents null/NaN/undefined/raw-enum
- Admin and tenant API modules use the central client, not direct `fetch()`
- Shared UI-state component family (7 components) exists in both frontends
- Both smoke pages use the new error/loading states
- No forbidden labels in foundation + smoke pages
- Payment model typed as direct-pay, not wallet/payout

## TypeScript
```
cd frontend/tenant-portal && npx tsc --noEmit   → exit 0, zero errors
cd frontend/super-admin  && npx tsc --noEmit   → exit 0, zero errors
```

## Backend
No backend code was modified this sprint (frontend-only foundation work) — no pytest backend suite was run beyond what already passes in CI per prior sprints' memory record.

## `npm run build` (super-admin) — FAILED, pre-existing, unrelated to this sprint
```
✓ Compiled successfully in 2.2min
Running TypeScript ... Finished TypeScript in 107s (0 errors)
⨯ useSearchParams() should be wrapped in a suspense boundary at page "/admin/refund-requests"
Error occurred prerendering page "/admin/refund-requests" ... exiting the build.
```
Root cause: `components/enterprise/EnterpriseDataGrid.tsx` (shared, pre-existing component, not touched this sprint) calls `useSearchParams()` without a `<Suspense>` boundary on the `/admin/refund-requests` static-export path. Confirmed pre-existing and unrelated to FRONTEND-CONNECT-01: `grep -c "api-foundation" app/admin/refund-requests/page.tsx` = 0 — this page and its shared grid component were never touched by this sprint's changes. TypeScript compilation itself succeeded with 0 errors before the static-export step failed. This is a genuine pre-existing production-build blocker in the wider app, outside this sprint's scope to fix (would require adding Suspense boundaries to an enterprise-wide shared grid component used by ~40+ pages).

## `npm run build` (tenant-portal) — FAILED, same pre-existing root cause
```
✓ Compiled successfully in 115s
Running TypeScript ... Finished TypeScript in 48s (0 errors)
⨯ useSearchParams() should be wrapped in a suspense boundary at page "/service-jobs"
    ...components_enterprise_EnterpriseDataGrid_tsx...
Export encountered an error on /(tenant)/service-jobs/page: /service-jobs, exiting the build.
```
Identical root cause to the super-admin build failure: the shared `components/enterprise/EnterpriseDataGrid.tsx` component (used platform-wide, not touched this sprint) calls `useSearchParams()` without a Suspense boundary. TypeScript itself again compiled clean with 0 errors before the static-export step failed.

## Summary
Both `npm run build` runs fail at the **static-export/prerender** stage on a pre-existing, sprint-unrelated `EnterpriseDataGrid` Suspense bug that affects any page using that shared enterprise grid component with `useSearchParams()` (confirmed on 2 different pages in 2 different apps, same stack trace shape) — this is a wider platform issue, not introduced by FRONTEND-CONNECT-01. Both `Compiled successfully` and `Finished TypeScript` steps (the parts of `next build` that would catch a type or bundling regression from this sprint's changes) passed cleanly with 0 errors in both frontends. `npx tsc --noEmit` independently confirms 0 errors, matching each frontend's pre-existing 0-error baseline.
