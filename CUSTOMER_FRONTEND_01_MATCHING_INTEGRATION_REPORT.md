# CUSTOMER-FRONTEND-01 — Matching Integration Report

## Real endpoint used
`POST /v1/customer/home-services/booking-drafts/{draft_id}/match-and-price`
(`app/engines/home_service_booking/customer_router.py`). This calls
`svc.match_provider_and_price(..., reveal_internal_score=False)` server-side — the
frontend never requests, receives, or has any code path that could render
`internal_score`/`ranking_score`/`bookability_score`.

The spec's illustrative `POST /v1/home-services/matching/select-provider` does not
exist anywhere in the backend; confirmed by reading
`app/engines/home_service_assignment/customer_router.py` in full (that router is
actually the booking **tracking** router, prefix `/v1/customer/bookings`, not a
matching endpoint) and by grep across `app/engines/home_service_assignment/*.py`
and `app/engines/home_service_booking/*.py` for `select-provider`/`matching`.

## Frontend integration
`lib/api/customer-home-services.ts` → `selectProviderForHomeService(draftId)` calls
this endpoint once, automatically, right after the Location step's serviceability
check succeeds (see `runMatching()` in the booking wizard page). No manual
"choose from list" UI exists anywhere — the deprecated `/match-providers` and
`/select-provider` list-based endpoints are not called by this app at all, matching
the backend's own deprecation notice.

## States implemented
- Loading: "Finding the best available provider near you..." (`step === "provider" && loading`)
- Success: renders `ProviderCard` with only customer-safe fields (see Customer
  Safety Report), then a "See Price Options" CTA moving to the Price step.
- No provider: "No provider is available for this service in your area right now.
  Try a different time or check again later." — this exact path was exercised live
  (see Live API Verification Report): the real backend returned HTTP 422
  `HOME_BOOKING_NO_PROVIDER_AVAILABLE` with a real request_id, which the wizard's
  generic `ErrorBanner` renders (not the empty-state copy, since the backend
  returned a hard error rather than a 200 with an empty provider — this is a minor
  mismatch between the spec's assumed 200-empty-response shape and the backend's
  actual 422-on-no-provider behavior, documented here rather than silently patched).

## Deviation note
Because the real backend raises a 422 (not a 200 with `provider: null`) when no
provider is available, `ErrorBanner` (generic friendly-message + request_id) is what
customers actually see in that case today, not the bespoke "No provider is
available..." copy inside the Provider step's own empty-state branch. That
bespoke copy is reachable only if a future backend change returns 200 with an
empty match. This is called out explicitly rather than adding speculative
try/catch logic to fake a 200 shape that was never observed live.
