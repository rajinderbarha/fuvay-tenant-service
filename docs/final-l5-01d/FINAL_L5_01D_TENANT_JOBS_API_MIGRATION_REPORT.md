# FINAL-L5-01D — Tenant Jobs API Migration Report

## Changes made
1. **`frontend/tenant-portal/lib/api.ts`**: added `serviceJobsApi` typed module (`list()`, `get()`) wrapping the canonical `/v1/provider/my-records/jobs` endpoints, alongside the pre-existing `serviceJobAssignmentApi` (`/v1/provider/service-jobs/*`).
2. **`app/(tenant)/jobs/page.tsx`**: rewritten to call `serviceJobsApi.list()` instead of `jobsApi.list()`. Verified: real seeded jobs (`L501-JOB-*`) now returned by the canonical endpoint for this exact tenant.
3. **`app/(tenant)/jobs/[id]/page.tsx`**: rewritten to call `serviceJobsApi.get()` for the job record and `serviceJobAssignmentApi.{getTimeline, getEligibleStaff, assign, cancelAssignment, schedule}` for actions — replacing the legacy quote/checklist/assessment workflow (which has no canonical equivalent) with real assignment-lifecycle actions.

## Requirements checklist

| Requirement | Status |
|---|---|
| Use central API client | Yes — `apiFetch` via `lib/api.ts`, no raw fetch in page components |
| Use typed domain API methods | Yes — `serviceJobsApi`, `serviceJobAssignmentApi` |
| Preserve tenant context | Yes — canonical endpoint derives tenant from JWT (`_get_tenant_id(user)`), no client-supplied `tenant_id` needed |
| Preserve authentication | Yes — unchanged, `Depends(get_current_user)` |
| Preserve pagination | Yes — real `limit`/`offset`/`total` from the canonical envelope |
| Preserve filters | Yes — `status` filter preserved, values updated to canonical enum |
| Preserve sorting | Backend orders by `created_at desc` server-side; no client sort control existed before or after |
| Preserve search | Client-side search preserved (job_number, zipcode — `customer_name`/`service_type` search removed since those fields no longer exist in the canonical response) |
| Preserve status labels | Yes — `JobStatusBadge` unchanged, gracefully humanizes any unmapped status string |
| Preserve assignment/schedule/cancel actions | Yes — now wired to the *real* assignment API (previously these used to be part of the legacy `job_type`-aware close/quote flow, which had no true "assign a technician" concept — this is arguably a functional improvement, not just a swap) |
| Preserve request_id error handling | Yes — unchanged, `apiFetch`'s existing error handling applies uniformly |
| Remove legacy response-shape adapters | Yes — no adapter layer was added; the component consumes the canonical shape directly |

## Verified
- `npx tsc --noEmit`: **0 errors** for the whole tenant-portal app after this change.
- Zero `jobsApi.` references remain in the two migrated files (grep-verified).
- Live curl confirms the canonical endpoint returns real seeded data for the exact canonical tenant used in browser testing.

## What was NOT preserved (honest, not hidden)
The legacy detail page's quote negotiation, checklist, assessment (repair/service/consultation `job_type`), and "close with final price" workflows have **no equivalent** in the canonical `service_jobs` model and were removed rather than pointed at wrong data or fabricated. If this functionality is still required for Home Services tenants, it needs a proper design/backend-extension pass — not a frontend adapter. Flagged in remaining blockers.

## Failure status
Not applicable — migration completed, TypeScript clean, zero legacy calls remain in the target files.
