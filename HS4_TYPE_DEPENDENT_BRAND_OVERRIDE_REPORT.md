# HS4 — Type-Dependent Brand Override Report

## Status: already fixed and live-verified in a prior sprint this session
This exact requirement (Window AC + LG and Split AC + LG must be
separate, independently-priced records) was the subject of a dedicated
earlier sprint this session ("FIX — Home Services Type-Dependent Brand
Pricing"), which:
1. Added migration 120: `service_type_id` column on
   `tenant_service_brands`, unique constraint widened to
   `(tenant_service_id, service_type_id, brand_id)`.
2. Fixed `set_brand_pricing`/`get_brand_pricing_for_setup` in
   `tenant_service.py` to actually scope by `service_type_id` (previously
   accepted the parameter but silently ignored it for storage).
3. Live-verified: Window AC + LG set to ₹370–480, Split AC + LG set to
   ₹700–850 independently, confirmed as 2 distinct DB rows with correct,
   independent values on GET.
4. HS3 (admin side) added the matching
   `SERVICE_TYPE_REQUIRED_FOR_BRAND_PRICING` validation to the admin
   pricing-rule creation endpoint and duplicate-rule detection.

## Re-confirmed this sprint
`tests/test_type_dependent_brand_pricing.py` (14 tests) and
`tests/test_hs3_admin_tier_pricing.py` (15 tests) — both re-run this
sprint, **29/29 passing**, confirming the fix is still intact and
hasn't regressed across the HS2/HS2B/HS3 sprints that touched adjacent
code.

## Frontend
`/tenant/setup/services` already renders brand pricing scoped per
selected type (per-type/brand table layout, confirmed in the HS0/HS2
sprints' inspection of this page) — `service_type_id` is threaded
through the existing API calls unchanged.

## Verdict
Type-dependent brand override: **fixed, live-verified, and
regression-tested across 4 sprints**. No new work needed this sprint —
re-confirmed intact.
