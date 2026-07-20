# Product Decisions Required — Slice 2F-7 (not resolved this slice)

## 1. Should staff/technician ever get delegated service-area capabilities?
Currently `TENANT_SERVICE_AREA_CREATE/UPDATE/DELETE/SERVICE_*` are
granted only to `tenant_owner`. If the product wants office staff to
manage coverage without owner involvement, these permissions are the
candidates to extend — not done this slice ("do not grant a permission
merely because no role currently has it").

## 2. Tenant-catalog-enablement for service mappings
`add_service_mapping` validates against the canonical, platform-wide
`MasterService` catalog but does not check for a separate tenant-specific
"this service is enabled for my tenant" record. Whether such a concept
exists or should exist is owned by `admin_catalog`, explicitly out of
scope this slice ("do not begin admin_catalog.tenant_router").

## 3. Geography reference validation
No canonical Country/State/District/City/PostalCode table exists
anywhere in the platform. Whether to introduce one (enabling postal-code
format validation, city/district cross-checks, country linkage) is a
significant platform-wide product/architecture decision, not scoped to
this slice ("do not invent geography concepts missing from the
repository").

## 4. District as a coverage type
`district` is stored on both `CustomerAddress` and `TenantServiceArea`
but is not a selectable `coverage_type` and is never used as a matching
key. Whether to implement district-level coverage is a product decision,
not made here.

## 5. Missing audit event for service-mapping mutations
`add_service_mapping`/`update_service_mapping`/`delete_service_mapping`
do not call an audit-logging function, unlike area-level mutations. A
future slice should decide the event-name/payload convention.

## 6. The `geo.ServiceZone` tenant-portal page
`app/(tenant)/service-areas/page.tsx` is a separate, existing UI for a
different backend module (`app.engines.geo`) with its own zone CRUD.
Whether this page's authorization matches its own backend's policy was
not evaluated this slice (out of scope — a different module).

## Recommendation (non-binding)
None of these block security or domain-integrity closure. If prioritized,
the geography-reference-table question (#3) would have the broadest
platform-wide impact and should be scoped as its own dedicated
initiative, not a follow-up patch.
