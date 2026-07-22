# Deferred Items

Per this slice's explicit OUT OF SCOPE list, the following remain deferred:

- Any provenance column, migration, or legacy-data remediation.
- A tenant-local customer directory, customer-contact model, or invitation/OTP/consent workflow.
- Merging `Booking` with `ServiceBooking`, or `field_ops.Job` with `ServiceJob`.
- Any `PartsRequest` or `quote_checklist` change.
- Any new role, alias, or permission.
- Frontend/UI work (Booking Exception Resolution, Admin/Tenant My Work, Next-Action aggregation).
- Remediation of `readonly@demo-ac-services.local` (confirmed untouched).
- Application of Migration 144 (confirmed unapplied).
- Any module outside the Booking creation-actor-binding/coverage chain audited by this slice.
- Database-level uniqueness constraints on `BookingStatusHistory`'s creation row (theoretical multiplicity risk, documented not fixed — see `known-limitations.md`).
