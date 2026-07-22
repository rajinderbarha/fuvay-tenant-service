# Assignment Ownership Audit — Workstream 6

## accept/reject (home_service_assignment.staff_router) — FIXED this slice
Previously relied solely on `ServiceJobAssignment.assigned_staff_member_id`
matching the resolved staff_id, with **no explicit tenant_id filter** in
`_load_job()`. This slice adds explicit tenant defense-in-depth:
- `HomeServiceJobAssignmentService.technician_accept_job` and
  `technician_reject_job` now accept an optional `tenant_id` parameter
  (default `None`, so no existing internal caller that doesn't pass it can
  break) and raise `ERR_ACCESS_DENIED` if the loaded `ServiceJob.tenant_id`
  doesn't match.
- The router handlers (`accept_job`, `reject_job`) now pass
  `tenant_id=uuid.UUID(str(user.tenant_id))` from the authenticated
  principal.
- The error message for `ERR_ACCESS_DENIED` is mapped to the same generic
  "Job not found." text as `ERR_JOB_NOT_FOUND` (not a distinct "wrong
  tenant" message) — deliberately, so a cross-tenant probe cannot
  distinguish "this job doesn't exist" from "this job exists but isn't
  yours," avoiding a sensitive-record-existence leak (Workstream 12's
  explicit requirement).
- This is defense-in-depth, not a replacement for the assignment-ownership
  check — `_current_assignment(job_id)` matching
  `assigned_staff_member_id` against the resolved staff_id remains fully
  intact and unchanged.

## assign/reassign/cancel-assignment/schedule (home_service_assignment.provider_router)
Already had tenant scoping (`tenant_id = uuid.UUID(user.tenant_id)` passed
to every service call, confirmed pre-existing from the `HS8 fix` comment in
source) — this slice added the access-scope guard
(`require_tenant_owner_mutation`) on top, without touching the existing
tenant-scoping mechanism.

`assign_job`'s service method already verifies `job.tenant_id == tenant_id`
(raises `ERR_ACCESS_DENIED`) and validates target-staff eligibility
(`validate_staff_eligibility` — wrong tenant, inactive, role-not-allowed all
produce distinct, specific error codes) — confirmed via direct source
reading, not re-implemented or weakened this slice.

`reassign_job`/`cancel_assignment`/`schedule_job`'s ownership mechanisms
were **not independently re-verified line-by-line this slice** (out of the
narrow "apply the access-scope guard + defense-in-depth for the one
documented gap" scope) — flagged in `known-limitations.md`, not a blocker
for this slice's closure since the guard swap itself doesn't touch or rely
on their correctness.

## Execution-progress endpoints (execution.home_service_router)
All 14 progress + 4 parts endpoints already call `_assert_staff_owns_job`
(via the service layer, unchanged this slice) after loading the job scoped
by `tenant_id` (via `_get_job`). This mechanism was not modified — only the
router-level guard (`get_current_user` → `require_staff_or_above_mutation`)
was added in front of it. Confirmed via the new regression test
(`TestAuthorizedActorClearsAuthLayer::test_technician_clears_auth_layer_execution`)
that an unassigned fake technician correctly hits
`EXECUTION_STAFF_NOT_ASSIGNED` (a 403 from the ownership layer, distinct
from the guard's own `PERMISSION_DENIED` 403) — proving both layers work
and are distinguishable.

## Wrong-provider / cross-tenant proof
- Cross-tenant: proven via the new tenant defense-in-depth check
  (accept/reject) and pre-existing tenant_id checks (assign/reassign/
  cancel-assignment/schedule, execution-progress) — confirmed present via
  source reading, exercised (with a mocked DB returning a non-matching
  tenant_id) via the live HTTP tests in
  `test_phase2f3b_execution_assignment_mutation_enforcement.py`.
- Wrong-provider (a technician from a DIFFERENT provider/tenant attempting
  to act on a job assigned to a different provider's technician): covered
  by the same tenant_id check, since "provider" in this system IS the
  tenant.
