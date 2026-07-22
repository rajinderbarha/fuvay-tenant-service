# create_job Caller Audit

## Callers enumerated

1. **`POST /v1/jobs` route** (`app.engines.field_ops.router.create_job`) — persona:
   `tenant_owner`/`super_admin` (via `require_tenant_mutation_permission(P.TENANT_UPDATE)`).
   Tenant source: server-pinned. Customer source: client-supplied (subject to this slice's new
   relationship guard when standalone). Booking/parent: either optional. No frontend caller
   exists (`FRONTEND_MUTATION_SURFACE_ABSENT`, re-confirmed).
2. **`FieldOpsService._spawn_repair_from_consultation`** (internal, called by
   `spawn_repair_from_consultation` and `respond_to_quote`'s auto-conversion path) — persona:
   whatever the outer caller's `actor_role`/`actor_tenant_id` already is (already validated by
   `_get_job_for_assignment`/`respond_to_quote`'s own customer check before this internal call is
   ever reached). Customer source: always `str(consultation_job.customer_id)` — **always the
   parent-derived mode**, so the new relationship guard never fires for this caller (confirmed:
   it always supplies `parent_job_id`).

## Confirmation

No internal caller supplies `customer_id` in standalone mode (neither `booking_id` nor
`parent_job_id`) — the only caller that reaches `create_job` at all besides the public route is
`_spawn_repair_from_consultation`, and it always supplies `parent_job_id`. **No caller legitimately
requires arbitrary global customer selection.** No compatibility exception was needed or granted.
