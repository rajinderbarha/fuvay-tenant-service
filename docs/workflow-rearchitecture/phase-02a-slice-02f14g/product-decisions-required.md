# Product Decisions Required

1. **`BookingService.create_booking`'s missing customer-existence validation** — a `tenant_owner`
   can supply an arbitrary `customer_id` with zero User-table validation (unlike `create_job`,
   which validates this). Whether/how to add this validation is a product/architecture decision
   for the booking engine, out of this slice's scope (confined to the `create_job` relationship
   helper).
2. **`BookingService.confirm_booking`'s unilateral tenant confirmation** — no customer
   participation is required to move a Booking to `CONFIRMED`. Whether to require some form of
   customer acknowledgment before confirmation counts as relationship evidence is a genuine
   product-policy question (see relationship-evidence-threat-model.md's "residual risk"), not
   something closeable via the `create_job` helper alone.
3. **Whether `BookingStatusHistory` should be queried** to distinguish a `cancelled`/`voided`
   Booking that WAS previously confirmed from one that never was — would allow `cancelled`/
   `voided` to qualify in the "previously confirmed" case, at the cost of an extra query and
   added complexity. Not implemented this slice (the current exclusion is safe, just possibly
   over-conservative for that specific sub-case).
4. **`TENANT_LOCAL_CUSTOMER_DIRECTORY_WITH_VERIFIED_LINKING`** (long-term target, carried over
   from Slice 2F-14F, unchanged).
5. Carried over, unchanged: `JobMedia` internal/customer-visible schema; legacy checklist
   deprecation; legacy quote-surface consolidation; `booking_id`/`parent_job_id` documented
   coexistence semantics; address derivation from booking; concurrency hardening.
