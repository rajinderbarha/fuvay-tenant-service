# CUSTOMER-L5-11 — Booking Creation Architecture

## Real Flow

```
valid, ready_for_confirmation booking_summary (/summary)
→ customer taps "Confirm booking"
→ stable idempotency key generated once (held for the lifetime of the screen)
→ POST /{draftId}/confirm  (Idempotency-Key + X-Idempotency-Key headers)
     → mark_ready_for_confirmation (real server-side preflight, skipped if already confirmed)
     → HomeServiceFinalCreationService.finalize()
         → CustomerBookingConfirmation dedup check (draft_type, draft_id)
         → generate booking_number / job_number
         → create ServiceBooking + ServiceJob
         → draft.status = "confirmed" + draft event
         → create CustomerBookingConfirmation lock row
         → audit log row
→ real booking_id / booking_number returned
→ navigation.reset() to BookingSuccess (pre-booking stack discarded)
→ GET /v1/customer/my-activity/bookings/{bookingId}  (canonical fetch, not the mutation response)
→ confirmation screen renders real ServiceBooking + ServiceJob data
```

## Ownership (per §6, confirmed against the real backend)

- **Pricing engine** (CUSTOMER-L5-09): provides the current estimate, already consumed by prior sprints.
- **Bargain/tier-choice** (CUSTOMER-L5-10): provides the negotiated price, already persisted into `draft.booking_summary`.
- **Booking engine** (`home_service_booking` + `final_records`, this sprint): runs the real preflight and creates the canonical `ServiceBooking`+`ServiceJob` transaction.
- **This client**: renders the review, submits the confirm action with a stable idempotency key, and renders whatever canonical result the backend returns — never computes, infers, or asserts a booking outcome itself.

This client never: generates a booking ID, marks a draft "booked" locally
before a real confirmed response, creates a service job independently, or
calculates any price total — verified by grep across
`features/booking-confirmation/` for any local ID generation, price
arithmetic, or optimistic status mutation (none found).

## Why This Sprint Uses `home_service_booking`'s Own `/confirm` (Not `final_records`'s Parallel Endpoint)

Two real, live endpoints both ultimately call the same
`HomeServiceFinalCreationService.finalize()` (contract-matrix.md). This
sprint uses `POST /{draftId}/confirm` (the `home_service_booking` router's
own endpoint) because it performs the real preflight
(`mark_ready_for_confirmation`) internally, in the same request — the
`final_records` parallel endpoint
(`POST /v1/customer/confirm/home-service-booking/{draftId}`) expects the
draft to already be `ready_for_confirmation` and has no dedicated
customer-facing endpoint of its own to get there. Using the
already-integrated single-call version avoids an unnecessary extra
round trip and matches how the backend's own router comments describe the
intended real flow.

## No Client-Side Transaction Reimplementation

Per §62's "Transactional Integrity" requirement: this client does not
attempt to verify partial-transaction invariants itself (e.g., "booking
created but draft still active") — that is a real, server-side guarantee
this sprint trusts (the DB-unique constraints on
`CustomerBookingConfirmation(draft_type, draft_id)` and
`ServiceBooking.draft_id` make a partial/duplicate outcome structurally
impossible under normal DB transaction semantics — verified by direct
source reading, not observed via a live transaction test, since no live
database was reachable this sprint — see runtime-evidence.md).

## Draft Closure

After a real `confirmed` outcome, this sprint invalidates the draft's
cached query entry (`useInvalidateDraftAfterBooking`) so no stale
"resume your draft" affordance can appear elsewhere in the app referencing
a now-terminal (`"confirmed"`) draft. This client does not delete any
local state the backend itself retains for audit purposes (the draft
row and its event log remain, server-side, exactly as `mark_ready_for_confirmation`'s
own docstring implies they should) — only the client-side query cache
entry is invalidated.
