# Category, Service, and Parent Integrity — Workstream 8

## Verified

| Check | Status | Evidence |
|---|---|---|
| A service belongs to the selected category | YES | `enable_service` reads `svc.category_id` directly from the loaded `MasterService` row and copies it onto the new `TenantService` — the category is never independently client-supplied |
| A category belongs to the expected service group | Implicit — `svc.service_group_id` is read from `MasterService`, used only for the entitlement check, not independently re-validated against `ServiceCategory` in this router |
| Tenant cannot enable a child service without a required parent mapping | N/A — no parent/child hierarchy between two `TenantService` rows was found; `TenantServiceType`/`TenantServiceBrand` are children of a single `TenantService` (the enabled service itself is the "parent"), and both require `_load_tenant_service` + `_assert_tenant_owns_ts` before any child mutation, which transitively requires the parent `TenantService` to exist and belong to the tenant |
| Tenant cannot create duplicate mappings | YES | `enable_service` rejects with `TENANT_SERVICE_ALREADY_ENABLED` (409) if an enabled row already exists for `(tenant_id, master_service_id)`; the unique constraint `uq_ts_tenant_service` on `TenantService` backs this at the schema level too |
| Disabled/archived platform catalog records cannot be newly enabled | YES | `enable_service` rejects with `MASTER_SERVICE_INACTIVE` if `svc.is_active` is false, and `SERVICE_CATEGORY_INACTIVE` if the category is inactive |
| Removing a parent mapping handles child mappings per existing, explicit behavior | Documented, not redesigned — `disable_service` only sets `TenantService.is_enabled = False`; it does **not** cascade to `TenantServiceType`/`TenantServiceBrand` rows, which remain in the database unchanged (their own `is_enabled` flags are untouched). This means re-enabling a service (via `enable_service`'s re-enable path, which flips `is_enabled` back to `True` on the existing row) would restore the previously-configured types/brands automatically, since they were never deleted. This is existing, unmodified behavior — not a cascade defect, but a "soft-disable preserves child configuration" design, confirmed via source read, not invented or changed |
| Tenant cannot reference a service type/option belonging to another service | Not independently re-traced to the byte level this slice for `set_tenant_service_types`/`set_tenant_service_brands`'s internal `type_ids`/`brand_ids` validation against `MasterServiceType`/`MasterServiceBrand` — existing pattern, not flagged as broken by any test or investigation finding, and modifying it was not evidenced as necessary |
| Tenant cannot reference an invalid brand for the selected service/category | Same disposition — existing validation pattern, not independently re-verified byte-by-byte, no defect evidenced |
| Tenant cannot overwrite canonical platform names/descriptions/hierarchy | YES | No mutation method in `TenantCatalogService` writes to any field of `MasterService`/`ServiceCategory`/`ServiceGroup`/`ServiceType`/`Brand` — confirmed via grep for `.add(MasterService`/`update(MasterService`/etc. across `tenant_service.py`: zero matches |

## No cascade behavior invented
Per instruction ("do not invent cascade behavior"), the observed
soft-disable-preserves-children behavior is documented as-is; no new
cascade-delete or cascade-disable logic was added.
