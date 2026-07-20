# CUSTOMER-L5-10 — Runtime Evidence

## Live Backend Certification: NOT PERFORMED

Identical constraint to every previous sprint: this environment has no
running backend server, no reachable database, and no seeded
`BargainRule` data. None of the following were done:

- No real `POST /{draftId}/confirm-price-choice` request was made against
  a live server.
- No real tier confirmation (`low`, `mid`, or `high`) was observed
  producing a genuine `booking_summary` from a live backend.
- No real "change selection" (calling `confirm-price-choice` twice with
  different tiers on the same draft) was observed against a live server.
- No request IDs, status codes, or screenshots from a live run exist.

## What Was Verified Instead

- The exact real backend contract, via direct source-code reading of
  `home_service_booking/service.py`, `customer_router.py`, `constants.py`,
  `admin_catalog/bargain_engine.py`, `admin_catalog/models.py`
  (`BargainRule`), `admin_catalog/service.py`, `admin_catalog/admin_router.py`,
  `app/core/feature_flags.py`, `app/core/security.py` — cross-checked by
  an independent background research pass reaching identical conclusions
  on every point, including the decisive `MANUAL_BARGAIN_RULES_ENABLED`
  feature-flag finding.
- An exhaustive, repo-wide, case-insensitive grep for any
  bargain-session/offer/attempt/counteroffer persistence model or
  bargain-specific rate-limit/cooldown mechanism, confirming zero hits.
- Every client-side code path (schema parsing — real success shape, all
  three tier values, malformed-payload cases; state derivation — every
  real transition including preflight, loading, unavailable, choosing,
  confirming, confirmed, confirm-failed) is exercised by 13 new unit
  tests using fixtures shaped exactly like the real backend's actual
  response bodies (per the exact dict literal read from source).
- `npx tsc --noEmit`: 31 errors, 0 new (identical to the pre-sprint
  baseline).
- `npx jest`: 564/564 passing (550 carried forward + 13 new + 1 route
  registry rename).
- `npx eslint src`: 0 errors, 36 pre-existing warnings (baseline
  unchanged).
- `npx prettier --check`: clean on every new/changed file.

## Honest Gate Impact

Per this sprint's own acceptance standard, this cannot claim a hard PASS:
live runtime proof was not possible in this environment, and the
overwhelming majority of the spec's aspirational proof points (bargain
eligibility, session creation, counteroffer flow, attempt limits, rate
limiting, cooldown, session/offer expiry, negotiated-price-specific
expiry) describe capabilities that do not exist in this real backend at
all — verified exhaustively, not assumed. There is nothing for a live run
to prove for them even in principle. The gate decision reflects PARTIAL,
with the added honesty that this sprint's real scope is intentionally far
smaller than the spec's aspirational one, for backend-verified reasons
documented across every doc in this sprint's set.

## What Would Close the Environment Gap

Run the actual backend (`uvicorn app.main:app`) against a seeded database
with a real, active `BargainRule` (customer_min_price < customer_max_price,
non-zero platform_fee_percent) for the matched tenant's service. Walk
Home → Category → Service → Assistant → Draft → Media → Address →
Serviceability → Provider Preview → Pricing Estimate → Bargain end to end
on a real device, choosing each of the three tiers in separate runs to
confirm all three produce genuinely different `customer_offer` amounts,
and confirm "Change selection" followed by a different tier choice
correctly overwrites the prior one in the database (`draft.booking_summary`).
