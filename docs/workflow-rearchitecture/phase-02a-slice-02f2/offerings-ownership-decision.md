# Offerings Ownership Decision — Workstream 8

## What provider_portal.router owns
`provider_enabled_offerings` — the tenant's selection of which platform
`master_services` it has enabled, plus provider-level overrides
(`provider_display_name`, `provider_price_override`, `provider_min_price`/
`max_price`, `provider_visit_fee`, `provider_appointment_fee`,
`supported_type_ids`, `supported_brand_ids`) and lifecycle state
(`is_enabled`, `is_active`, `status`, `readiness_status`).

Separately, `set_area_coverage` owns `tenant_service_area_services` — a
DIFFERENT, more granular per-service-area coverage mapping (which
service/type/brand combination is offered in which geographic area),
already correctly guarded pre-slice via
`require_tenant_mutation_permission(P.TENANT_SERVICE_AREA_SERVICE_UPDATE)`.

## Is the mutation tenant-wide?
Yes for all 5 offerings endpoints (`enable_offering`,
`update_enabled_offering`, `activate_offering`, `deactivate_offering`,
`refresh_offering_readiness`) — every mutation is scoped by the caller's
own `tenant_id`, affecting the whole business's service catalog, not a
per-technician or per-area subset.

## Staff delegation / technician self-service
Neither is proven or present — all 5 are `require_tenant_owner`-gated
(now `require_tenant_owner_mutation`), excluding staff and technician
entirely, same evidence basis as the availability capabilities.

## Required permission
None granted today (role-gate only, like most of this module) — this
slice's guard swap adds access-scope enforcement without introducing a new
granular permission, consistent with "do not grant new permissions merely
to make an endpoint accessible."

## Canonical vs. duplicate — Workstream 8 disposition
Checked for another router owning the same enable/disable-a-service-offering
capability. `app.engines.admin_catalog` and `app.engines.service_setup`
modules own **catalog definition** (creating/editing `master_services`
themselves, platform-wide) — a materially different capability from
provider_portal's **enablement selection** (a tenant choosing which
already-defined services to turn on for their business). No duplicate
route was found for offering enable/disable/activate/deactivate/readiness-
refresh.

**Disposition: CANONICAL_HERE** for all 5 offerings mutation endpoints —
`provider_portal.router` is the sole, correct owner of tenant-level
offering-enablement mutations; no compatibility route, no consolidation
needed.

For `set_area_coverage`: also **CANONICAL_HERE** — the per-area coverage
mapping is a provider-portal-specific concept (HS5B, per the existing
docstring), not duplicated by the admin catalog (which defines what
service/type/brand combinations exist globally, not which areas a specific
tenant covers with them).

## Frontend exposure
Confirmed via `frontend/tenant-portal/lib/api.ts` (lines ~2537-2549) — all 5
offerings endpoints have a real tenant-portal caller, tenant_owner-facing,
matching the backend policy.
