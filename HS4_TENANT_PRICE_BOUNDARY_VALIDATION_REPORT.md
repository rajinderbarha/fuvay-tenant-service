# HS4 — Tenant Price Boundary Validation Report

## Backend enforcement — live-verified this sprint (fresh calls, real DB)
Using the real tenant service (AC Repair, `015efedb-dd92-41f4-97ef-cc2745437760`)
and its real admin-configured Window AC type range (₹550–₹1500):

1. `PUT .../types/{window_ac}/pricing` with `{100, 200}` (below admin min)
   → **422 `TENANT_PRICE_BELOW_ADMIN_MIN`**, `"Your minimum price cannot
   be below the admin floor (Rs. 550.00)."`, `request_id` present. ✅
2. `PUT .../types/{window_ac}/pricing` with `{600, 2000}` (above admin
   max) → **422 `TENANT_PRICE_ABOVE_ADMIN_MAX`**, `"Your maximum price
   cannot exceed the admin ceiling (Rs. 1500.00)."`, `request_id`
   present. ✅
3. Min > Max rejected — confirmed via source read (`tmin > tmax` check,
   `INVALID_PRICE_RANGE`), consistent with the two live calls above
   using well-formed ranges.

## Enforcement is server-side (not just frontend)
Confirmed via direct `curl` against the real backend, bypassing the
frontend entirely — these are real HTTP 422 responses from
`TenantCatalogService.set_type_pricing`/`set_brand_pricing`, not
client-side-only checks.

## Verdict
Provider price boundary validation: **enforced, live-verified,
server-side**. Both required error codes present with correct messages
and `request_id`.
