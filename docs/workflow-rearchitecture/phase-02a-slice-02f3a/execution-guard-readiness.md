# execution.home_service_router — Next-Slice Guard-Application Readiness

## Disposition: READY_WITH_DISTINCT_PIPELINE_EXCEPTIONS

## Reasoning
The overlap that could have blocked broad guard application on
`execution.home_service_router` (the accept/reject shadowing against
`home_service_assignment.staff_router`) has been conclusively adjudicated:
the shadowed copies inside `execution.home_service_router`
(`staff_accept_job`, `staff_reject_job`) are dead code, unreachable, and
therefore pose no risk of a future guard slice protecting the wrong
implementation or leaving a live weaker path open. A future guard-
application slice can safely:
- Apply `require_tenant_mutation_permission`-style guards to all 25
  remaining LIVE endpoints in `execution.home_service_router` (23 total
  minus the 2 dead accept/reject copies... note: this document counts the
  27 non-duplicate + shadowed entries; see `canonical-route-disposition.csv`
  for the exact per-route list).
- SKIP `staff_accept_job`/`staff_reject_job` entirely (guarding dead code
  wastes effort and produces misleading "protected" claims for something
  that never executes) — OR, at minimum, explicitly document them as
  excluded-because-unreachable in that slice's own inventory, rather than
  silently omitting them without explanation.

"Distinct pipeline exceptions" refers to: the whole-job-cancellation
(`provider_cancel_job`) vs assignment-cancellation (`cancel_assignment`)
distinction, and the admin-only (`PLATFORM_INTERNAL`) 3 endpoints, which
need different treatment (owner/staff-scope guard vs. platform-admin
guard vs. no guard needed) rather than one uniform sweep.

## What is NOT yet resolved (documented, not glossed over)
- **Object/assignment-ownership mechanism for the 14 execution-progress
  endpoints** (`_assert_staff_owns_job`) was not independently
  re-verified this slice for correctness against every edge case (e.g.
  does it correctly reject a technician from a DIFFERENT tenant, or only a
  different technician within the same tenant?) — flagged in
  `known-limitations.md`, not blocking readiness but worth a first check
  in the guard-application slice itself.
- **Parts-request endpoints' ownership checks** were not independently
  re-verified this slice.
- **Admin override endpoints' permission grants** (`require_admin_jobs_*`)
  were not re-checked against `ROLE_PERMISSIONS` this slice.

None of these block starting the guard-application slice — they are exactly
the kind of per-endpoint verification work that slice is expected to do,
same as Slices 2F-1/2F-2 did for their own modules.

## home_service_assignment.staff_router / provider_router — own guard slice needed?
**YES.** Both remain entirely unprotected by access-scope enforcement today
(confirmed: all 6 mutation endpoints across both routers are
`AUTHENTICATED_ONLY_NO_PERMISSION_CHECK`, per Slice 2F's original inventory
and re-confirmed live this slice). They should receive their OWN guard-
application slice — either combined with `execution.home_service_router`'s
guard slice (since they cooperate on the same `ServiceJob` record) or as an
immediately-following slice, given how closely coupled the record model is.
Recommendation: guard all 3 modules together in the next slice, now that
this adjudication has cleared the way, rather than splitting further.

## Explicitly not decided or started this slice
No mutation guard was applied to any of the 29 routes in this slice — per
the mission's explicit instruction, "Do not begin broad mutation-guard
application to execution.home_service_router during this slice."
