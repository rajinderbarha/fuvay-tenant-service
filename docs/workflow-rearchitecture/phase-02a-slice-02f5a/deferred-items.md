# Deferred Items — Slice 2F-5A

## Product decisions (see product-decisions-required.md)
1. Whether `admin_finance` should be granted `FINANCE_PAYOUTS_*`.
2. Whether `admin_finance` should be granted `FINANCE_CLAIMS_*`.
3. Whether any role should be granted `PACKAGES_*`.
4. Whether the credit-wallet top-up idempotency contract should be
   hardened.
5. Whether `finance_hub`'s internal ownership mechanisms should be
   independently re-verified.

## Recommended next slice
A **product-decision-and-verification slice** for
`app.engines.finance_hub.admin_router` (see `next-module-scope-lock.md`):
resolve the `FINANCE_PAYOUTS_*`/`FINANCE_CLAIMS_*` grant question with a
product owner, then verify (not redesign) the existing guard composition
correctly enforces whichever decision is made. This is NOT a broad
tenant-mutation-guard slice like 2F-1 through 2F-4 — neither
`package_commerce.admin_router` nor `finance_hub.admin_router` has any
tenant-facing persona to guard.

## Not in scope for any future slice unless separately approved
Merging finance models, introducing payout behavior, redesigning finance
UI, changing the monetization model, granting permissions without an
explicit product decision, `readonly@` remediation, migration 144
application, modifying any of the 6 previously security-closed modules —
none touched, consistent with the brief's explicit exclusions.
