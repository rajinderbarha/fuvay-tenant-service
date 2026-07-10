# Type-Dependent Brand Pricing — API Report

## Tenant-facing endpoints (real, fixed this sprint)

| Endpoint | Change |
|---|---|
| `GET /v1/tenant/catalog/enabled-services/{tenant_service_id}/brand-pricing?service_type_id=` | Already accepted `service_type_id` as a query param (pre-existing); now actually filters `TenantServiceBrand` rows by it instead of ignoring it for storage |
| `PUT /v1/tenant/catalog/enabled-services/{tenant_service_id}/brands/{brand_id}/pricing?service_type_id=` | Same — now upserts a row scoped by `(tenant_service_id, service_type_id, brand_id)` instead of `(tenant_service_id, brand_id)` |
| `GET /v1/tenant/catalog/enabled-services/{tenant_service_id}/brands` | Unchanged endpoint, fixed underlying query — restricted to the type-independent enablement marker rows so per-type pricing rows don't pollute the brand-selection list |

## New validation errors (real, implemented and live-verified)

```json
{
  "error_code": "SERVICE_TYPE_REQUIRED_FOR_BRAND_PRICING",
  "detail": "Service type is required when adding brand pricing for a type-based service."
}
```
Raised when `ts.requires_type` is true and `service_type_id` is omitted.
Live-verified: calling `set_brand_pricing` without `service_type_id` for
the real type-based AC Repair tenant service returns this exact error.

```json
{
  "error_code": "SERVICE_TYPE_NOT_SUPPORTED",
  "detail": "This type is not selected for this service."
}
```
Raised when the given `service_type_id` isn't an enabled
`TenantServiceType` for this tenant_service.

Both errors flow through the existing `ServiceOSException` → RFC 7807
problem+json handler, which includes `request_id` automatically (no new
handling needed — confirmed via `test_backend_exceptions_use_serviceos_
exception`).

## Admin-side endpoints (ticket-requested, not built this sprint)
The ticket asks for `GET/POST/PUT /v1/admin/home-services/pricing-rules`
with `service_type_id`/`brand_id`/`tier_id` query params and a
`DUPLICATE_TYPE_BRAND_PRICING_RULE` error. The underlying
`ServicePricingRule` model already has the required columns and (as of
this sprint) the unique constraint that would produce a DB-level
integrity error on a true duplicate — but the admin router/service layer
was not updated this sprint to catch that integrity error and translate
it into the ticket's specific `DUPLICATE_TYPE_BRAND_PRICING_RULE`
`ServiceOSException`. Documented in Remaining Blockers.

## Customer price resolution (ticket-requested, not built this sprint)
The ticket describes a 5-step resolution fallback (brand+type+zone →
type+zone → service+zone → error). The existing
`_find_admin_pricing_rule` helper in `tenant_service.py` already
implements the *type+brand exact-match* step correctly (verified live),
but the full customer-facing booking-time resolution chain (with
zone/tier fallback) lives in a different part of the codebase
(booking/matching engine) that was not touched or verified this sprint.
Documented in Remaining Blockers — this sprint's scope was the tenant
setup wizard's pricing storage/API, not the customer booking price
resolution path.

## Verdict
Tenant-facing API: **fixed and live-verified**. Admin-side duplicate-rule
API error and full customer resolution chain: **not implemented**,
honestly flagged rather than claimed complete.
