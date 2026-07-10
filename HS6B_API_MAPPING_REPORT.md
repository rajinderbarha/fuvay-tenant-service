# HS6B — API Mapping Report (updated, second pass)

## Existing endpoint, response shape extended
`POST /v1/admin/home-services/matching-diagnostics` (or the equivalent
route registered by `auto_price_options_router.py`) — no new route, but
its request body now accepts an optional `requested_at`, and its
response gained 5 keys: `excluded_providers`, `bookability_source`,
`area_coverage_source`, `availability_source`, `pricing_source`. This is
additive — no existing consumer breaks.

## Real endpoints confirmed reused (not duplicated)
- `POST /v1/provider/status/refresh` — the canonical bookability
  computation matching trusts, unchanged this pass (fixed in HS4B).
- HS5B's `PUT /v1/provider/service-areas/{area_id}/coverage` — the real
  endpoint used to configure the coverage data matching correctly
  consumes.
- HS5B's `POST /v1/provider/home-services/matching-inputs/preview` — its
  underlying function `get_tenant_home_services_matching_inputs()` is
  now also called directly by `_passes_full_eligibility_gate` (imported,
  not reimplemented) when `requested_at` is supplied, so the real
  matching gate and the customer-facing preview endpoint share the exact
  same break/holiday/booking-window logic — no drift possible between
  the two.

## Verdict
API integration: one existing endpoint's contract extended additively;
no new routes; the previously-separate preview function and the real
matching gate now share one source of truth for time-window logic.
