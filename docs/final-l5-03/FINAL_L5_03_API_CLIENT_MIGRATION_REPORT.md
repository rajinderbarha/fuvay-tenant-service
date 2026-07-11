# FINAL-L5-03 — API Client Migration Report

## Migrated this sprint

| File | Before | After |
|---|---|---|
| `super-admin/app/admin/audit-logs/page.tsx` | Hand-rolled `fetch()` + manual token read + `new Error(json?.error?.message)` | `apiFetchPaginatedRaw(endpoint, params)` (new shared helper in `lib/api.ts`) |
| `super-admin/app/admin/refund-requests/page.tsx` | Same pattern | Same fix |
| `super-admin/app/admin/payments/page.tsx` | Same pattern | Same fix |
| `super-admin/app/admin/commission-records/page.tsx` | Same pattern | Same fix |
| `super-admin/app/admin/home-services/service-jobs/page.tsx` | Same pattern | Same fix |
| `tenant-portal/app/login/page.tsx` | Raw `fetch()` to `/v1/tenant/dashboard/runtime` with manually-attached `Authorization` header | `categoryDashboardApi.getRuntime()` |

## New shared helper
`apiFetchPaginatedRaw(endpoint, params)` added to `super-admin/lib/api.ts` — wraps the existing private `apiFetch<T>()`, so all 5 migrated pages now inherit: centralized auth header injection, the 401→refresh→retry flow (previously **absent** on all 5 — an admin whose token expired mid-session on these pages got a raw, unhelpful error instead of a clean re-login prompt), and `request_id` preservation on errors (previously **discarded** on all 5, violating rule 12).

## Why these 5 existed
All 5 are `EnterpriseDataGrid`-driven pages needing a generic `fetchFn(params) => paginatedData` shape. No prior shared "generic paginated fetch" helper existed, so each page's author independently hand-rolled the same ~10 lines. This is exactly the "duplicated apiFetch" / "duplicated token parsing" pattern the mission's Part 1 inventory explicitly asks to find.

## Type-safety side effect
`GridData`/`GridParams` (previously private interfaces in `EnterpriseDataGrid.tsx`) were exported so the 5 migrated pages could type their return values correctly — the old raw-`fetch()`+`.json()` pattern was implicitly `any`-typed, silently bypassing TypeScript's structural checks entirely. Making the transport typed surfaced 6 real type errors (now fixed) that TypeScript had never been able to see before.

## Verification
- `npx tsc --noEmit` (super-admin): 0 errors, verified after migration.
- `npm run build` (super-admin): succeeds, all 5 pages present in the route manifest.
- Real Chromium regression: `final-l5-03-cross-app-regression.spec.ts` navigates to `/admin/audit-logs` and `/admin/finance/usage-credits` (a 6th, separately-fixed page) and confirms real data renders, 0 new console errors.

## Result
No `NOT_READY_FINAL_L5_03_API_CLIENT_FAILED`.
