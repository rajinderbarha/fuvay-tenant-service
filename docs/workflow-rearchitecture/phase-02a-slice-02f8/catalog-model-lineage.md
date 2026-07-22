# Catalog Model Lineage — Workstream 2

## Models touched by `admin_catalog.tenant_router` / `TenantCatalogService`

| Model | Table | Tenant key | Ownership | Classification |
|---|---|---|---|---|
| `MasterService` | `master_services` | none | Platform | **PLATFORM_CATALOG_CANONICAL** — read-only from this router |
| `ServiceCategory` | `service_categories` | none | Platform | **PLATFORM_CATALOG_CANONICAL** — read-only (`enable_service` checks `cat.is_active`) |
| `ServiceGroup` | (referenced via `svc.service_group_id`) | none | Platform | **PLATFORM_CATALOG_CANONICAL** — read-only, used as the entitlement key |
| `MasterServiceType` | `master_service_types` | none | Platform | **PLATFORM_CATALOG_CANONICAL** — canonical type-to-service mapping, read-only |
| `MasterServiceBrand` | `master_service_brands` | none | Platform | **PLATFORM_CATALOG_CANONICAL** — canonical brand-to-service mapping, read-only |
| `ServiceType` | `service_types` | none | Platform | **PLATFORM_CATALOG_CANONICAL** — read-only |
| `Brand` | `brands` | none | Platform | **PLATFORM_CATALOG_CANONICAL** — read-only |
| `ServicePricingRule` | `service_pricing_rules` | none | Platform | **PLATFORM_CATALOG_CONFIGURATION** — pricing-floor reference, read-only from this router |
| `TenantService` | `tenant_services` | `tenant_id` (required) | Tenant | **TENANT_SERVICE_ENABLEMENT** — the canonical "this tenant has enabled this master service" record; created/updated/soft-toggled by this router |
| `TenantServiceType` | `tenant_service_types` | `tenant_id` (denormalized) | Tenant | **TENANT_CATALOG_MAPPING** — which canonical types a tenant supports for an enabled service |
| `TenantServiceBrand` | `tenant_service_brands` | `tenant_id` (denormalized) | Tenant | **TENANT_CATALOG_MAPPING** — which canonical brands a tenant supports |
| `TenantServiceArea` (from `serviceability`) | `tenant_service_areas` | `tenant_id` | Tenant (owned by `serviceability`, read-only reference from `publish_service`'s area-existence check) | **TENANT_SERVICE_ENABLEMENT** (cross-module reference, not owned here) |

## Entitlement dependency
`enable_service` calls `entitlement_service.has_category_entitlement(db, tenant_id, svc.service_group_id)` (from `app.engines.entitlement`) — a **platform-owned package/plan entitlement check**, confirming a tenant cannot enable a service outside their subscribed category/service-group, re-verified unmodified (FINAL-L5-04B, pre-existing).

## No merging performed
Per instruction ("do not merge models"), `TenantService`/`TenantServiceType`/`TenantServiceBrand` remain distinct, separately-keyed tables, exactly as found. No consolidation was made.
