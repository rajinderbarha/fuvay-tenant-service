# Transaction, Idempotency, and Concurrency — Workstream 10

## Package lifecycle (create/update/delete/activate/deactivate/clone/features/limits)
Single `flush()` + audit per call, commit managed by the outer request
session (same platform-wide pattern noted in Slice 2F-5B). No row locking.
Concurrent double-create of the same package name is possible in theory
(slug-collision handling exists — a duplicate slug gets a random suffix
appended rather than erroring — so this is a non-issue for `create_package`
specifically). No other duplicate-mutation risk applies to definition-only
mutations (idempotent toggles, or safe repeats).

## `admin_purchase_package` / `create_package_assignment`
- Explicit `await db.commit()` in the router after the service call
  (distinct from most other package_commerce routes, which rely on
  request-scoped auto-commit) — confirmed via source read of
  `admin_router.py:364`.
- Duplicate-assignment protection via the `PACKAGE_ALREADY_PENDING`
  status-set query (re-verified, see `package-assignment-integrity.md`).
- No row locking on the duplicate-check query — a genuine simultaneous
  double-submit (both requests passing the existence check before either
  flushes) is theoretically possible, consistent with the platform-wide
  lockless pattern already documented for `finance_hub` in Slice 2F-5B.
  Not fixed here (same rationale: platform-wide pattern, not unique to
  this module, no maker-checker/locking redesign requested).

## Credit-wallet adapter (`admin_topup_wallet` / `admin_adjust_wallet`)
**Better than the platform-wide default**: `UsageCreditService._post`
takes an explicit `with_for_update()` row lock on the `TenantBilling` row
before computing `balance_after` — genuine row-level concurrency
protection, re-verified via direct source read
(`usage_credits/service.py:129-132`). Concurrent top-ups/adjustments for
the same tenant serialize correctly. The idempotency-key gap (see
`credit-wallet-adapter-integrity.md`) is a distinct issue from
concurrency — it concerns *retries*, not *simultaneous* requests, and is
not mitigated by the row lock (two different random keys both pass the
dedup lookup and both acquire the lock sequentially, each posting a
distinct ledger entry).

## Commission (`admin_calculate_commission` / `admin_deduct_commission`)
- `calculate_commission`: job_id-uniqueness dedup query, no row lock —
  two simultaneous first-time calls for the same `job_id` could both pass
  the "does a record exist" check before either flushes, in theory
  creating two `CommissionRecord` rows for one job (a genuine, if narrow,
  race). Not exploitable in practice by anyone but `super_admin` (the
  only role that can reach this endpoint), and no evidence of a unique
  DB constraint on `job_id` was found to rely on for a fix without
  a migration — **documented, not fixed**, since closing it correctly
  would require a schema-level unique constraint (a migration), which is
  out of scope.
- `deduct_commission`: dual protection (status guard + stable
  `debit_wallet` idempotency key `commission-deduct-{record.id}`) makes
  a double-deduction race much narrower than the calculate-side race
  above — the underlying `debit_wallet` ledger primitive's own
  idempotency-key check (same mechanism as `usage_credits`) is the actual
  backstop.

## Explicitly looked for and not found
- Duplicate package assignment beyond the already-covered pending-status
  race (no other path creates `TenantPackageAssignment` rows in this
  module).
- Package activated without required ledger update: `create_package_assignment`
  explicitly does NOT touch the ledger ("Wallet credits are NOT added
  here" — by design, not a partial-commit bug).
- Ledger entry without a matching package assignment: the credit-wallet
  adapter routes are entirely independent of package assignment (they
  operate on the tenant's usage-credit ledger directly, unrelated to
  `TenantPackageAssignment`) — not a defect, just two unrelated
  capabilities living in the same router file.
- Partial transaction commits: no code path was found that commits a
  ledger write without also committing its accompanying record update in
  the same request.

## Conclusion
Row locking exists where it matters most (the credit ledger, via
`UsageCreditService`) but not for package-assignment or commission-
calculation dedup queries — an honest, pre-existing, platform-wide gap.
No conclusively provable, uniquely-package_commerce concurrency defect
requiring a code change was found.
