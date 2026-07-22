# Product Decisions Required — Slice 2F-21

## For Slice 2F-22 (selected module: package_commerce.tenant_router)
1. **`mark_paid` self-attestation trust.** `POST /v1/tenant/packages/{package_id}/purchase`
   reads `payload.get("mark_paid")` directly from the untrusted tenant
   request body and passes it straight into `create_package_assignment(...,
   is_paid=bool(...))`. Whether a tenant-side caller should EVER be able to
   self-mark a purchase as paid (versus requiring a payment-gateway
   verified token, or denying the flag entirely for non-`super_admin`
   callers) is a genuine product/business decision, not resolved by this
   slice. A valid interim security fix exists without resolving the
   underlying payment-gateway-integration question (see
   `selected-next-module.md`).
2. **Purchase idempotency / duplicate-purchase semantics.** No
   idempotency-key check found in the call path. Whether duplicate
   purchases of the same `package_id` by the same tenant should be
   rejected, allowed (stacking), or require confirmation is a product
   decision for the implementation slice.

## For future slices (non-selected modules, not blocking)
- `customer_reviews.provider_router` / `marketing_automation.provider_router`:
  whether `staff` (not just `tenant_owner`) should be admitted for these
  capabilities — flagged, not blocking (a role-gate-only fix is possible
  without resolving this).
- `admin_catalog.brand_provider_router` /
  `admin_catalog.service_option_provider_router`: whether cross-tenant
  service_id references should ever be legitimately allowed (e.g. platform
  catalog admin flows) — flagged, not blocking.

None of the above are BLOCKING for Slice 2F-22's selection or for this
slice's own coverage reconciliation, per the mission's own selection
criteria (interim security fixes exist for all flagged items).
