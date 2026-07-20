# CUSTOMER-L5-11 — Security Review

## Ownership Enforcement

- `/summary`, `/confirm`: both use the existing `_require_draft(draft_id,
  customer_id)` pattern (unchanged since CUSTOMER-L5-06) before any
  computation runs.
- `GET /bookings/{id}`: real ownership check
  (`booking.customer_id != customer_id → {"error": "FINAL_ACCESS_DENIED"}`),
  though returned as HTTP 200 rather than 403 — this client's
  `useBookingDetail` parses this specific shape and throws a categorized
  `ApiError` (`forbidden`) rather than treating the 200 status as success
  (contract-matrix.md).

## Critical Finding: `provider_snapshot` Requires Client-Side Stripping

`ServiceBooking.provider_snapshot` is confirmed to be the **raw,
unstripped** `draft.selected_provider_snapshot` — including
`internal_score`/`matching_score_snapshot`, fields `build_booking_summary`
strips server-side for its own `booking_summary.selected_provider` field,
but which `HomeServiceFinalCreationService.finalize()` copies verbatim
into the permanent `ServiceBooking` record without the same treatment
(baseline-verification.md finding #7). This client's
`bookingDetailSchema` deliberately reuses `matchedProviderSchema` (the
same 5-field-only schema L5-08 established) for `provider_snapshot` —
`z.object()`'s default unknown-key-stripping means these two internal
fields are structurally discarded the moment the response is parsed,
regardless of what the raw JSON contains. Verified by a dedicated test
(`booking-schema.test.ts`'s "strips internal_score/matching_score_snapshot"
case) that constructs a raw payload including both fields and asserts
they never survive parsing.

## No Client-Generated Identifiers

`booking_id`/`booking_number`/`confirmation_id`/`job_id`/`job_number` are
always read from the real backend response — this client never
constructs, formats, or guesses any of these values. Verified by grep:
no template-string construction of anything resembling `BK-`/`JOB-`
anywhere in `features/booking-confirmation/`.

## No Client-Side Canonical Acceptance

This client never marks a draft "booked" or shows a success state before
a real `booking_id` is present in a successful `/confirm` response — the
`confirmed` state requires `confirmMutation.isSuccess && confirmMutation.data`,
both backend-derived. The `uncertain` state (§30) explicitly does **not**
show success — it shows a calm, honest "checking" state.

## Idempotency Key Privacy

Never logged, never included in analytics, never rendered in any UI —
verified by grep across `use-confirm-booking.ts`/
`booking-confirmation-queries.ts` (see idempotency-contract.md).

## No Sensitive Logging

`booking_review_load_started/_failed`, `booking_create_started/
_succeeded/_failed`, `booking_create_timeout`, `booking_fetch_failed`,
`booking_confirmation_viewed`, `booking_return_home_selected` all pass
only booleans, reason-category strings, and (for `booking_offer_submit_started`-
style calls elsewhere) closed enum values — never a raw address, raw
customer notes (none exist in this flow), the idempotency key, or the
booking token concept (this backend has no separate "booking token" per
§23 — confirmed absent; the idempotency key itself is the closest real
analog, and it is never logged).

## No Production Mocks

Grepped `features/booking-confirmation/` for `mock`, `fake`, `TODO`,
`FIXME` — none found.

## Cross-Tenant/Cross-Customer Isolation

Relies entirely on the backend's own ownership checks (above). No new
client-side authorization logic was added. `useBookingDetail`'s query key
is locale/tenant-scoped (`cache-transition.md`), preventing any
plausible cross-tenant cache collision even before the backend's own
check would reject the request.

## No Direct-Payment Mutation

This sprint never initiates payment, collects payment details, or asserts
a paid/unpaid status beyond rendering the real, fixed `payment_mode`
string — verified by grep: no payment-collection UI, no card-input
component, no "mark paid" action exists anywhere in
`features/booking-confirmation/`.
