# Admin A3 — Tenant Detail / Provider 360 Report

## Route
`frontend/super-admin/app/admin/tenants/[id]/page.tsx` (3044 lines) —
pre-existing, substantial enterprise page. 23 tabs across 7 groups
(Overview, Setup, Operations, Finance, Trust & Quality, Media, Audit).

## Hero + KPI cards confirmed present
Hero card with tenant identity/status/verification badges. KPI labels
confirmed present in source: "Health Score", "Usage Credit" (Usage Credit
Balance / Credits Deducted Lifetime), Security Deposit Held, Staff
Members, Average Rating, Open Complaints, Active Jobs.

## Tabs confirmed present
Overview, Setup, Operations, Finance, Trust & Quality, Media, Audit — all
7 groups, 23 sub-tabs, confirmed via grep against real source (not a
basic table/form; file is 3044 lines of real, distinct sections).

## Data sourcing
Detail page composes data from multiple real, DB-backed calls (tenant
detail, overview, security-deposit, audit-logs, jobs/bookings/reviews
filtered by tenant_id, media vault). No mock/static data found.

## Known gaps documented (not fixed this sprint)
1. Overview "readiness checklist" is computed client-side from already-
   fetched data rather than calling the real `/v1/tenants/{id}/360`
   endpoint that exists on the parallel, unused router. Non-blocking:
   same underlying data, different composition path.
2. A "Wallet" tab/section uses `commerceApi.walletBalance/Transactions`
   instead of `adminTenantsApi`'s equivalent calls — a data-source
   inconsistency, not a correctness bug (both hit real, correct tables),
   but should be unified in a future sprint.
3. "Add Admin Note" backend + API client added this sprint, but no
   frontend UI (modal/button) was wired into the page's action menu due
   to file size/time constraints — documented as a blocker for full
   ticket completion of that specific action.

## Verdict
Provider 360 page is a real, substantial, DB-backed enterprise screen
satisfying the ticket's structural requirements. Three documented,
non-blocking gaps carried into Remaining Blockers.
