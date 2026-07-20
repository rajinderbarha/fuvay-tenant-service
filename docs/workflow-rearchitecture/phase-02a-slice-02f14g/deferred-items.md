# Deferred Items

- `BookingService.create_booking`'s customer-existence validation gap (product-decisions-required.md
  item 1) — a genuine, disclosed architectural gap in the booking engine, out of this slice's
  scope.
- `BookingService.confirm_booking`'s unilateral confirmation gap (item 2) — same reasoning.
- `BookingStatusHistory`-based disambiguation of cancelled/voided bookings (item 3).
- `TENANT_LOCAL_CUSTOMER_DIRECTORY_WITH_VERIFIED_LINKING` (long-term target, unchanged).
- `JobMedia` internal/customer-visible schema, legacy checklist deprecation, legacy quote-surface
  consolidation, `booking_id`/`parent_job_id` documented coexistence semantics, address
  derivation from booking, concurrency hardening — all carried over, unchanged.
- No second router module begun, per the mission's explicit instruction.

With this slice, the `create_job` relationship-evidence provenance gap (the trivial low-trust
Booking bootstrap and legacy-Job grandfathering risk) is closed. The remaining residual risk
(self-confirmation of a fabricated booking) is a genuine architectural gap in the booking engine
itself, explicitly out of this slice's scope, and is honestly disclosed rather than silently
left unaddressed or falsely claimed as closed.
