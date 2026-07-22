# Alternate Catalog Route Audit — Workstream 11

## Method
Searched `admin_catalog`'s other routers (`brand_provider_router`,
`recommendation_router`, `service_option_provider_router` — all
explicitly deferred, not modified), `provider_portal`, `tenant_engine`,
`serviceability`, `pricing`, package commerce, and legacy catalog engines
(`service_catalog`) for equivalent tenant-catalog-enablement capability.

## Findings

### `TenantService`/`TenantServiceType`/`TenantServiceBrand` — sole writer confirmed
Re-confirmed via repository-wide search for `TenantService(`/
`TenantServiceType(`/`TenantServiceBrand(` constructor calls and for
`.add(TenantService`/`update(TenantService` statements: the only writer
is `admin_catalog.tenant_service.TenantCatalogService`. A name collision
exists — `app.engines.tenant_engine.service.TenantService` is a
**completely different class** (tenant-engine business logic, e.g.
`check_limit`), not the catalog model — confirmed by import path, not
assumed. **Disposition: CANONICAL_TENANT_ENABLEMENT_WRITE.**

### `admin_catalog.brand_provider_router` / `recommendation_router` / `service_option_provider_router`
Not investigated in depth (explicitly deferred: "do not begin
admin_catalog.brand_provider_router" etc.) — confirmed only that they are
structurally separate router files, not reachable from
`tenant_router.py`, and not mounted under the same prefix. **Disposition:
REQUIRES_FUTURE_MODULE_SLICE** (each is its own future closure target,
not audited here beyond confirming they are structurally distinct).

### `service_catalog` module (legacy)
A genuinely separate, tenant-scoped `ServiceCatalogItem` model
(`service_catalog_items` table) exists with its own router
(`app.engines.service_catalog.router`) and `create_item`/`update_item`/
`deactivate_item` methods. This is **not** an alternate writer for
`TenantService` — it's a structurally distinct, seemingly legacy
tenant-catalog concept that the matching engine's query joins against
(see `tenant-catalog-enablement-contract.md` for the full ambiguity this
raises). **Disposition: DISCONNECTED** relative to `admin_catalog.TenantService`
— no write-path overlap was found, but its *read* relationship to
`serviceability`'s matching query is a genuine open question, logged as
a product decision, not a duplicate-writer security concern for this
module.

### `provider_portal`, `tenant_engine`, `pricing`, `package_commerce`
No equivalent tenant-catalog-enablement mutation capability was found in
any of these modules — confirmed via targeted grep for
`TenantService`/`master_service_id` write patterns. No alternate route
exists.

## Summary table

| Capability | tenant_router route | Alternate | Canonical owner | Disposition |
|---|---|---|---|---|
| Tenant service enablement | `enable_service`/`disable_service` | none found | `admin_catalog.TenantCatalogService` | CANONICAL_TENANT_ENABLEMENT_WRITE |
| Tenant type/brand mapping | `set_tenant_service_types`/`set_tenant_service_brands` | none found | same | CANONICAL_TENANT_ENABLEMENT_WRITE |
| Tenant service-level pricing override | `set_tenant_type_pricing`/`set_tenant_brand_pricing` | none found | same | CANONICAL_TENANT_ENABLEMENT_WRITE |
| Tenant service publish/draft | `publish_tenant_service`/`save_tenant_service_draft` | none found | same | CANONICAL_TENANT_ENABLEMENT_WRITE |
| Legacy tenant-scoped `ServiceCatalogItem` | n/a (not in this router) | `service_catalog.router` | `app.engines.service_catalog` | DISCONNECTED (separate model, not a weaker alternate writer of `TenantService`) |

## Conclusion
No weaker alternate write path was found for anything this module owns.
The 3 sibling `admin_catalog` provider/recommendation/option routers
remain correctly deferred to future slices, not begun here.
