# Deferred Items

- `booking/router.py`'s `add_note` persona/mutation-scope enforcement (product-decisions-required.md
  item 1).
- `cancel_booking`/reschedule route access-scope upgrades (item 2).
- Legacy pre-fix Booking data audit/remediation (item 3).
- Tenant-local customer directory, verified invitation workflow (carried over, unchanged).
- `BookingStatusHistory`-based cancelled/voided disambiguation (carried over, unchanged).
- Concurrency hardening for booking-creation relationship checks (known-limitations.md item 4).
- No second router/module begun, per the mission's explicit instruction.

With this slice, the specific customer-identity and confirmation-provenance vulnerability
disclosed in Slice 2F-14G (tenant self-mints a Booking for an unrelated customer, self-confirms
it, uses it as field_ops relationship evidence) is closed at its source: `create_booking` no
longer accepts an unvalidated or unrelated customer for the tenant-assisted path. The remaining
open items above are genuine product-scoping decisions or pre-existing, disclosed risk classes,
not newly-discovered security gaps.
