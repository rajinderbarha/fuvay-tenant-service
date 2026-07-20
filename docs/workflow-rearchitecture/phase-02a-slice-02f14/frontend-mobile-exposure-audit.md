# Frontend / Mobile Exposure Audit

## staff_router (`/v1/staff/me/jobs/...`)

Searched all of `frontend/` for any caller. Only stale references exist in
`frontend/tenant-portal/docs/e2e10/*.md` (historical E2E report markdown, not executable code).
Consistent with the already-recorded L5-36 finding (memory: `project_module_l5_36_...`): the
staff-app's job surface was repointed away from `field_ops` (0 rows) to the real `service_jobs`
pipeline via `homeServiceStaffJobsApi`. **Result: `FRONTEND_MUTATION_SURFACE_ABSENT`** — no live
frontend or mobile caller of `field_ops.staff_router` exists. This slice's fixes close a real
tool-visibility/completion-gate gap, but no UI currently reaches these routes at all.

## field_ops.router's 9 fixed routes

`frontend/tenant-portal/lib/api.ts` defines a `jobsApi` client (`list`, `get`, `history`,
`updateStatus`, `updateChecklist`) and a standalone `submitFindings` function that target these
exact routes (`/v1/jobs/{id}/status`, `/v1/jobs/{id}/checklist`, `/v1/jobs/{id}/findings`).
Searched `frontend/tenant-portal/app/**` for any component invoking `jobsApi.updateStatus`,
`jobsApi.updateChecklist`, or `submitFindings` — **zero live call sites found**. The only
references are in the same stale `docs/e2e10/*.md` historical reports. **Result:
`FRONTEND_MUTATION_SURFACE_ABSENT`** for all 9 fixed routes as well — confirmed no regression
risk from this slice's guard changes (a live tenant_owner-facing page calling the legacy
`updateChecklist` route would have been broken by the new `require_staff_or_technician_only`
guard, since that route previously admitted any authenticated user with zero role check; no such
live caller exists, so no regression occurred).

## Conclusion

No frontend or mobile UI changes were made or are needed this slice — there is nothing live to
align. This is recorded rather than silently ignored, per the mission's `FRONTEND_MUTATION_SURFACE_ABSENT`
convention used in prior slices.
