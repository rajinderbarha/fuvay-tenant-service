# Route Denominator Reconciliation — Slice 2F-39A2

| Metric | After 2F-39A | After 2F-39A2 |
|---|---|---|
| Mounted route records | 2,320 | 2,320 (unchanged) |
| Unresolved route-method records | 229 | **149** (-80, this tranche) |
| Real authorization defects found | 0 (this tranche) | **7** (1 fixed, 6 flagged unresolved) |
| Read-path privacy observations recorded | 0 | 2 |

## By classification, this tranche's 80 routes (verified by counting the actual CSV, not estimated)

- `CANONICAL_TENANT_PROVIDER_MUTATION`: 41
- `PLATFORM_ADMIN_MUTATION`: 24
- `PRODUCT_DECISION_REQUIRED`: 7 (2 pricing + 5 security — the real
  unresolved findings, see `authorization-remediation-report.md`)
- `CUSTOMER_SELF_SERVICE_MUTATION`: 3
- `AUTHENTICATED_READ_ONLY`: 3
- `PUBLIC_OR_CALLBACK_MUTATION`: 2 (Razorpay webhooks)

Total: 41+24+7+3+3+2 = 80. Exact per-route detail in
`final-route-classification.csv` — this table is a rollup for
readability, not a substitute for the row-level evidence.

This slice does not attempt to update `verify_2f37.py`'s hardcoded
313/313, nor merge this tranche's canonical additions into a single
consolidated ledger with 2F-39A's 8 — that reconciliation is deferred
(see `deferred-items.md`).
