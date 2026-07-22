# Duplicate and Idempotency Policy — Slice 2F-22

## Observed policy (not invented)

**`DUPLICATE_REJECTED`** for sequential requests, with a residual
**`CONCURRENCY_DEFECT_CONFIRMED`** under exact concurrency that cannot
duplicate benefits.

The guard is pre-existing (added by MODULE-L5-30), unchanged by this slice:

```
existing = SELECT ... WHERE tenant_id = :tid AND package_id = :pid
           AND status IN ('selected','pending_review','pending_payment',
                          'paid_pending_approval')
if existing: raise PACKAGE_ALREADY_PENDING
```

| Scenario | Behavior |
|---|---|
| Repeated pending purchase (sequential) | `PACKAGE_ALREADY_PENDING`, raised **before** persistence |
| Browser retry / double-click | same — rejected |
| Repeated paid purchase | same guard (paid states are in the status list) |
| Multiple *different* packages | ALLOWED — one pending selection per (tenant, package), not per tenant |
| Retry after rejection | ALLOWED — `rejected` is not in the guard's status list, so a tenant may re-select after an admin rejection |
| Concurrent identical requests | **TOCTOU race** — see below |

## The concurrency gap, stated honestly

The guard is SELECT-then-INSERT with no unique constraint and no row lock.
Two simultaneous requests can both pass the check and create two
`pending_review` rows for the same (tenant, package).

**Why this does not duplicate benefits**, traced end to end:

1. `activate_tenant_package_assignment` selects its candidate with
   `LIMIT 1` — one activation per call.
2. That function is reachable only from `verify_tenant`, which rejects any
   tenant whose `verification_status` is not one of
   `("not_started", "pending", "changes_requested")`. After the first
   approval the status is `approved`, so a second approval raises
   `TENANT_VERIFICATION_INVALID_STATUS`.
3. Therefore activation runs **at most once per tenant**, and the second
   duplicate row is never activated.

Consequence of the race is a **stale orphan `pending_review` row**, not
duplicated credits, quota, or money.

## Why it was not fixed this slice

The correct fix is a partial unique index on
`(tenant_id, package_id) WHERE status IN (...)`, which requires a migration.
This slice is explicitly prohibited from adding or applying migrations.

An application-level `SELECT ... FOR UPDATE` would not help: there is no
existing row to lock in the racing case.

Recorded in `known-limitations.md` and `product-decisions-required.md`.

## Policies NOT invented

Per the mission's prohibition, this slice did not invent renewal, stacking,
upgrade, replacement or idempotency-key semantics. The observed model is:
one pending selection per (tenant, package); multiple distinct packages
permitted; no renewal or stacking concept exists in code.

## Tests
`TestDuplicatePurchaseGuard` (2 tests); concurrency row in
`financial-integrity-test-matrix.csv`.
