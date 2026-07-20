# convert_to_repair Boundary

## Findings

Source record: `field_ops.Job` (job_type `CONSULTATION`). Target: a new `field_ops.Job`
(job_type `REPAIR`), linked via `parent_job_id`. Object ownership was **already correct** —
`_get_job_for_assignment` (tenant_owner own-tenant, super_admin platform-wide), unmodified.

- **Target tenant**: derived from source (`tenant_id=job.tenant_id`), never from the request —
  verified correct, unchanged.
- **Customer association**: derived from source (`customer_id=job.customer_id`), never
  substitutable — verified correct, unchanged.
- **Source state prerequisite**: `job.status == JS.QUOTE_APPROVED` required, else
  `CONSULTATION_CONVERSION_NOT_ALLOWED` (422) — verified correct, unchanged.
- **Duplicate-conversion guard**: two independent checks — `job.status == JS.CONVERTED_TO_REPAIR`
  (409) and an explicit query for an existing `Job` with `parent_job_id == job.id AND
  job_type == REPAIR` (409 `CONSULTATION_ALREADY_CONVERTED`) — verified correct, unchanged.
- **Transaction boundary**: both the new repair Job and the consultation's status update are
  flushed within the same service-method call, no partial-state window observed in code
  inspection.

## Defect found and fixed

The router guard was `require_permission(P.FIELD_OPS_JOBS_ASSIGN)` — **permission-only, not
access-scope-aware** (the same defect class already fixed for `assign_job`/`update_status` in
Slice 2F-14 and for the 5 financial routes in Slice 2F-14A). A tenant-side actor with a read-only
access scope could still perform this real mutation. Fixed: upgraded to
`require_tenant_mutation_permission`.

## Verified

- Source belongs to the principal tenant: enforced (`_get_job_for_assignment`).
- Read-only tenant actor denied: now enforced at the router (fixed).
- Technician tenant-wide conversion: `FIELD_OPS_JOBS_ASSIGN` is granted to `tenant_owner` only in
  `ROLE_PERMISSIONS` — technician has no established policy for this and is correctly denied by
  the existing permission grant.
- Source cannot convert twice: verified (duplicate guard above).
- Invalid source state creates no target: `INVALID_TRANSITION`-style exceptions raise before any
  `Job(...)` construction.
- Failure leaves no partial state: the duplicate/state checks all occur before `self.db.add`.
