# CUSTOMER-L5-11 — Runtime Evidence

## Live Backend Certification: NOT PERFORMED

Identical constraint to every previous sprint: this environment has no
running backend server, no reachable database, and no seeded
provider/pricing data. None of the following were done:

- No real `POST /{draftId}/summary` or `POST /{draftId}/confirm` request
  was made against a live server.
- No real `ServiceBooking`/`ServiceJob` row was ever observed created.
- No real duplicate-submit (two rapid taps, or a retry after a genuine
  timeout) was observed being deduplicated by the real
  `CustomerBookingConfirmation` unique constraint.
- No real two-device concurrent confirmation was observed.
- No real `GET /bookings/{id}` request was made against a live server.
- No request IDs, status codes, or screenshots from a live run exist.
- The rollback-on-exception behavior documented in
  `conversion-contract.md` is a source-code-level inference (standard
  SQLAlchemy async-session semantics), not an observed live transaction
  trace.

## What Was Verified Instead

- The exact real backend contract, via direct source-code reading of
  `home_service_booking/service.py`, `customer_router.py`,
  `final_records/creation_service.py`, `idempotency.py`, `models.py`,
  `number_service.py`, `constants.py`, `customer_router.py`,
  `app/exceptions.py`, `app/core/idempotency.py` — cross-checked by an
  independent background research pass that additionally surfaced the
  parallel `final_records` confirm endpoint, the app-wide
  `X-Idempotency-Key` middleware, and the legacy, unrelated `/v1/bookings`
  system this sprint correctly avoids.
- Every client-side code path (schema parsing — real ready/not-ready
  review shapes, real first-time/idempotent-retry confirm shapes, real
  found/error/malformed booking-detail shapes including the
  `internal_score`/`matching_score_snapshot`-stripping behavior; state
  derivation — every real review and confirm-failure-category transition)
  is exercised by 20 new unit tests using fixtures shaped exactly like
  the real backend's actual response bodies (per the exact dict literals
  read from source).
- `npx tsc --noEmit`: 31 errors, 0 new (identical to the pre-sprint
  baseline).
- `npx jest`: 584/584 passing (564 carried forward + 20 new).
- `npx eslint src`: 0 errors, 36 pre-existing warnings (baseline
  unchanged).
- `npx prettier --check`: clean on every new/changed file.

## Honest Gate Impact

Per this sprint's own acceptance standard, this cannot claim a hard PASS:
live runtime proof was not possible in this environment. Unlike
CUSTOMER-L5-10 (where most of the spec's aspirational model had no real
backend counterpart at all), this sprint's real backend capability is
substantial and closely matches the spec — the gap here is purely the
inability to observe it running (no live database/server), not an
absence of real capability to observe. The gate decision reflects
PARTIAL.

## What Would Close the Environment Gap

Run the actual backend (`uvicorn app.main:app`) against a seeded database
with a draft that has genuinely passed through the full real flow
(service → media → address → serviceability → match-and-price →
confirm-price-choice). Walk Home → ... → Bargain → Booking Review → tap
"Confirm booking" on a real device, observing: (1) a real `ServiceBooking`
+ `ServiceJob` row pair created with the expected `booking_number`
format; (2) the draft's `status` becoming `"confirmed"` in the database;
(3) a rapid double-tap or a forced network interruption immediately after
tapping Confirm, followed by "Check status," confirmed to return the
exact same `booking_id` rather than creating a second row; (4) the
confirmation screen rendering the real `GET /bookings/{id}` response, not
a stale mutation-response fallback; (5) a second device (or a second app
instance) attempting to confirm the same already-confirmed draft,
confirmed to receive `idempotent: true` with the same booking rather than
an error or a duplicate.
