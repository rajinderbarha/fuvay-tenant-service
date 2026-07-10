# CUSTOMER-FRONTEND-01 — Review UI Report

Implemented in `frontend/customer-app/app/customer/bookings/[bookingId]/rate/page.tsx`,
calling the real:
- `POST /v1/customer/bookings/{booking_id}/rating`
- `GET /v1/customer/bookings/{booking_id}/rating`

from `app/engines/home_service_assignment/customer_router.py`.

## Fields implemented vs spec
Spec asked for: rating 1-5, comment optional, quality tags optional,
would-recommend yes/no optional, photo optional, Submit.

The **real backend** `submit_booking_rating` handler only accepts `rating` (int
1-5, required) and `comment` (optional string) in its request body — it builds
a fixed internal `signals` dict (overall_quality/punctuality/cleanliness/
value_for_money/communication, all set to the same rating value) rather than
accepting separate quality tags, a would-recommend flag, or a photo. Building
UI controls for quality tags / would-recommend / photo would mean collecting
data the backend silently discards, which is worse than not offering it, so
this app implements only rating (1-5 stars) + optional comment, matching what
is genuinely wired. Documented as a spec-vs-backend gap, not silently dropped.

## Gating rules verified against source
- `booking.status != "completed"` → backend raises `BOOKING_NOT_COMPLETED` (422)
  with message "You can review this service after it is completed." — the
  frontend's own pre-check (`booking.status !== "completed"`) short-circuits to
  the same message before even attempting submission, and the real error, if it
  ever reaches the client (e.g. race condition), is shown via `ErrorBanner`
  (generic + request_id) since it's a `CustomerApiError`.
- Duplicate review → backend raises `REVIEW_ALREADY_SUBMITTED` (409). The
  frontend also proactively calls `getCustomerBookingReview()` on page load and
  shows "A review has already been submitted for this booking." if one exists,
  without requiring the user to hit Submit and get an error first.
- Ownership: the backend's own `booking.customer_id != customer_id` check
  returns 404 `BOOKING_NOT_FOUND` (not the review-specific codes), and the
  frontend has no client-side ownership check of its own — it fully defers to
  the backend, which is correct (never trust a client-side ownership gate).

## Not live-tested
No genuinely completed booking exists in this dev DB in the time available
(the only draft created during live verification never reached `confirm` because
matching returned no provider), so submission of a real review was **not**
observed end-to-end. See CUSTOMER_FRONTEND_01_LIVE_API_VERIFICATION_REPORT.md.
