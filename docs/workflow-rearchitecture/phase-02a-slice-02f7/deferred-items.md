# Deferred Items — Slice 2F-7

Explicitly deferred, per the out-of-scope list and this slice's own
findings — none of these were investigated, designed, or acted on:

1. Modifying invoice/payment authorization or integrity.
2. Building invoice detail/payment forms; fixing the dead View Invoice
   link.
3. Beginning `admin_catalog.tenant_router` or `complaints.provider_router`.
4. Remediation of `readonly@demo-ac-services.local`.
5. Migration 144.
6. Merging `Booking`/`Job`/`ServiceBooking`/`ServiceJob`; Booking
   Exception Resolution; modifying booking creation.
7. Admin My Work; Tenant My Work; Next-Action aggregation.
8. Redesigning service-area pages; adding a map provider; changing
   pricing policy.
9. Introducing a canonical geography reference table (flagged, not
   built — see `product-decisions-required.md`).
10. Implementing district-level coverage.
11. Adding tenant-catalog-enablement validation to
    `add_service_mapping` (flagged, owned by `admin_catalog`).
12. Adding audit events to service-mapping mutations (flagged, not
    added).
13. Auditing/fixing `app/(tenant)/service-areas/page.tsx` (the `geo`
    module's zone UI) — a different backend module, never named in this
    mission.
14. Field-by-field audit of the service-area creation form's
    `coverage_type` option set.
15. Adding a new canonical role or alias.
16. Beginning a second router module.
17. Visual redesign.
