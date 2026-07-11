# FINAL-L5-01D — Tenant Jobs Frontend Consumer Report

Real `grep` inventory of every `jobsApi.*` call site in `frontend/tenant-portal`.

| Path | Function/component | Current endpoint | Migration status |
|---|---|---|---|
| `app/(tenant)/jobs/page.tsx` | `JobsPage` — main Tenant Jobs list | Was `jobsApi.list()` (`/v1/jobs`) | **MIGRATED** this sprint to `serviceJobsApi.list()` (`/v1/provider/my-records/jobs`) |
| `app/(tenant)/jobs/[id]/page.tsx` | `JobDetailPage` — job detail | Was `jobsApi.get/history` + `quotesApi` + checklist actions | **MIGRATED** this sprint to `serviceJobsApi.get()` + `serviceJobAssignmentApi.{getTimeline,getEligibleStaff,assign,cancelAssignment,schedule}` |
| `app/(tenant)/staff/[id]/page.tsx` | Technician profile page's "recent jobs" widget | `jobsApi.list({limit:"20"})` | **NOT MIGRATED this sprint** — secondary/tangential consumer (a widget on the staff profile page, not the primary Jobs navigation), out of this sprint's scoped "Tenant Jobs list/detail" mandate. Flagged in remaining blockers. |

## Response/filter/status mapping notes
- List envelope changed from `{jobs: Job[], total: number}` (legacy) to `{items: ServiceJobRecord[], total, limit, offset}` (canonical) — component updated accordingly (`jobs.data?.items` not `jobs.data?.jobs`).
- Status filter values changed from field_ops statuses (`in_progress`, `en_route`, `accepted`, `parts_required`, `completed`, `disputed`, `closed`) to canonical `service_jobs` statuses (`new`, `assigned`, `in_progress`, `completed`, `cancelled`) — `JobStatusBadge` has a graceful fallback for unmapped values, verified safe.
- Fields with no canonical equivalent (`customer_name`, `service_type` as string, `assigned_staff` as string, `job_value`, `minutes_in_status`) were **removed from display** rather than fabricated — replaced with real available fields (`zipcode`/`city`, `assignment_status`, `scheduled_date`/`scheduled_time_window`, short IDs for `assigned_staff_id`).
- SLA alerts widget (`jobsApi.slaAlerts()`) — **removed**, no canonical equivalent exists; not fabricated.

## No consumer left calling the legacy endpoint from the primary Jobs pages
Confirmed via re-grep after migration: `app/(tenant)/jobs/page.tsx` and `app/(tenant)/jobs/[id]/page.tsx` contain zero `jobsApi.` references post-migration.
