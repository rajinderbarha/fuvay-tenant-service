# Confirmation Semantics

## Disposition: PROVIDER_CONFIRMS_SERVICEABILITY / PROVIDER_ACCEPTS_BOOKING (NOT customer consent)

## Evidence

- `confirm_booking`'s router docstring: "Step 5: Confirm pending_confirmation booking —
  **tenant_owner only**."
- `BookingService.confirm_booking` explicitly denies the `customer` role: `if self.actor_role ==
  "customer": raise ServiceOSException("CUSTOMER_CANNOT_CONFIRM_BOOKING", ...)`.
- No customer-facing "confirm my booking" route exists anywhere in `booking/router.py` — the
  customer's only actions on a booking are create, cancel, and reschedule-request.
- The confirmation write itself: `b.confirmed_by_user_id = self.actor_id` (always the
  `tenant_owner`), `b.status = BS.CONFIRMED`, history reason `"Confirmed by tenant owner"`
  (literal string in source, `service.py:695`).
- `BS.CONFIRMED`'s only forward transitions are `[CONVERTED_TO_JOB, SCHEDULED, CANCELLED]` —
  operational progression, not a customer-facing state.

## Conclusion

`CONFIRMED` means **the tenant/provider has accepted the booking and confirmed they can service
it** (serviceability/capacity/business acceptance) — it does NOT mean the customer accepted
anything beyond their own initial booking request. This is `OPERATIONALLY_CONFIRMED_NOT_CUSTOMER_AUTHORIZED`
for the specific question of "does CONFIRMED prove NEW customer consent beyond what already
existed at booking-creation time" — but for `CUSTOMER_SELF_SERVICE_BOOKING`, the customer's OWN
act of creating the booking already IS their consent (they initiated it), so `CONFIRMED` on a
customer-originated booking is trustworthy relationship evidence (the customer wanted this
tenant's service; the tenant accepted). For `EXISTING_CUSTOMER_ASSISTED_BOOKING`, the customer
never took any action on this SPECIFIC booking at all — but as of this slice's fix, that mode can
only be used for a customer with an ALREADY-established relationship, so `CONFIRMED` there is
not being asked to prove customer consent from nothing; it's confirming an assisted extension of
an already-legitimate relationship.

## Why CONFIRMED remains the qualifying threshold (not a NEW field_ops concept)

No change was needed to `_assert_tenant_customer_relationship`'s own `QUALIFYING_BOOKING_STATUSES`
set (Slice 2F-14G) — the fix for the confirmation-provenance question lives entirely in
`create_booking` (who may even create a booking naming a given customer), not in what
`CONFIRMED` itself means. This matches the mission's explicit instruction: "Do not reopen
field_ops authorization or relationship logic unless this slice proves that a minimal connected
adjustment is required after Booking-engine closure" — no such adjustment was proven necessary.
