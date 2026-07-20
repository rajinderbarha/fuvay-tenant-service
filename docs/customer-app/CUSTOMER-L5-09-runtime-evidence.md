# CUSTOMER-L5-09 — Runtime Evidence

## Live Backend Certification: NOT PERFORMED

Identical constraint to every previous sprint: this environment has no
running backend server, no reachable database, and no seeded
`BargainRule`/`ServicePricingRule`/tenant data. None of the following were
done:

- No real `POST /{draftId}/match-and-price` request was made purely to
  observe the price-options fields (as distinct from L5-08's earlier
  observation of only the provider fields from the same endpoint).
- No real successful Low/Mid/High calculation against seeded
  `BargainRule` data was observed.
- No real `PRICE_OPTIONS_UNAVAILABLE` was triggered and observed against a
  live server (a tenant matched but lacking a configured customer price
  range).
- No real price revision was observed (e.g., an admin editing a
  `BargainRule`'s `customer_min_price`/`customer_max_price` between two
  customer-side refreshes, then confirming the client's "revised" banner
  fires against a genuine backend change).
- No request IDs, status codes, or screenshots from a live run exist.

## What Was Verified Instead

- The exact real backend contract, via direct source-code reading of
  `home_service_booking/service.py`, `matching_engine.py`, `constants.py`,
  `customer_router.py`, `admin_catalog/models.py` (`BargainRule`,
  `ServicePricingRule`), `admin_catalog/bargain_engine.py`,
  `pricing/models.py` (`CityTierConfig`) — cross-checked by an independent
  background research pass reaching identical conclusions, plus several
  additional confirmed details (exact `confirm-price-choice` request
  validation, exact `DRAFT_EXPIRY_HOURS = 24`, exact dead-code status of
  `bargain_enabled`, exact `price_status` update-site list) folded into
  contract-matrix.md/pricing-resolution.md.
- Every client-side code path (schema parsing — real range shape,
  field-stripping of market-comparison/admin data, malformed-payload
  cases; preflight — all five real precondition checks including draft
  expiry; state derivation — all state transitions including the
  first-vs-revalidation distinction and revision detection) is exercised
  by 24 new unit tests using fixtures shaped exactly like the real
  backend's actual response bodies (per the exact dict literals and
  formula read from source, not guessed).
- `npx tsc --noEmit`: 31 errors, 0 new (identical to the pre-sprint
  baseline).
- `npx jest`: 550/550 passing (526 carried forward + 24 new).
- `npx eslint src`: 0 errors, 36 pre-existing warnings (baseline
  unchanged).
- `npx prettier --check`: clean on every new/changed file.

## Honest Gate Impact

Per this sprint's own acceptance standard (identical to every previous
sprint's), this cannot claim a hard PASS: live runtime proof was not
possible in this environment, and several of the spec's aspirational
proof points (real city-tier influence on the rendered Low/Mid/High,
real quantity/unit effects, real SLA pricing effects, a real
`bargain_allowed` signal) describe capabilities that do not exist in the
real flow this app correctly uses, so there is nothing for a live run to
prove for them even in principle — see baseline-verification.md and
pricing-resolution.md for the full, honest accounting of why. The gate
decision reflects PARTIAL.

## What Would Close the Environment Gap

Run the actual backend (`uvicorn app.main:app`) against a seeded database
with: at least one active `BargainRule` (with `customer_min_price` <
`customer_max_price` and a non-zero `platform_fee_percent`) linked to the
matched tenant's `master_service_id`, to genuinely exercise a real
distinct Low/Mid/High range; a second scenario with a matched tenant that
has no such `BargainRule` (to genuinely trigger
`PRICE_OPTIONS_UNAVAILABLE`); and a live edit to the seeded `BargainRule`'s
price range between two customer-side "Refresh estimate" taps (to
genuinely exercise the revision-detection banner against a real backend
change, not just the client's own unit-test fixtures). Authenticate a
real test customer, walk Home → Category → Service → Assistant → Draft →
Media → Address → Serviceability → Provider Preview → Pricing Estimate end
to end, observing the real Low/Mid/High render, the refresh action, and
(if a second tenant with a different `BargainRule` is seeded) confirm a
different matched provider produces a genuinely different range.
