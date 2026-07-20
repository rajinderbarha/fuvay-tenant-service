# Product Decisions Required — Slice 2F-8 (not resolved this slice)

## 1. Tenant catalog enablement vs. serviceability's matching path
Whether `TenantServiceAreaService` (in `serviceability`) should require
an enabled `TenantService` before allowing coverage mapping is
unresolved (`PRODUCT_DECISION_REQUIRED` — see
`tenant-catalog-enablement-contract.md`). Compounding this: the
matching engine's own query joins against a third, apparently-legacy
model (`app.engines.service_catalog.ServiceCatalogItem`), not
`admin_catalog.MasterService` or `TenantService` — whether this join
target is even correctly populated for tenants using the modern
`admin_catalog` enablement flow is itself an open question requiring
investigation of a fourth, unnamed module. Recommend a dedicated future
slice to resolve the `ServiceCatalogItem` question before deciding
whether to add a `TenantService.is_enabled` check to serviceability.

## 2. Concurrency hardening for `enable_service`
No advisory/row lock exists (unlike `serviceability.create_service_area`'s
`pg_advisory_xact_lock`, Slice 2F-7). The schema-level unique constraint
prevents an actual duplicate row, but a concurrent race would surface as
a raw database `IntegrityError` rather than a clean 409. Whether to add
a matching advisory lock is a reasonable future-slice candidate, not
conclusively required by any evidenced production incident this slice.

## 3. Audit-event coverage for catalog-enablement mutations
No audit-log call was found in any of the 9 mutation methods (unlike
similarly-scoped modules audited in prior slices). A future slice should
decide the event-name/payload convention and add it.

## 4. Should staff ever receive delegated catalog-mapping capability?
`TENANT_UPDATE` is currently `tenant_owner`-only. Whether office staff
should be able to enable/configure services without owner involvement is
an open product question, not decided here.

## Recommendation (non-binding)
Item #1 (the enablement/matching ambiguity) is the highest-value
follow-up — it touches real matching/booking correctness, not just
authorization, and deserves its own dedicated investigation slice
scoped explicitly to `service_catalog` and the matching engine's join
target.
