# HS5B — Per-Area Service/Type/Brand Coverage Report

## Real finding: infrastructure existed, was never wired up
`tenant_service_area_services` (service-level per-area coverage) already
existed as a real table — but **no router anywhere in the codebase used
it**. This sprint both extended its schema (`service_type_id`, `brand_id`
columns via migration 121) and built the first real endpoint for it.

## API — live-verified
- `GET /v1/provider/service-areas/{area_id}/coverage` — lists coverage
  rows for an area.
- `PUT /v1/provider/service-areas/{area_id}/coverage` — upsert
  (service_id + service_type_id + brand_id is the natural key, matched
  with `IS NOT DISTINCT FROM` to correctly handle NULL type/brand).

## Validation — real, against real catalog tables, live-verified
- Service must be tenant-enabled (`tenant_services.is_active=true`) —
  `SERVICE_NOT_TENANT_ENABLED` if not.
- Type must belong to the selected service
  (`master_service_types.master_service_id=service_id`) —
  `INVALID_SERVICE_TYPE_FOR_COVERAGE` if not.
- Brand must belong to the selected service
  (`master_service_brands.master_service_id=service_id`) —
  `INVALID_BRAND_FOR_COVERAGE` if not, **live-verified**: a fake brand
  UUID was correctly rejected with this exact error code and the
  ticket's exact message.

## Live verification — real data
Set Split AC + LG coverage for the real "Ludhiana Central" area
(zipcode 141001) for the real AC Repair tenant service → `200`,
real row created with `service_type_id`/`brand_id` correctly persisted.

## No dedicated frontend UI built this sprint
The service-areas page's existing "Supported Services/Types/Brands"
form fields (confirmed present in the HS5 sprint) were not re-wired to
this new endpoint — that would require frontend changes not made this
sprint.

## Verdict
Per-area type/brand coverage: **real gap found (dead infrastructure)
and fixed — schema extended, real endpoint built, validated against
real catalog data, live-verified including the rejection case**.
Frontend wiring: **not done this sprint**.
