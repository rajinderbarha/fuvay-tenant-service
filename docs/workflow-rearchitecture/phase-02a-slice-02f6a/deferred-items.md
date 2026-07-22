# Deferred Items — Slice 2F-6A

Explicitly deferred, per the out-of-scope list — none of these were
investigated, designed, or acted on this slice:

1. Beginning `serviceability.router` or any other new module.
2. Modifying any previously-closed module beyond this one.
3. Granting `FIELD_OPS_INVOICE_GEN` to staff or technicians.
4. Introducing a new tenant role.
5. Payment-gateway processing / changing the on-site payment model /
   adding payouts.
6. Merging `Booking`/`Job`/`ServiceBooking`/`ServiceJob`.
7. Booking Exception Resolution.
8. Remediation of `readonly@demo-ac-services.local`.
9. Migration 144.
10. Invoice page redesign; Admin/Tenant My Work; unrelated frontend
    redesign; global monetization policy changes.
11. Frontend button-visibility correction for the Issue/staff-action
    controls (flagged, not made — see `frontend-exposure-audit.md`).
12. Adding an audit event to `add_item` (flagged, not added).
13. Deciding whether overpayment should ever create an account credit
    (flagged, not decided).
14. Blocking empty-invoice issuance (flagged, not conclusively proven as
    a defect).
15. Adding row-level locking to this module's mutation methods.
