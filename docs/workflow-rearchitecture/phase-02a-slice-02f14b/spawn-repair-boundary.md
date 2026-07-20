# spawn_repair Boundary

## Classification

Same underlying capability as `convert_to_repair` — a manual, on-demand alternate that skips the
`QUOTE_APPROVED` prerequisite ("Manually spawn a repair job from a consultation (any time, not
just on quote approval)"), calling the shared internal helper
`_spawn_repair_from_consultation(consultation_job, quote)`. Not a Job-duplication route, not an
internal compatibility route, not a customer-approved conversion — a **provider-only operation**.

## Defects found and fixed (both were live, both closed)

1. **No tenant/job ownership check at all.** `spawn_repair_from_consultation` previously loaded
   the job by ID with zero ownership validation — any actor holding the platform-wide
   `TENANT_UPDATE` permission could spawn a repair from a **different tenant's** consultation
   job. Fixed by reusing `_get_job_for_assignment` (the identical helper `convert_to_repair` uses)
   — tenant_owner own-tenant, super_admin platform-wide.
2. **No duplicate-repair guard.** Unlike `convert_to_repair`, this method had no check for an
   existing repair job on the same parent — repeated calls could create unlimited duplicate
   repair jobs for the same consultation. Fixed by adding the identical
   `Job.parent_job_id == job.id AND job_type == REPAIR` existence check, raising the same
   `CONSULTATION_ALREADY_CONVERTED` (409) `convert_to_repair` already used.

## Verified

- Parent and child tenant match: child inherits `consultation_job.tenant_id` via `create_job`
  (which pins to `actor_tenant_id` for tenant-scoped callers — matching, since ownership is
  already enforced by `_get_job_for_assignment` before this point).
- Customer association cannot be overridden: child inherits `consultation_job.customer_id`.
- Foreign Job/source ID rejected: `_get_job_for_assignment` denies cross-tenant access (404).
- Read-only tenant actor denied: router upgraded to `require_tenant_mutation_permission`.
- Customer cannot invoke provider-only spawning: `TENANT_UPDATE` permission is not granted to
  `customer` in `ROLE_PERMISSIONS`.
- Repeated calls cannot create uncontrolled duplicate repairs: fixed (see above), tested via
  `test_duplicate_spawn_rejected`.
- Invalid state (non-CONSULTATION job_type) creates no child Job: `INVALID_JOB_TYPE` raised
  before any lookup of an existing repair or job creation.

No bridge to `ServiceJob` was created or considered.
