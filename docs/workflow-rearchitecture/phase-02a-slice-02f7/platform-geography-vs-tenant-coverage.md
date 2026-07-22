# Platform Geography vs. Tenant Coverage Boundary — Workstream 4

## Finding
`app.engines.serviceability.router` does **not** mount any endpoint that
mutates shared platform geography (states, districts, cities, postal
codes, city tiers, or platform zones). Re-verified via direct source
read of all 19 mounted mutations:

- No route creates/updates/deletes a `ServiceZone` (owned by
  `app.engines.geo`) or `CityTierConfig` (owned by `app.engines.pricing`).
- `service.py` only ever `SELECT`s `ServiceZone` for matching purposes
  (2 read-only references, confirmed via grep) — never writes to it.
- `TenantServiceArea.zone_id` is a nullable reference to a
  platform-defined zone, but selecting/entering a zone_id when creating
  a tenant service area creates or updates a **tenant coverage mapping**
  (`TenantServiceArea`), not the canonical `ServiceZone` record itself —
  exactly the boundary the mission requires ("a tenant selecting a city
  or postal code should create or update a tenant mapping, not modify
  the canonical geography record").

## The 4 "admin" routes are not a boundary violation
`admin_create_service_area`, `admin_update_service_area`,
`admin_delete_service_area` all mutate `TenantServiceArea` — the same
tenant-owned coverage table as the tenant-facing routes, just invoked by
a platform admin on a specific tenant's behalf (URL `tenant_id`
parameter). They do **not** touch shared geography. Classified
`PLATFORM_GEOGRAPHY_ADMIN_ONLY` in the route inventory as a naming
convenience matching the mission's requested vocabulary, but the more
precise description is "platform admin managing tenant coverage
records," not "platform admin managing shared geography." No shared
geography mutation exists in this router at all.

## Requirements verification

| Requirement | Status |
|---|---|
| Tenant users cannot mutate shared geography | Trivially true — no shared-geography mutation endpoint exists in this module for anyone to reach |
| Tenant coverage routes may reference shared geography but cannot edit it | Confirmed — `zone_id` is read-only from this module's perspective |
| Platform geography routes use canonical platform permissions | N/A (no such routes exist here); the 4 admin routes correctly use `PLATFORM_ADMIN` |
| Platform routes do not receive tenant access-scope guards | Confirmed — the 4 admin routes were left on plain `require_permission(P.PLATFORM_ADMIN)`, not wrapped in `require_tenant_mutation_permission` (that guard is for tenant-scoped personas; a platform admin has no tenant access_scope to check) |
| Platform geography controls must not appear in tenant UI | Not independently re-verified at the frontend layer this slice (no tenant-portal geography-admin page was found to exist in the first place — see `frontend-exposure-audit.md`) |

## Conclusion
No platform-geography boundary violation exists in this module, and none
needed fixing. The boundary is naturally maintained by the fact that
`serviceability` simply does not own or mutate any shared geography
table — that ownership lives entirely in `app.engines.geo` and
`app.engines.pricing`, both untouched by this slice.
