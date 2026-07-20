# Product Decisions Required

1. **Whether an existing tenant/customer relationship should be required** for the manual
   creation mode (`customer_id` supplied without `booking_id`/`parent_job_id`) — see
   manual-customer-authority.md. Not fixed, since no established relationship model exists and
   inventing one would break the evidenced "first contact" use case.
2. **Whether `booking_id`/`parent_job_id` should ever be allowed to coexist with explicit,
   documented semantics** (e.g. "a repair job that ALSO references the original consultation's
   booking") — currently rejected outright (see booking-parent-coexistence.md) since no such
   semantics were ever established.
3. **Whether `create_job` should derive `address` from a referenced booking** when the booking
   has one and the client didn't supply one — currently address remains independently
   client-supplied in all modes (see source-derived-field-matrix.csv). Not a security gap.
4. **Booking/parent concurrency hardening** — carried over from Slice 2F-14D, unchanged
   (`CONCURRENCY_RISK_DOCUMENTED`).
5. **Customer-consent recording, address normalization, tenant/customer directory design** —
   carried over from prior slices, unchanged, out of scope.
