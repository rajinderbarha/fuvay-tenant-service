# Deferred Items — Slice 2F-8

Explicitly deferred, per the out-of-scope list and this slice's own
findings — none of these were investigated, designed, or acted on:

1. `admin_catalog.brand_provider_router`, `admin_catalog.recommendation_router`,
   `admin_catalog.service_option_provider_router` — confirmed structurally
   distinct, not begun.
2. `complaints.provider_router` — not begun.
3. Redesigning catalog pages, service setup, or consolidating catalog
   pages.
4. Fixing category naming/duplication (no directly-connected integrity
   defect was proven in this router requiring it).
5. Creating new categories/services; changing the canonical catalog
   hierarchy, pricing rules, or commission rules.
6. Introducing `tenant_manager` or any other role alias.
7. Reopening `serviceability` — the enablement/matching ambiguity does
   not meet the "all conditions proven" bar for a serviceability code
   change (see `tenant-catalog-enablement-contract.md`).
8. Investigating `app.engines.service_catalog` (the `ServiceCatalogItem`
   legacy model) in depth (flagged as a recommended future slice in
   `product-decisions-required.md`).
9. Adding an advisory lock to `enable_service` (flagged, not added).
10. Adding audit events to the 9 catalog-enablement mutations (flagged,
    not added).
11. Remediation of `readonly@demo-ac-services.local`.
12. Migration 144.
13. Merging `Booking`/`Job`/`ServiceBooking`/`ServiceJob`; Booking
    Exception Resolution.
14. Admin My Work; Tenant My Work; Next-Action aggregation.
15. Granting any new permission.
16. Beginning a second router module.
17. Visual redesign.
