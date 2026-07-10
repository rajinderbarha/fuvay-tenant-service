# ADMIN-TENANT-E2E-09B — Window AC + LG Sparse Coverage Report

## Findings (real, live, before any change)

- Window AC (`e27f6591-...`) is a valid admin master type for AC Repair (`master_service_types`
  row exists), but was **not enabled** as a supported type for Demo AC Services at all
  (`GET .../types` returned only Split AC). The prior sprint's "₹420-490 tenant price" note was
  stale/inaccurate — real current data (confirmed via `GET .../type-pricing` after enabling the
  type) is admin floor/ceiling 550/1500 with an existing tenant range of 600/700 already stored
  (i.e. Window AC pricing existed in the DB from an earlier setup attempt, but the type was
  disabled at the `types` list level, so it was invisible/unusable).
- LG brand was already enabled at the brand level for this service (`is_enabled: true`).
- No `tenant_service_area_services` row existed for (area 141001, service=AC Repair,
  type=Window AC, brand=LG) — confirmed via direct SQL. Only the Split AC + LG row existed.

## Real, additive fix attempted (via real tenant APIs, not raw SQL)

1. `PUT /v1/tenant/catalog/enabled-services/{id}/types` with `type_ids=[Split AC, Window AC]`
   → 200 OK. Window AC is now a supported type (additive; Split AC untouched).
2. `PUT /v1/provider/service-areas/{area}/coverage` with
   `{service_id, service_type_id: Window AC, brand_id: LG}` → **500 IntegrityError**:
   `duplicate key value violates unique constraint "uq_tsas_active_mapping"` on
   `(tenant_service_area_id, service_id, job_type)`.

## Real root cause

`tenant_service_area_services` enforces uniqueness on **(area, service, job_type)** only — not
on (area, service, type, brand) despite `service_type_id`/`brand_id` being real columns on the
table. Because Split AC and Window AC share the same `service_id` (AC Repair) and the same
`job_type` (`repair`), the existing Split AC coverage row already occupies that unique slot,
and a second per-type coverage row for the same service/job_type cannot be inserted through the
current schema/endpoint — this is a genuine backend data-model limitation, not a data-entry gap.

## Decision

Per the spec's own guidance ("if adding it is risky... document as a scoped P2 gap instead"),
this is documented as a scoped P2/backend-schema gap rather than forced with a raw-SQL
workaround that would violate the app's own constraint and its intended semantics. The
additive, safe part (enabling Window AC as a supported type + LG brand) was completed and left
in place since it is harmless and forward-progress; the area-coverage row itself could not be
added without either a schema migration (out of this sprint's scope — no schema changes were
authorized) or an app-level redesign of how the coverage table keys per-type coverage, which is
a legitimate follow-up recommendation for a future sprint.

Demo AC Services' bookability was re-verified immediately after (`is_bookable: true,
is_visible: true`) — this attempt did not break the shared tenant's live bookability.
