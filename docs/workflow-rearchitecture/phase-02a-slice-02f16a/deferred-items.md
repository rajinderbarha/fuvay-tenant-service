# Deferred Items

Per this slice's explicit OUT OF SCOPE list, the following remain deferred:

- A new Quote model; merging `ServiceJobQuote` with `field_ops.JobQuote`; merging `ServiceJob` with `field_ops.Job`; merging `Booking` with `ServiceBooking`.
- Any `PartsRequest` behavior change.
- Payment collection, refund behavior, PDF generation, quote versioning.
- Offline customer-approval infrastructure.
- Frontend/UI work of any kind.
- Any new permission, role, or alias.
- Any migration or new media infrastructure.
- My Work / Next-Action aggregation implementation.
- Booking Exception Resolution.
- Remediation of `readonly@demo-ac-services.local` (confirmed untouched).
- Application of Migration 144 (confirmed unapplied).
- Any module outside the quote-checklist/invoice-lineage chain audited by this slice.
- Discount-cap policy, `visit_charge`/`other` bucket coverage, quote expiry automation, optimistic concurrency fields (all documented in `product-decisions-required.md`).
