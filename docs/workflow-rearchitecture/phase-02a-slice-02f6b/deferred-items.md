# Deferred Items — Slice 2F-6B

Explicitly deferred, per the out-of-scope list and this slice's own
findings — none of these were investigated, designed, or acted on:

1. Building the invoice detail page / any of the 4 mutation forms
   (out of scope: "do not redesign the invoice interface").
2. Fixing the dead "View Invoice" row-action link.
3. Modifying invoice/payment backend authorization, amount validation,
   or invoice state transitions.
4. Granting `FIELD_OPS_INVOICE_GEN` to staff, or any new permission.
5. Adding a new role (`office_staff`, `manager`, `tenant_manager`,
   `tenant_finance`, or any other alias).
6. Beginning `serviceability.router` or any other new module.
7. Remediation of `readonly@demo-ac-services.local`.
8. Migration 144.
9. Invoice page redesign; color/theme/layout/component changes.
10. Payment-gateway processing; on-site payment policy changes;
    discounts; payouts.
11. `Booking`/`Job`/`ServiceBooking`/`ServiceJob` ownership changes.
12. Admin or Tenant My Work.
13. Formally adopting a frontend test framework (flagged, not done).
14. Deciding whether/when to build the missing invoice UI (flagged, not
    decided — see `product-decisions-required.md`).
