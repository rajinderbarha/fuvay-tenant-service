# CUSTOMER-L5-08 — Runtime Evidence

## Live Backend Certification: NOT PERFORMED

Identical constraint to every previous sprint: this environment has no
running backend server, no reachable database, and no seeded provider/
tenant/service-area data. None of the following were done:

- No real `POST /{draftId}/match-and-price` request ever left this
  machine.
- No real successful match against seeded eligible-provider data was
  observed.
- No real `HOME_BOOKING_NO_PROVIDER_AVAILABLE` or `PRICE_OPTIONS_UNAVAILABLE`
  422 was ever triggered and observed against a live server.
- No real multi-candidate scoring/selection was observed choosing between
  two or more genuinely eligible tenants.
- No request IDs, status codes, or screenshots from a live run exist.

## What Was Verified Instead

- The exact real backend contract, via direct source-code reading of
  `home_service_booking/service.py`, `matching_engine.py`, `constants.py`,
  `customer_router.py`, `tenant_engine/models.py` — cross-checked by an
  independent background research pass reaching identical conclusions on
  every point, plus several additional confirmed details (exact response
  dict literals, exact eligibility-gate order, exact error-code
  registration gap) folded into contract-matrix.md.
- Every client-side code path (schema parsing — success, null-rating,
  empty-badges, pricing-field-stripping, malformed-payload cases; badge
  mapping — all three known strings plus an unrecognized-string fail-safe
  case) is exercised by 10 new unit tests using fixtures shaped exactly
  like the real backend's actual response bodies (per the exact dict
  literals read from source, not guessed).
- Route promotion (`providerPreview` → real, `pricing` remains the dev-only
  next boundary) is exercised by 2 new route-registry tests.
- `npx tsc --noEmit`: 31 errors, 0 new (identical to the pre-sprint
  baseline — verified by diffing the error list, all 31 are in legacy
  `src/screens/*` files this sprint never touched).
- `npx jest`: 526/526 passing (516 carried forward + 10 new).
- `npx eslint src`: 0 errors, 36 pre-existing warnings (baseline
  unchanged).
- `npx prettier --check`: clean on every new/changed file.

## Honest Gate Impact

Per this sprint's own acceptance standard (identical to every previous
sprint's), this cannot claim a hard PASS: live runtime proof was not
possible in this environment, and several of the spec's aspirational proof
points (candidate-list comparison, ranking-position display,
availability-state display) describe backend capabilities that do not
exist in the real flow this app uses, so there is nothing for a live run
to prove for them even in principle. The gate decision reflects PARTIAL.

## What Would Close the Environment Gap

Run the actual backend (`uvicorn app.main:app`) against a seeded database
with: at least two tenants in the same city/zipcode, both passing the full
eligibility gate for the same `master_service_id` (to genuinely exercise
scoring/selection between real candidates, not just a single-candidate
trivial case), at least one tenant with `rating_average >= 4.5` and one
without (to exercise both badge-set variants), and a seeded zipcode with
zero eligible tenants (to genuinely trigger
`HOME_BOOKING_NO_PROVIDER_AVAILABLE` end to end). Authenticate a real test
customer, walk Home → Category → Service → Assistant → Draft → Media →
Address → Serviceability → Provider Preview end to end, observing both the
success and no-match screen states against real data.
