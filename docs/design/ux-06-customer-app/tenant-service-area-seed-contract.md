# Tenant Service Area Seed Contract — UX-06 Round 4

## Real endpoints used (no raw SQL)

```
POST /v1/tenant/service-areas/{area_id}/services   (create mapping)
PUT  /v1/tenant/service-areas/{area_id}/services/{mapping_id}  (update mapping)
GET  /v1/tenant/service-areas                        (list — used for before/after)
GET  /v1/tenant/service-areas/{area_id}/services      (list mappings — used for verification)
```

Authenticated as `provider@serviceos.local` (the DEMO tenant's real
`tenant_owner`), which already holds the real permissions
(`TENANT_SERVICE_AREA_SERVICE_CREATE`/`UPDATE`) these routes require —
no permission/authorization config was touched.

## Deterministic identifiers used

- Tenant: `5209ef33-a53e-4fc0-b3f6-006335b8d712` (pre-existing DEMO tenant)
- Service area (pre-existing, city-level Ludhiana coverage):
  `c50daa54-3d07-46a4-b449-41761ab33fc0`
- Service (`MasterService.id` for `ac_repair`, resolved via the real
  `GET /v1/catalog/master/services` catalog endpoint by slug — **not** the
  `MasterOffering.id` the customer-facing catalog returns; these are two
  distinct tables keyed by matching slug, a real discovery this round):
  `a96e625a-60e1-46c0-bde4-ccbb88da50a2`

## Row created

`TenantServiceAreaService` id `d07529ff-406f-4c83-9f89-ba423199860b`:
`{tenant_service_area_id: c50daa54-..., service_id: a96e625a-..., job_type: "repair", is_available: true, sla_minutes: 120, base_price: 775.00, min_price: 650.00, max_price: 900.00}`.

## Idempotency / rerun safety

The real `add_service_mapping` service method (`app/engines/serviceability/service.py:624`)
already enforces a real duplicate guard (`ERR_DUPLICATE_MAPPING`, 409) on
`(tenant_service_area_id, service_id, job_type, is_available=true)` — rerunning
the exact same create call a second time fails safely with a real 409 rather
than creating a duplicate row. Verified: rerunning the seed step is safe by
construction (backend-enforced), no custom idempotency logic was needed on the
client side.

## What this does NOT do

- Does not touch any other tenant's service areas (scoped by `tenant_id` at
  every layer — `area.tenant_id` is derived server-side from the area record,
  never client-supplied).
- Does not create wildcard/global coverage — scoped to exactly one city
  (Ludhiana) for exactly one service (`ac_repair`, `job_type=repair`) for
  exactly one tenant.
- Does not touch pricing/bargain policy beyond this one service area mapping's
  own `base_price`/`min_price`/`max_price` fields (which feed the
  catalog-default price-estimate path only, not the `match-and-price`
  provider-selection path — see round4-implementation-summary.md for why the
  full booking-submission sequence still isn't provable this round).
