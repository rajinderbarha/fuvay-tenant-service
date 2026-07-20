# Tenant Catalog Enablement Contract — Workstream 7

## Canonical model
"A service is enabled for a tenant" is represented by a `TenantService`
row (`tenant_services` table) with `is_enabled = True`, uniquely keyed on
`(tenant_id, master_service_id)`. Created by `enable_service`
(`POST /v1/tenant/catalog/enable-service`), soft-toggled off by
`disable_service` (`POST /v1/tenant/catalog/disable-service`).

## Prerequisites enforced at enablement time (re-verified, unmodified)
- `MasterService` must exist and be `is_active` (canonical catalog gate).
- Its `ServiceCategory` must be `is_active`.
- The tenant must hold an **active category entitlement** for the
  service's `service_group_id`, via
  `entitlement_service.has_category_entitlement` (FINAL-L5-04B,
  package/plan-based).
- No package prerequisite beyond the entitlement check was found
  (entitlement is itself presumably package-derived, not independently
  re-traced this slice — `entitlement` is a separate module).
- No explicit approval/review state exists for enablement itself (the
  separate `setup_status` field on `TenantService` — `draft`/`published`
  — governs the *setup wizard's* completeness, gated by
  `publish_tenant_service`, not enablement).

## The exact 5 questions

### 1. Does `TenantServiceAreaService` require an enabled `TenantService`?
**NO.** `serviceability.service.ServiceabilityService.add_service_mapping`
calls `_assert_service_active(service_id)`, which validates the
`service_id` against **`admin_catalog.MasterService`** only (must exist +
`is_active`) — it never queries `TenantService` at all. Re-confirmed via
direct source read of `_assert_service_active` (re-verified from Slice
2F-7, not assumed).

### 2. Does serviceability validate only canonical service activity?
**YES**, confirmed above.

### 3. Can a tenant map a globally active service it has never enabled?
**YES** — nothing in `serviceability.add_service_mapping` prevents this.
A tenant could call `POST /v1/tenant/service-areas/{area_id}/services`
with any active `MasterService.id`, without ever having called
`enable_service` for it.

### 4. Would that make the service appear serviceable/matchable?
**Unresolved — genuinely ambiguous, and the ambiguity goes deeper than
the enablement question.** `match_tenants_for_location`'s matching query
joins `TenantServiceAreaService.service_id` against
**`app.engines.service_catalog.models.ServiceCatalogItem`** — a
**third, distinct, tenant-scoped legacy model** (`service_catalog_items`
table, `"One service a tenant offers"`, its own `tenant_id` column) —
**not** `admin_catalog.MasterService` and **not** `admin_catalog.TenantService`.
A code comment in `serviceability/service.py` (MODULE-L5-02) asserts
"the matching engine already reads `tenant_service_area_services.service_id`
as a master_service id," implying an assumption that `ServiceCatalogItem.id`
and `MasterService.id` share the same ID space — but no migration, seed
script, or synchronization mechanism between `MasterService`/`TenantService`
and `ServiceCatalogItem` was found in this investigation. Whether
`service_catalog_items` rows are ever created for a tenant that enables a
service through the modern `admin_catalog` flow was not conclusively
established within this slice's scope (a separate, standalone
`service_catalog` module with its own router and `create_item` method
exists and was not investigated in depth — doing so would mean
auditing a fourth, unnamed module, squarely out of this slice's
boundary).

### 5. Is tenant catalog enablement a proven business rule, or only an intended future policy?
**Cannot be conclusively established either way from the available
evidence.** No test, product document, or explicit business rule
statement was found asserting "a service must be `TenantService`-enabled
before it can be added to a `TenantServiceArea`." The permission/service
layer treats `MasterService`-activity as the only enforced precondition.

## Disposition
**PRODUCT_DECISION_REQUIRED.**

This does **not** meet the bar for a serviceability code change, because
not all of the required conditions are proven:
- Tenant enablement being "canonical and currently required" for
  serviceability is **not established** — no evidence proves this is an
  enforced business rule today, only that it is *plausible* product
  intent.
- Whether `TenantServiceAreaService`'s matching path even correctly
  reaches live data through `ServiceCatalogItem` is itself an open,
  unresolved question — introducing a `TenantService.is_enabled` check
  into `serviceability` would not resolve that deeper, separate
  ambiguity, and could not be verified by a regression test without
  first resolving the `ServiceCatalogItem` question (which requires
  investigating a fourth module).
- Per the interim policy, "only modify serviceability if all are
  proven" — they are not. **Serviceability is left unchanged this
  slice.**

## What was and was not done
- `admin_catalog.tenant_router`/`TenantCatalogService` were audited and
  the one proven, directly-connected bypass (cross-tenant `tenant_id`
  query-param override) was fixed — squarely within this module's own
  boundary.
- `serviceability.service.py` was **not modified**.
- The `ServiceCatalogItem`/`MasterService` ID-space question is logged
  in `product-decisions-required.md` as a recommended follow-up
  investigation, not resolved here.
