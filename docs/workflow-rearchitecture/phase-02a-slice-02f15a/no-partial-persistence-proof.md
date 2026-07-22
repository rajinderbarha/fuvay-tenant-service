# No-Partial-Persistence Proof

Every new rejection path added this slice raises its `ServiceOSException` BEFORE any `db.add`/`db.flush`/`db.commit` call:

- `FieldOpsService._assert_tenant_customer_relationship` (tightened predicate) — raises before `create_job` reaches its `db.add(Job(...))` call.
- `FieldOpsService.create_job`'s new independent-evidence block (`booking_id` path) — inserted before the final `customer_id` validation block and well before any `db.add` call in the method.
- `BookingService.create_booking`'s tightened relationship check — raises before the `db.add(Booking(...))` call later in the method.
- `BookingService.convert_to_job`'s new independent-evidence block — inserted before staff-assignment validation and the `db.add(FieldJob(...))` call.

All corresponding new tests (`test_provider_created_qualifying_booking_no_longer_qualifies`, `test_chain_of_provider_created_bookings_cannot_bootstrap`, `test_provider_created_booking_without_independent_evidence_rejected`) assert `db.add.assert_not_called()` on the rejection path, confirming zero partial persistence.
