# Slice 2F-38 Scope Summary — Final Reconciliation, Role Cleanup and Application-Wide Certification

Slice 2F-38 implements no new canonical route. It is the final
reconciliation and certification slice, executed after 2F-35, 2F-36, and
2F-37 all complete. Its scope:

1. Final mounted mutation inventory (full re-enumeration, not a diff).
2. Canonical zero-gap proof, OR an exact enumerated list of remaining
   blockers if zero gap is not achieved.
3. Held-registry final reconciliation (every one of the original 59
   candidates must have a terminal disposition by the end of 2F-38).
4. Security-observation final disposition (every item in this slice's
   [critical-security-observation-map.csv](critical-security-observation-map.csv)
   and its successors in 2F-35/36/37 must be closed or explicitly
   deferred with a reason).
5. Migration 144 readiness proof (not application — see
   [migration-144-readiness-contract.md](migration-144-readiness-contract.md)).
6. Invalid-role account remediation (only canonical roles: super_admin,
   tenant_owner, staff, technician, customer, guest, admin_operations,
   admin_finance, admin_security, admin_readonly — no aliases).
7. `readonly@demo-ac-services.local` disposition (see
   [readonly-account-remediation-contract.md](readonly-account-remediation-contract.md)) —
   not touched before this slice.
8. Active-session handling for any role-remediated accounts.
9. Read-only mutation-enforcement proof (application-wide, not just the
   routes closed this program).
10. Final canonical role constraint application, only when safe.
11. Final canonical/matrix recount.
12. Application-wide authorization certification (scoped honestly —
    certifying what was actually closed, not implying every route in
    the application was reviewed if it wasn't).
13. Final deterministic regression (twice).
14. Final unresolved product-policy registry (carrying forward every
    `PRODUCT_DECISION_REQUIRED` item from 2F-34 through 2F-37 that
    remains undecided).

Full contract: [slice-2f38-certification-contract.md](slice-2f38-certification-contract.md).
