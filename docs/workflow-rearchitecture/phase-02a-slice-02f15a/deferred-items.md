# Deferred Items

The following were explicitly out of scope for Slice 2F-15A (per its mission's OUT OF SCOPE list) and remain deferred:

- Merging `Booking` with `ServiceBooking`, or `field_ops.Job` with `ServiceJob`.
- Any `PartsRequest` or `quote_checklist` changes.
- A tenant-customer directory, customer-contact model, or invitation/OTP/consent infrastructure (this would be the durable fix for the "legacy provenance" and "first assisted booking" tensions described in `product-decisions-required.md`).
- Any new migration, provenance column, role, or permission.
- Frontend/UI work of any kind (Booking pages, notifications, Exception Resolution, My Work aggregation, Next-Action aggregation).
- Remediation of the `readonly@demo-ac-services.local` account (confirmed untouched).
- Migration 144 (confirmed unapplied).
- Any module outside the Booking/field_ops relationship-authority chain audited by this slice.
