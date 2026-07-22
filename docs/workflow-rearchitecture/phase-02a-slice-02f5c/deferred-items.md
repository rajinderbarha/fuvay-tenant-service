# Deferred Items — Slice 2F-5C

Explicitly deferred to a future slice/phase, per the user's out-of-scope
list — none of these were investigated, designed, or acted on:

1. `finance_hub.admin_router` modification (untouched — already closed
   in Slice 2F-5B).
2. Granting any `PACKAGES_*` permission to `admin_finance` or any other
   role beyond super_admin.
3. Granting any new credit, commission, or finance permission.
4. Adding a tenant finance role.
5. Applying tenant access-scope guards to any platform-only route in
   this module.
6. Remediation of `readonly@demo-ac-services.local`.
7. Migration 144.
8. Package or finance UI redesign.
9. Package pricing policy changes.
10. Commission policy changes.
11. Security-deposit policy changes.
12. Ledger-history rewrites or merging finance models (including not
    merging the `TenantWallet`/platform_commerce ledger with the
    `TenantBilling`/usage-credits ledger, despite both being called
    "credit" in places — documented as a distinct-capability finding,
    not acted on).
13. Payment-gateway behavior.
14. Booking/job pipeline changes, including not resolving the
    cross-pipeline commission-record risk documented in
    `alternate-commerce-route-audit.md` (lives in `platform_commerce`,
    out of scope).
15. Admin or Tenant "My Work" features.
16. Beginning any new router module beyond `package_commerce.admin_router`.
17. Visual redesign.
18. Deleting the 6 confirmed-orphaned `PackageCommerceService` methods.
19. Adding the missing audit events for feature/limit CRUD and
    `calculate_commission` (flagged, not added — see `known-limitations.md`).
20. Fixing the credit-wallet idempotency-key contract gap (flagged,
    `PRODUCT_DECISION_REQUIRED`).
