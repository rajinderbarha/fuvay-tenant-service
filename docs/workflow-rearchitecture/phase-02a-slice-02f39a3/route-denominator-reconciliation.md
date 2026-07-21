# Route Denominator Reconciliation — Slice 2F-39A3

| Metric | After 2F-39A2R | After 2F-39A3 |
|---|---|---|
| Unresolved route-method records | 149 | **0** |
| Real authorization defects found | 0 (this tranche) | 2 (both fixed) |
| Routes flagged for further verification (`PRODUCT_DECISION_REQUIRED`) | 0 | 21 |
| Read-path privacy observations | 4 (tracked in ledger) | 4 (unchanged) |

## This tranche's 149 routes by classification

75 `CANONICAL_TENANT_PROVIDER_MUTATION`, 39 `PLATFORM_ADMIN_MUTATION`, 21
`PRODUCT_DECISION_REQUIRED`, 9 `CUSTOMER_SELF_SERVICE_MUTATION`, 3
`AUTHENTICATED_READ_ONLY`, 1 `PUBLIC_OR_CALLBACK_MUTATION`, 1
`DEPRECATED_BUT_MOUNTED`. Total: 149.

## What "0 unresolved" does and does not mean

Every one of the 261 originally-unresolved routes now has exactly one
final classification — the mission's classification-completeness
criterion is met. It does **not** mean every one of those 261 is
confirmed safe: 21 are explicitly flagged as unverified
(`PRODUCT_DECISION_REQUIRED`), carrying a real, disclosed risk rather
than a false "done" signal. See `final-status-rationale.md` for why this
distinction determines the final status token.
