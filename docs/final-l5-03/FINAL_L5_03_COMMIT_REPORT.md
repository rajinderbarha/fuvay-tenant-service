# FINAL-L5-03 — Commit Report

This sprint's changes are kept in one focused commit (the fixes are small, individually verified, and interdependent enough — e.g. the `GridData` export change is required by the `apiFetchPaginatedRaw` migration — that splitting them into the mission's suggested 5 commit groups would create intermediate non-building states). All changes are architecture-cleanup only; no unrelated feature development is included.

## Files changed
**API client / duplicate-code consolidation**
- `frontend/super-admin/lib/api.ts` — added `apiFetchPaginatedRaw`, removed `MOCK_MODE`
- `frontend/super-admin/app/admin/{audit-logs,refund-requests,payments,commission-records,home-services/service-jobs}/page.tsx` — migrated off raw `fetch()`
- `frontend/super-admin/components/enterprise/EnterpriseDataGrid.tsx` — exported `GridData`/`GridParams`
- `frontend/tenant-portal/lib/api.ts` — added `isTenantOwnerRole`, removed `MOCK_MODE`
- `frontend/tenant-portal/app/(tenant)/provider/{status,offerings}/page.tsx` — consumed `isTenantOwnerRole`

**Auth/session cleanup**
- `frontend/super-admin/app/login/page.tsx` — removed `MOCK_MODE` bypass
- `frontend/tenant-portal/app/login/page.tsx` — removed `MOCK_MODE` bypass, migrated runtime fetch to canonical client

**Dead code removal**
- `frontend/super-admin/lib/mock.ts` — deleted (0 consumers, verified)

**Bug fixes (dormant endpoint + hydration)**
- `frontend/tenant-portal/components/layout/TenantLayout.tsx` — migrated dormant `/v1/provider/wallet` call to `usageCreditsApi.getBalance()`
- `frontend/tenant-portal/app/(tenant)/dashboard/page.tsx` — fixed 3 instances of `<Skeleton/>` invalidly nested in `<p>`

**Build fix**
- `frontend/super-admin/app/admin/finance/usage-credits/page.tsx` — added missing `<Suspense>` boundary around `useSearchParams()`

**Test/evidence infrastructure**
- `e2e/tenant-portal/final-l5-03-cross-app-regression.spec.ts` — new real-Chromium regression spec

**Documentation**
- `docs/final-l5-03/*` — all required reports and JSON evidence

## Result
One coherent, fully-verified commit; no mixed unrelated feature work.
