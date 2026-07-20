# CUSTOMER-L5-14 — Booking / Job Status Effects

Every quote-decision endpoint this client calls triggers a real,
immediate `ServiceJob.status` write via `_sync_job_status`
(`quote_service.py`):

| This client's action | `ServiceJob.status` becomes |
|---|---|
| approve | `quote_approved` |
| reject | `quote_rejected` |
| request revision | `quote_revision_requested` |

(For completeness, staff's own `send_to_customer` sets
`awaiting_customer_quote_approval` — this client never calls that
endpoint, but this is the status a booking is in immediately before this
screen has anything actionable to show.)

## Extension to `booking-status-registry.ts` (shared with L5-12/13)

All four strings added this sprint to the same centralized registry
`features/bookings/domain/booking-status-registry.ts` already used by
`BookingDetailScreen`/`BookingsListScreen` — a **third**, separate real
engine writing to the same `ServiceJob.status` column (after
`final_records`'s dead constants and `execution`'s live ones). Mapped as
`group: "active"` (none are terminal — a quote decision never ends the
job), with `warning: true` on `awaiting_customer_quote_approval` (needs
customer attention),`quote_rejected` and `quote_revision_requested`
(needs provider follow-up), and `success: true` on `quote_approved`.

## Why this client invalidates two different booking-detail caches

`features/booking-confirmation`'s `useBookingDetail` (used by this
sprint's own `useQuoteDecision` to resolve `job.id`) and
`features/bookings`'s own, separately-cached `useBookingDetail` (used by
`BookingDetailScreen`) are two independent React Query cache entries for
what is ultimately the same real `GET`. Both must be invalidated after a
successful decision so the status label the customer sees immediately
after acting (on `BookingDetailScreen`, after navigating back) reflects
the real new status rather than a stale cached one — see
`quote-queries.ts`'s `useInvalidateAfterDecision`.

## What does NOT change

The `ServiceBooking.selected_provider`/`selected_price_amount` fields
shown elsewhere on `BookingDetailScreen` are untouched by any quote
decision — the original agreed price (from CUSTOMER-L5-09/10) and this
quote's `customer_payable_amount` are two separate real amounts; this
client never adds them together or implies one supersedes the other,
since no source file read this sprint establishes that relationship.
