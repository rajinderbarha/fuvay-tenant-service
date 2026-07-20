# Service Catalog Ownership — Workstream 5

## Verified checks for tenant-facing coverage mutations

| Check | Status | Evidence |
|---|---|---|
| Principal tenant is authoritative | YES | Every tenant-facing route derives `tenant_id` from `str(u.tenant_id)` (the caller's own `UserContext`), never from a request body/path parameter |
| Request tenant_id cannot override the principal tenant | YES | The 8 tenant routes accept no `tenant_id` parameter at all — only the 3 admin routes accept one, and those are platform-admin-only with an explicit mismatch check (FINAL-L5-05Q) |
| Coverage belongs to the principal tenant | YES | `get_service_area(area_id)` calls `_assert_owns_tenant(area.tenant_id)` for every area-scoped mutation (update, delete, set-primary, and both mapping-creation/lookup paths) |
| Parent service area belongs to the principal tenant | YES | `add_service_mapping`/`update_service_mapping`/`delete_service_mapping` all resolve the area first via `get_service_area`/`_get_mapping`, inheriting the ownership check |
| Referenced tenant service belongs to the principal tenant | PARTIAL — see finding below | `_assert_service_active` validates the `service_id` exists and is active in the **canonical, platform-wide** `admin_catalog.MasterService` catalog — it does not check that the tenant has separately "enabled" or "subscribed to" that service via any tenant-specific catalog-enablement table |
| Canonical category/service references are valid | YES | `_assert_service_active` (MODULE-L5-02 fix, pre-existing) |
| Foreign coverage IDs are rejected | YES | `_assert_owns_tenant` raises `NotFoundException` (404, not 403 — avoids existence leakage) |
| Foreign service-area IDs are rejected | YES | Same mechanism |
| Foreign service mappings are rejected | YES | `_get_mapping` cross-checks `mapping.tenant_service_area_id == area.id` |
| Removing coverage does not delete canonical geography or catalog records | YES | `delete_service_mapping` sets `is_available=False` (soft); `deactivate_service_area` sets `is_active=False` (soft) — neither touches `MasterService` or `ServiceZone` |
| Error responses do not expose foreign record details | YES | `NotFoundException("TenantServiceArea", str(id))` returns only the ID that was requested, not the foreign tenant's data |

## Finding: no tenant-catalog-enablement check
`add_service_mapping` validates that `service_id` refers to an
**active, canonical, platform-wide** `MasterService` — it does not
independently verify that the tenant has a separate "this service is
enabled for my tenant" record (if such a concept exists elsewhere in
`admin_catalog`, e.g. a tenant-service-enablement table). This was
**not investigated further this slice** — `admin_catalog.tenant_router`
is explicitly out of scope ("do not begin admin_catalog.tenant_router").
Whether a tenant can map coverage for a canonical service the platform
offers but the tenant has not individually "turned on" is a genuine
open question, logged in `product-decisions-required.md`, not
conclusively provable as a defect within this module's own boundary
(the canonical-catalog check that does exist is correct and was not
weakened).

## Conclusion
All ownership checks explicitly required by the mission are verified
present and correct, except one (tenant-catalog-enablement), which is
flagged as an open question belonging to a different module's scope,
not fixed here.
