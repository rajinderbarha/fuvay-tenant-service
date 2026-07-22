# Geography and Coverage Model Lineage — Workstream 2

## Central finding
`app.engines.serviceability` owns exactly **4 tables**, none of which is a
canonical platform geography reference table (no `Country`, `State`,
`District`, `City`, or `PostalCode` model exists anywhere in this
repository, in this module or any other). `state`/`city`/`district`/
`zipcode` are plain, unvalidated string columns on `CustomerAddress` and
`TenantServiceArea` — there is no separate geography table to foreign-key
against. This is a genuine, pre-existing platform characteristic, not a
gap introduced or hidden by this module — confirmed by repository-wide
search, not assumed.

## Models owned by serviceability

| Model | Table | Tenant key | Classification |
|---|---|---|---|
| `CustomerAddress` | `customer_addresses` | `tenant_id` (nullable — a customer may not belong to any tenant) | Not geography — a customer's own saved address. Not classified under the geography taxonomy; it's `MATCHING_INPUT` (used to resolve serviceability/matching) and a `CUSTOMER`-owned record. |
| `TenantServiceArea` | `tenant_service_areas` | `tenant_id` (required) | **TENANT_SERVICE_AREA** — a tenant's declared coverage area (city, zipcode, zone-reference, or radius). |
| `TenantServiceAreaService` | `tenant_service_area_services` | `tenant_id` (denormalized from parent area) | **TENANT_SERVICE_COVERAGE** — maps a canonical `MasterService` (from `admin_catalog`) to a specific `TenantServiceArea`, i.e. "this tenant covers this service in this area." |
| `ServiceabilityAuditLog` | `serviceability_audit_logs` | none (platform-wide log) | Not a coverage model — an immutable log of every serviceability check, written by `check_serviceability`. |

## Models referenced but NOT owned by serviceability

| Model | Owning module | How referenced | Classification |
|---|---|---|---|
| `ServiceZone` | `app.engines.geo` | `TenantServiceArea.zone_id` (nullable FK, read-only from this module — confirmed via grep, only ever `SELECT`ed for matching, never created/updated/deleted here) | **PLATFORM_GEOGRAPHY** (owned by `geo`, out of scope) |
| `CityTierConfig` | `app.engines.pricing` | Not referenced at all by `serviceability` (checked via grep — zero hits) | **PLATFORM_TIER_CONFIGURATION** (owned by `pricing`, entirely separate, not touched by this module) |
| `MasterService` | `app.engines.admin_catalog` | `TenantServiceAreaService.service_id`, validated via `_assert_service_active` (must exist + `is_active`) | Canonical service catalog, read-only from this module |

## Concepts explicitly NOT implemented anywhere in the platform
Per Workstream 6, marked explicitly rather than assumed or invented:
- **District** as a first-class geography level: exists only as a
  free-text column on `CustomerAddress`/`TenantServiceArea`, never
  validated, never used as a matching key by `service.py` (confirmed via
  grep — `district` only appears in model definitions and payload
  passthrough, never in a `WHERE` clause of the matching logic).
- **Country** as a validated reference: `country` defaults to `"India"`
  everywhere, never validated against any list.
- **Postal-code format validation**: none — `zipcode` is a bare
  `String(20)` with no regex/format check anywhere in `service.py` or
  the Pydantic schemas.
- **City tier** mutation from within `serviceability`: does not exist —
  `CityTierConfig` lives entirely in `pricing`, a separate, unmounted-
  by-this-router engine.

None of these were implemented this slice, per "do not invent geography
concepts missing from the repository."
