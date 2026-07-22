# create_job Authority

## Defect found and fixed

`tenant_id` was previously taken directly from the request body with **no check against the
caller's own tenant** — a `tenant_owner`/`staff`/`technician` could create a Job under any
`tenant_id` they chose. Fixed: `FieldOpsService.create_job` now pins `tenant_id` to
`self.actor_tenant_id` whenever `actor_role in ("tenant_owner","staff","technician")` and that
tenant is known — the identical pattern already established in `list_jobs`. `super_admin` (and
the internal `_spawn_repair_from_consultation` caller) may still pass an explicit `tenant_id`.

## Verified

- Read-only tenant actors: denied — router now uses `require_tenant_mutation_permission`.
- Request `tenant_id` cannot override principal tenant (test:
  `test_tenant_owner_cannot_override_tenant_id`).
- `super_admin`'s explicit `tenant_id` is preserved (test:
  `test_super_admin_tenant_id_not_overridden`) — necessary since `super_admin` has no own tenant.
- Staff/technician creation authority: `TENANT_UPDATE` is granted by existing `ROLE_PERMISSIONS`
  to `tenant_owner`/`super_admin` only — `staff`/`technician` do **not** hold this permission, so
  they are already denied by the existing permission grant (not modified, no new permission
  added).
- Customer cannot call this route: `require_tenant_mutation_permission(P.TENANT_UPDATE)` denies
  any role lacking the permission, and `customer` never holds `TENANT_UPDATE`.
- Customer association (`data.get("customer_id")`): passed through as-is. This is legitimate
  business functionality (tenant staff creating a job on behalf of an existing customer) — the
  `customer_id` is only used as a foreign-key attachment on the new Job row and grants the actor
  no additional authority over any other resource. No further restriction was found necessary or
  applied.
- A foreign booking/service record: `booking_id`/`service_type_id` are stored as-supplied
  references (same as before) — no FK validation exists in this codebase for either; this is
  unchanged from pre-existing behavior and out of this slice's proven-defect scope (no
  same-record bypass was identified from a foreign booking ID — the booking pipeline itself is
  a distinct pipeline, see job-pipeline-boundary.md from Slice 2F-14).
- Invalid creation (e.g. bad `job_type`) raises before `db.add` — no Job, assignment, or
  checklist items are created (`INVALID_JOB_TYPE` raised before the `Job(...)` construction).

## Alternate creation route

`_spawn_repair_from_consultation` (internal-only helper, called by `spawn_repair_from_consultation`
and `respond_to_quote`) calls `create_job` internally with `consultation_job.tenant_id` — since
the caller's `actor_tenant_id` at that point already matches the source job's tenant (enforced by
the fixes in convert-to-repair-boundary.md and spawn-repair-boundary.md), no conflict with the
new tenant-pinning logic occurs.
