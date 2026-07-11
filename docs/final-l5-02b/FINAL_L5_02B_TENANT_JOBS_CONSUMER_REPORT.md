# FINAL-L5-02B — Tenant Jobs Frontend Consumer Scan

`grep -rn "jobsApi\." frontend/tenant-portal/{app,components,hooks}` before this sprint's fix:

| Path | Function/component | Current endpoint (before) | Canonical replacement | Migration status |
|---|---|---|---|---|
| `app/(tenant)/jobs/page.tsx` | `JobsPage` | `serviceJobsApi.list` (already migrated FINAL-L5-01D) | n/a | Already done |
| `app/(tenant)/jobs/[id]/page.tsx` | `JobDetailPage` | `serviceJobsApi.get` + `serviceJobAssignmentApi.*` (already migrated FINAL-L5-01D) | n/a | Already done |
| `components/dashboard/HomeServiceDashboard.tsx` | `HomeServiceDashboard` | `jobsApi.list({limit:"8"})`, `jobsApi.slaAlerts()` | `serviceJobsApi.list({limit:8})`; SLA widget replaced with "Unassigned Jobs" (no canonical SLA equivalent exists) | **Migrated this sprint** |
| `app/(tenant)/staff/[id]/page.tsx` | `StaffDetailPage` | `jobsApi.list({limit:"20"})` filtered client-side by `assigned_staff_id` | `serviceJobsApi.list({limit:20})`, same client-side filter pattern preserved | **Migrated this sprint** |

No hooks, query modules, server actions, tests, or fixtures reference `jobsApi` in `tenant-portal` — the consumer surface was exactly these 4 page/component files, 2 already fixed, 2 fixed this sprint.

Post-fix scan (`grep -rln "jobsApi\." frontend/tenant-portal/{app,components,hooks}`): **0 matches.**

super-admin's `jobsApi` (a separately-defined module in `frontend/super-admin/lib/api.ts`, distinct file from tenant-portal's) is out of this mission's scope — see Legacy Deprecation Report.
