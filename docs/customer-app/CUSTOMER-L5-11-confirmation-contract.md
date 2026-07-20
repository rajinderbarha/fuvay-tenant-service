# CUSTOMER-L5-11 — Confirmation Contract

## Backend Field → Customer-Facing Label

| Backend field (`GET /bookings/{id}`) | Customer-visible label | Ownership | Privacy classification |
|---|---|---|---|
| `booking_number` | "Booking reference" | Real, backend-generated (`BK-YYYYMMDD-NNNNNN`) | `CUSTOMER_VISIBLE` |
| `status` | Drives the next-step guidance sentence (see below) | Real, backend-owned | `CUSTOMER_VISIBLE` |
| `address_snapshot` | "Address" | Real, copied verbatim from the draft at confirm-time | `CUSTOMER_VISIBLE` |
| `preferred_time_window` | "Preferred time" | Real | `CUSTOMER_VISIBLE` |
| `provider_snapshot` | "Provider" (name + rating only rendered) | Real, but **requires client-side stripping** — see security-review.md | Mixed: `CUSTOMER_VISIBLE` (name/rating/badges) + structurally-excluded `INTERNAL_ONLY` (`internal_score`/`matching_score_snapshot`) |
| `price_snapshot.selected_price_amount` | "Price" | Real, the exact tier-derived amount confirmed in CUSTOMER-L5-10 | `CUSTOMER_VISIBLE` |
| `price_snapshot.payment_mode` | Payment-policy note | Real, fixed value | `CUSTOMER_VISIBLE` |
| `job` (id/job_number/status) | Not separately rendered this sprint | Real (fetched, parsed, unused in UI) | N/A — no job-lifecycle UI this sprint (explicit scope exclusion) |

## Next-Step Guidance — Only Real, Observed Statuses Are Mapped

Per §37's explicit instruction ("Only show statements supported by the
actual lifecycle... Do not promise instant assignment"), this sprint maps
exactly the five real `ServiceBooking`/`ServiceJob` status literals found
in `final_records/constants.py` (`BOOKING_STATUS_*`) to a next-step
sentence:

| Status | Copy |
|---|---|
| `pending_assignment` (the only status a freshly created booking actually has) | "The provider will review your booking next." |
| `assigned` | "A technician has been assigned to your booking." |
| `in_progress` | "Your service is in progress." |
| `completed` | "Your service has been completed." |
| `cancelled` | "This booking was cancelled." |
| any other/unrecognized value | A generic fallback ("You will receive an update when your booking status changes.") — fails safe rather than showing nothing or a raw status string |

Since this sprint never builds technician-assignment/job-lifecycle UI, the
`assigned`/`in_progress`/`completed`/`cancelled` mappings exist for
forward-compatibility (a future sprint's backend changes could
theoretically return a booking already past `pending_assignment` if the
customer navigates here after some delay) but are not expected to be
exercised by this sprint's own real, freshly-created-booking flow, which
always observes `pending_assignment`.

## Canonical Data, Not the Mutation Response

Per §45, `BookingConfirmationScreen` renders **only** `useBookingDetail`'s
(`GET /bookings/{id}`) result — the `/confirm` mutation's own response is
used solely to obtain `booking_id` for navigation
(`BookingReviewScreen`'s `navigation.reset(...)` call) and is discarded
immediately afterward; it is never itself rendered on the confirmation
screen.

## Navigation Reset

Per §52, a successful confirmation calls `navigation.reset({index: 0,
routes: [{name: "BookingSuccess", params: {bookingId}}]})` — the entire
pre-booking stack (BookingReview, Bargain, Pricing, ProviderPreview,
ServiceabilityCheck, AddressSelection, ...) is discarded. Pressing back
from the confirmation screen has nowhere stale to return to; "Return home"
performs a second `reset` to `Home`.

## Test Coverage

`booking-schema.test.ts` covers the real found/error/malformed response
shapes and the internal-field-stripping behavior for `provider_snapshot`.
Next-step status-mapping itself is a plain object lookup with no branching
logic worth a dedicated unit test beyond what schema parsing already
covers (consistent with this project's established "no
component/render tests" deprioritization for screen-level display logic).
