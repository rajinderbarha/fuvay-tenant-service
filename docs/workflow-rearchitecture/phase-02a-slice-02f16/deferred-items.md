# Deferred Items

Per this slice's explicit OUT OF SCOPE list, the following remain deferred:

- Building a new quote/pricing engine, customer quote UI, invoice/payment/refund infrastructure, media infrastructure, or PDF generation.
- Creating a new permission, role, or alias.
- Merging `field_ops.Job`/`ServiceJob`, or `Booking`/`ServiceBooking`.
- Moving `PartsRequest` into `field_ops.Job`, or merging quote_checklist with field_ops quote models or checklist templates.
- Redesigning pages, implementing Admin/Tenant My Work, Next-Action aggregation, or resolving Booking Exception Resolution.
- Remediating `readonly@demo-ac-services.local` (confirmed untouched) or applying Migration 144 (confirmed unapplied).
- Quote expiry automation, discount-cap pricing policy, Job-status effect for checklist completion, and optimistic-concurrency versioning — all deferred as open product decisions (see `product-decisions-required.md`).
- Unifying `QUOTE_NOT_FOUND`/`QUOTE_ACCESS_DENIED` into a single privacy-uniform error code.
