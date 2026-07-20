# CUSTOMER-L5-15 — Reschedule Policy Contract

## For the canonical booking (`ServiceBooking`/`ServiceJob`, home services)

**No reschedule capability exists at all** — not partially, not behind a
flag. Confirmed by an exhaustive grep for `reschedul` (case-insensitive)
across `execution/home_service_service.py`,
`execution/home_service_router.py`, every file in
`home_service_assignment/`, and every file in `final_records/`: zero
matches. `JOB_TRANSITIONS` (`execution/constants.py`) has no
reschedule-related target status. The only "reschedule" concept
anywhere in the `execution` engine is for the **coaching-appointment**
vertical (a different product line, not home services) — staff-initiated
only, no customer action, no re-validation of anything.

## For the disconnected legacy `booking` engine (reference only, NOT implemented client-side)

```
POST /v1/bookings/{booking_id}/reschedule/request   — customer, P.BOOKING_RESCHEDULE
POST /v1/bookings/reschedule/{id}/accept            — tenant only
POST /v1/bookings/reschedule/{id}/reject             — tenant only
```

- Request body: raw JSON `{requested_date, requested_slot, reason?}` —
  no Pydantic model, missing fields raise a raw `KeyError` rather than a
  422.
- `MAX_RESCHEDULE_COUNT = 3` — a 4th request raises a `"CONFLICT"` error
  with resolution text "Cancel and create a new booking."
- Creates a `BookingRescheduleRequest` row, `status: "pending"` until a
  tenant accepts/rejects.
- **Accept does not re-validate anything**: no serviceability recheck, no
  re-pricing, no re-bargain, no provider re-match. It directly overwrites
  `booking.preferred_date`/`preferred_slot` and increments
  `reschedule_count`.
- A standalone `GET /v1/bookings/tenants/{tenant_id}/slots/check`
  capacity-check endpoint exists but is never invoked by the accept flow
  — it's a disconnected, independently-callable check.
- No idempotency support, no version/concurrency field (same as
  cancellation).

## Why this is not implemented client-side

Same reason as cancellation: this engine's `Booking`/
`BookingRescheduleRequest` rows are keyed against a table the real
booking pipeline never populates. Even setting that aside, this
engine's reschedule flow does not implement any of the spec's required
serviceability/pricing/bargain/provider revalidation — it is a bare
date/slot swap. Building against it would satisfy neither the "real
endpoint" requirement nor the "real revalidation" requirement.

## What a correct backend fix would look like

A reschedule capability for the real `ServiceJob` pipeline would need,
at minimum: a customer-facing eligibility endpoint, a replacement-window
source tied to real capacity (none exists anywhere in the repository for
home-service jobs — the `slots/check` endpoint above is the closest
analog and is itself disconnected from any transactional reschedule
flow), and explicit orchestration re-invoking CUSTOMER-L5-07's
serviceability, CUSTOMER-L5-09/10's pricing/bargain, and the provider
matching engine. None of this exists today; this sprint does not
fabricate it.
