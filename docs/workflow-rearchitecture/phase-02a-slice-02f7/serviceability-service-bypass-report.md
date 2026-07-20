# Serviceability Service Bypass Report — Workstream 10

## Methods audited
`create_service_area`, `update_service_area`, `deactivate_service_area`,
`set_primary_service_area`, `add_service_mapping`,
`update_service_mapping`, `delete_service_mapping`, `create_address`,
`update_address`, `delete_address`, `set_default_address`.

## Callers
Every one of these methods has **exactly one caller**: the corresponding
endpoint in `serviceability/router.py`. Re-confirmed via the alternate-
route audit (`alternate-serviceability-route-audit.md`) — no other
module writes to any of the 4 tables this service owns.

## Tenant ID source verification
All 8 tenant-facing coverage mutations derive `tenant_id` from
`str(u.tenant_id)` (the router's `_svc` factory reads it from the
authenticated `UserContext`) — never from a request body or query
parameter. The 3 admin routes accept an explicit `tenant_id` URL
parameter (appropriate for a platform-admin persona acting on any
tenant's behalf), cross-checked against the loaded record's real
`tenant_id` (FINAL-L5-05Q fix, pre-existing, re-verified unmodified).

## Ownership verification
- Coverage/service-area ownership: `_assert_owns_tenant`, called at the
  top of every area-scoped read/write.
- Service/category ownership: `_assert_service_active`, validates
  against the canonical `admin_catalog.MasterService` before creating a
  mapping.
- Geography-reference validation: `_validate_coverage`, enforces
  required fields per `coverage_type` (no canonical table to validate
  against beyond that, per `geography-reference-integrity.md`).

## Transaction boundaries
Each mutation performs its DB writes and `db.commit()` within the same
request — no cross-request transaction spanning. `create_service_area`
additionally uses a Postgres advisory transaction lock
(`pg_advisory_xact_lock`) keyed on the exact tenant+coverage tuple before
its duplicate check, closing a previously-confirmed concurrent-duplicate-
create race (FINAL-L5-05Q, pre-existing, re-verified unmodified).

## Cache/index updates
No cache or search index exists for this domain — every mutation writes
directly to the row the matching query later reads, with no
intermediate materialized view or cache layer to invalidate.

## Audit behavior
`_audit_service_area` is called for area create/update/deactivate
(confirmed present, pre-existing, unmodified — this service is the
"certified canonical owner" per the FINAL-L5-05T ADR referenced in its
own source comments). Service-mapping mutations
(`add_service_mapping`/`update_service_mapping`/`delete_service_mapping`)
do **not** call an equivalent audit function — a pre-existing gap, not
introduced this slice, logged in `known-limitations.md` rather than
fixed (same disposition as similar audit gaps found in prior slices —
choosing the event-name/payload convention is a small design decision,
not a mechanical fix).

## Service-layer defense-in-depth
Already present and correct: `_assert_owns_tenant` runs inside the
service layer itself, independent of the router-level guard — meaning
even if a router-level guard were ever misconfigured, the service layer
would still reject a cross-tenant mutation attempt. This is genuine,
pre-existing defense-in-depth, re-verified via the direct cross-tenant
tests in `tests/test_phase2f7_serviceability_authorization.py`.

## Conclusion
Zero connected service bypasses found. One pre-existing, low-severity
audit-coverage gap (service-mapping mutations lack an audit event)
documented as a known limitation, not fixed.
