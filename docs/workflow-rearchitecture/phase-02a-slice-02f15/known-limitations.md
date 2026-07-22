# Known Limitations

1. **Legacy pre-fix Bookings are not retroactively audited.** Any Booking created via the
   previously-unvalidated tenant-assisted path (before this slice's deployment) that reached
   `CONFIRMED`-or-later status could still exist in the database with no genuine customer
   relationship, and would still be usable as `field_ops` relationship evidence (since
   `_assert_tenant_customer_relationship` only checks structural fields, not creation history).
   No migration or data audit was performed — disclosed, not silently ignored (see
   product-decisions-required.md item 3).
2. `booking/router.py`'s `add_note`, `cancel_booking`, `accept_reschedule`, `reject_reschedule`,
   `request_reschedule` remain unprotected/access-scope-unaware — explicitly out of this slice's
   create/confirm/convert scope (product-decisions-required.md items 1-2).
3. `booking_preflight` was not modified (read-only, no persistence — correctly out of scope).
4. Concurrent booking-creation race window (two simultaneous assisted-booking requests for the
   same not-yet-related customer) is not specifically addressed — the relationship check and the
   Booking insert are not wrapped in a transaction-level lock. This is the same
   `CONCURRENCY_RISK_DOCUMENTED` class already disclosed in Slices 2F-14D/E/G, unchanged.
5. Tenant-local customer directory, verified invitation workflow, `BookingStatusHistory`-based
   cancelled/voided disambiguation — all carried over from prior slices, unchanged.
