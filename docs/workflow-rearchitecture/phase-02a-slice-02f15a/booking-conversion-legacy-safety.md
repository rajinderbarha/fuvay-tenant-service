# Booking Conversion Legacy Safety

`Booking.convert_to_job` (`app/engines/booking/service.py::BookingService.convert_to_job`) now runs, immediately after the existing duplicate-Job-for-booking guard and before staff-assignment validation:

1. Read the Booking's creation-history row (`BookingStatusHistory.changed_by_role` where `from_status IS NULL`).
2. If `changed_by_role == "customer"` — proceed unchanged (no additional query, no behavior change from pre-2F-15A).
3. If NOT `"customer"` (provider-created, or a legacy row with no recorded creator) — require independent relationship evidence per `independent-relationship-proof.md`. If absent, raise `CUSTOMER_TENANT_RELATIONSHIP_REQUIRED` (422) before any persistence.

This directly satisfies the mission's Workstream 10 mandate: *"Prevent untrusted legacy Bookings from converting into field_ops.Job."* A fabricated or provider-created Booking, however deeply confirmed, cannot become a Job unless independently backed by real customer-relationship evidence.

See `legacy-row-test-matrix.csv` for the specific test scenarios proving this (customer-created converts normally; provider-created with independent evidence converts; provider-created with none is rejected with zero persistence).
