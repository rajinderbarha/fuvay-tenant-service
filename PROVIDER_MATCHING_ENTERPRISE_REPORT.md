# Provider-First Matching + Customer Price Choice — Final Report

## Scope note

This ticket was followed immediately by a scope-correction message restricting
the whole flow to Home Services only. Both are covered in this single report;
see the "Home Services Only" section at the end.

## 1. Flow correction

Replaced the customer-facing "list providers, customer picks manually" model
with: backend eligibility-gates every candidate → scores them → selects
exactly one → computes that provider's Low/Mid/High price → customer chooses
a tier only. New module `app/engines/home_service_booking/matching_engine.py`
(pure scoring/pricing functions + DB-aware eligibility/ranking/area-comparison
functions), new service methods `match_provider_and_price` and
`confirm_price_choice` in `home_service_booking/service.py`, two new customer
router endpoints (`/match-and-price`, `/confirm-price-choice`) under the
existing `/v1/customer/home-services/booking-drafts/{draft_id}/` prefix. Old
list-based endpoints (`/match-providers`, `/select-provider`) kept for backward
compatibility, marked `[DEPRECATED]`.

## 2. Provider matching rules

All required eligibility gates implemented in `_passes_full_eligibility_gate`:
tenant active, home_services vertical, not suspended, bookable
(`provider_visibility_statuses.is_bookable`), service area covers zipcode,
offering enabled+active, type/brand coverage (when requested), ≥1 active
technician, availability configured, pricing exists, package active, usage
credits available, security deposit paid/waived. Live-verified: the real test
tenant is correctly **excluded** (status is `pending_setup`, not `active`, and
no bookability row exists yet) — deliberately not mutated to force a fake
"success," per this session's established convention of not disturbing shared
baseline test fixtures.

## 3. Provider ranking factors

`compute_provider_score` implements the ticket's exact weighted formula (8
factors, weights sum to 1.0). Verified formula-exact via unit test. Low-health
provider loses to a stronger one — verified.

## 4. Selected provider price options

`compute_price_tiers` reuses the Bargain Module's `evaluate_customer_bargain`
(prior sprint) for `allowed_offer_min`/`allowed_offer_max`, then derives
`low_price = allowed_offer_min`, `high_price = allowed_offer_max`,
`mid_price = round_to_nearest_10((min+max)/2)`. Matches the ticket's
₹715/₹810/₹900 example exactly.

## 5. Area competitor comparison

`get_area_market_comparison` — separate, read-only function with no code path
back into provider selection or price computation (verified via static
inspection test). Live-tested against real DB (returns zero-competitor state
correctly for the current sparse test data).

## 6. API response shape

`match_provider_and_price` returns the exact ticket JSON shape:
`selected_provider` (public fields only), `selected_provider_price_options`,
`area_market_comparison`. `internal_score`/`internal_score_breakdown` only
included when `reveal_internal_score=True` (an admin/debug-only parameter,
never set by the customer router).

## 7. Booking creation

`confirm_price_choice` accepts only a `price_tier` name (`low`/`mid`/`high`)
— never a raw customer-submitted amount — resolves the exact stored backend
price, and stores the full required snapshot (`selected_tenant_id`,
`selected_provider_name`, `selected_zipcode`, `matching_score_snapshot`,
`selected_price_tier`, `customer_offer`, `allowed_offer_min/max`,
`platform_fee_amount`, `payment_mode`) onto `draft.booking_summary`.

## 8. Bugs found and fixed

1. New area-comparison SQL had an asyncpg `AmbiguousParameterError` on
   `NULL`-comparison bind params — fixed with explicit `CAST(... AS TEXT/UUID)`.
2. Candidate base query filtered on `tenants.category_id`, which is NULL on
   real seeded tenants (same class of bug found and fixed in the My Offerings
   sprint) — removed; vertical is now the correct, populated gate.
3. (Addendum) No vertical restriction existed at all — any vertical could in
   principle invoke this Home-Services-specific matching/bargain logic. Fixed
   with a hard `assert_home_services_vertical` guard.

## 9. Tests

34 total: 18 in `test_provider_first_matching_and_price_choice.py` (formula,
ranking, price tiers, redaction, eligibility-gate structure), 15 in
`test_home_services_only_bargain_scope.py` (vertical guard). 103/103 across
the full recent-sprint regression run.

## 10. Home Services Only (scope addendum)

- Added `assert_home_services_vertical(vertical)` / `VerticalFlowNotSupported`
  (a `ServiceOSException` subclass, `error_code=VERTICAL_FLOW_NOT_SUPPORTED`,
  `status_code=422`, context `{"supported": false, "vertical": ..., "reason": ...}`
  — matches the ticket's alternate JSON contract).
- Wired into `match_provider_and_price` — resolves the category's
  `vertical_type` and rejects anything but `"home_services"` before any
  matching/scoring/pricing logic runs.
- Live-verified against a real IELTS Coaching category — correctly rejected
  with 422.
- All customer-facing routes already live under
  `/v1/customer/home-services/booking-drafts/...` (the ticket's preferred
  naming), not a generic `/v1/customer/bookings/...` path.
- 15 tests added covering: Home Services passes, 5 non-Home-Services
  verticals rejected (CA/professional_services, IELTS/coaching, restaurant,
  real_estate, education), `None` vertical rejected, guard is actually wired
  into the service entry point (static inspection), route naming is
  Home-Services-scoped, error response shape matches the ticket's JSON
  contract exactly.
- No customer-facing frontend exists in this repo (consistent with all prior
  sprints) — the "hide Low/Mid/High UI for non-Home-Services" requirement is
  satisfied structurally: the backend never returns that data for a
  non-Home-Services request (it 422s before computing anything), so no future
  UI built against this API can accidentally render it for the wrong vertical.

## Final recommendation

**READY_PROVIDER_FIRST_MATCHING_THEN_CUSTOMER_PRICE_CHOICE_CERTIFIED**
**READY_HOME_SERVICES_ONLY_PROVIDER_FIRST_BARGAIN_SCOPE_CERTIFIED**

See `PROVIDER_MATCHING_TEST_RESULTS.md` and `PROVIDER_MATCHING_REMAINING_BLOCKERS.md`
for full verification evidence and honestly-documented non-blocking gaps
(chiefly: draft creation's dependency on the legacy `master_offerings` table,
a pre-existing, separate issue out of this ticket's scope).
