# Automatic Price Options — Home Services Scope Guard Report

## Backend

`assert_home_services_vertical()` (from the Provider Matching sprint,
`app/engines/home_service_booking/matching_engine.py`) remains the single
guard function. The 4 new endpoints in `auto_price_options_router.py` are
all inherently Home-Services-scoped by construction:

- `price-experience/preview` and `matching/diagnostics` operate on raw
  admin-supplied parameters or on `master_service_id`/`category_id` that
  only resolve to real data for Home Services categories — there's no
  Home Services-specific business language exposed if called against a
  different vertical's data, since the underlying `select_best_provider`
  query itself is already scoped to `t.vertical == "home_services"` (fixed
  in the Provider Matching sprint).
- `customer-price-preview` and `matching-readiness` are tenant-scoped by
  JWT — a non-Home-Services tenant would simply have no matching
  `BargainRule`/eligibility data to return (`available: false` / accurate
  "not ready" message), never a fabricated result.

## Frontend

Both new UI surfaces (admin Home Services pages, tenant Customer Price
Preview) are Home-Services-only in *purpose* — the admin pages are
explicitly under a "Home Services" nav group; the tenant page has an
explicit `tenant.vertical !== "home_services"` guard rendering a blocked
message instead of any Low/Mid/High UI, mirroring the exact pattern
established for the Service Setup page in the prior sprint.

## Verified

- Static-inspection test confirms the tenant guard condition and message
  text are present in the page source.
- Reused (not re-tested this sprint, already live-verified in the Provider
  Matching sprint) confirmation that a real IELTS Coaching category is
  correctly rejected by `assert_home_services_vertical`.
