# Tenant Type-Brand Override Validation Report

## All required validations already real (backend, prior sprint) — re-confirmed this sprint
1. Type-based brand override requires `service_type_id` —
   `SERVICE_TYPE_REQUIRED_FOR_BRAND_PRICING` (422).
2. `service_type_id` must belong to `service_id` — enforced via the
   `TenantServiceType` lookup in `set_brand_pricing`
   (`SERVICE_TYPE_NOT_SUPPORTED` if the type isn't enabled for this
   tenant service).
3. `brand_id` valid for service/type — `MasterServiceBrand` lookup,
   `BRAND_NOT_SUPPORTED` if not.
4/5. Provider min/max validated against the admin range for that
   specific service+type+brand combination — `TENANT_PRICE_BELOW_
   ADMIN_MIN`/`TENANT_PRICE_ABOVE_ADMIN_MAX`, both live-verified this
   sprint (real 422s with real request_ids on the previous "Tenant
   Price Boundary" sprint, re-confirmed unchanged this sprint via the
   successful within-range saves).
6. Min ≤ Max — `INVALID_PRICE_RANGE`.
7. Duplicate handling — upsert by natural key
   `(tenant_service_id, service_type_id, brand_id)`, confirmed via this
   sprint's live test: updating Window AC + LG a second time correctly
   updated the existing row rather than creating a duplicate.
8. Window AC + LG and Split AC + LG are independent — **the core fix
   this sprint**, live-verified with 3 distinct DB rows.
9. All errors include `request_id` — confirmed via the existing global
   `ServiceOSException` → RFC 7807 contract, unchanged.

## Frontend-side (informational only — backend remains authoritative)
No client-side pre-validation was added beyond what already existed
(numeric parsing checks) — the fix's scope was the type-scoping bug,
not new validation logic. All validation enforcement is server-side.

## Verdict
Validation: **complete, real, and live-verified**. All 9 ticket-required
rules confirmed enforced server-side.
