# Tenant Provider Price Range Setup Report

## Status: already built and certified in the prior sprint

The "Tenant Home Services Service Setup Wizard" ticket (immediately
preceding this one) already delivered the full tenant-side price range
setup flow this ticket's Part B describes, live-verified against the
exact same example numbers this ticket uses:

- Route: `/tenant/setup/services`
- Step 3 (Set Provider Price Range): shows Platform Allowed Range
  (admin floor/ceiling, read-only), Your Provider Range (editable
  min/max inputs), and a live Customer Price Options Preview
  (Low/Mid/High) sourced from the real backend after each save.
- Step 4 (Brand Overrides): Same for all / Override some, per-brand
  provider range inputs, admin-range validation, routing-only brands
  disabled from override.
- Step 5 (Review & Publish): full pricing matrix (Service/Type/Brand/
  Platform Range/Provider Range/Customer Sees/Price Source/Status-style
  columns), Save Draft, Publish (blocked when setup is incomplete or no
  active service area exists).

## Re-verified this sprint

Live-verified again (after the menu reorganization, to confirm nothing
regressed):
- Provider range 800–1000 @ 10% platform fee → **Low ₹880 / Mid ₹990 /
  High ₹1100** — exact match to this ticket's example.
- `TENANT_PRICE_BELOW_ADMIN_MIN` (422) still correctly rejects a
  provider minimum below the admin floor.
- `TENANT_PRICE_ABOVE_ADMIN_MAX` (422) still correctly rejects a provider
  maximum above the admin ceiling.
- Backend enforces `provider_min <= provider_max`, `provider_min >=
  admin_min`, `provider_max <= admin_max` — all server-side, not just in
  the frontend (see `TenantCatalogService.set_type_pricing`/
  `set_brand_pricing` in `app/engines/admin_catalog/tenant_service.py`).

## Tenant cannot edit admin-controlled fields

The wizard's pricing step only renders inputs bound to `tenant_min_price`/
`tenant_max_price` — `admin_floor_price`, `admin_ceiling_price`, and
`platform_fee_percent` are displayed as read-only text, never as editable
form fields, matching the ticket's "Tenant cannot edit: Admin Min Price,
Admin Max Price, Platform Fee, Completed Job Deduction" rule.

## No new frontend/backend changes were required for Part B

This report exists to confirm — not re-build — that requirement. See
`TENANT_HOME_SERVICES_SETUP_TEST_RESULTS.md` (prior sprint) for the full
original live-verification transcript, including the brand-override
example (Voltas 950/950 → Low ₹1045) and the publish-validation bug fixes
made at that time.
