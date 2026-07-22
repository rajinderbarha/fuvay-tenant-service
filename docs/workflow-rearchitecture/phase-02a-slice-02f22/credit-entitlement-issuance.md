# Credit and Entitlement Issuance — Slice 2F-22

## Central finding: the purchase route issues nothing

`create_package_assignment` writes a selection row and an audit event. It
does not touch the wallet, the ledger, quotas, commission, or any
entitlement. Confirmed by source read and asserted by
`test_purchase_issues_no_wallet_credits`.

Every benefit flows from exactly one place:
`activate_tenant_package_assignment`, reachable only from
`tenant_engine/admin_service.verify_tenant` (admin approval).

## Effects at activation, and their authority

| Effect | Source of value | Condition |
|---|---|---|
| Wallet credit | `assignment.included_spendable_credits` (snapshot of `pkg.included_credit_amount`) | admin approval only |
| Storage quota | `pkg.storage_quota_gb` | admin approval only |
| Commission rate | `pkg.commission_rate` | admin approval only |
| `starts_at` / `expires_at` | `now()` + `validity_days` snapshot | admin approval only |
| Lead credits | `pkg.lead_credits` snapshot | recorded at selection; not spendable pre-approval |
| Security deposit | `pkg.security_deposit_amount` snapshot | recorded, remains non-spendable |

## Verification against each required property

- **Derived from authoritative package definition** — yes, all of the above.
- **Issued to the principal tenant only** — yes; `tenant_id` is the
  server-derived value throughout.
- **Issued only after the correct activation condition** — yes; admin
  approval is the sole trigger.
- **Never issued from client `mark_paid`** — now structurally impossible: the
  field is rejected at the schema, the handler passes `is_paid=False`
  literally, and the service refuses paid state without an authoritative
  `payment_authority`.
- **Exactly once** — `credit_wallet` is called with
  `idempotency_key=f"pkg-assign-credit-{assignment.id}"`, so a repeated
  activation of the *same* assignment cannot double-credit.
- **Repeated purchase call does not duplicate issuance** — a repeat purchase
  raises `PACKAGE_ALREADY_PENDING` before persistence; and even if a second
  pending row existed, activation selects `LIMIT 1`.
- **Double activation across two assignments** — prevented upstream:
  `verify_tenant` rejects any tenant not in
  `("not_started", "pending", "changes_requested")`, so approval is one-shot
  per tenant and `activate_tenant_package_assignment` runs at most once.
  This is the load-bearing guard for benefit non-duplication and was verified
  by reading `admin_service.verify_tenant`, not assumed.
- **Failed transaction leaves no partial entitlement** — see
  `no-partial-persistence-proof.md`.
- **Ledger and balance reconcile** — `credit_wallet` writes both atomically
  within the caller's transaction; unchanged by this slice.

## Reversal / refund

No refund or reversal path exists for package assignments. `rejected` is
terminal and issues nothing. Refund policy is an open product decision
(`product-decisions-required.md`); none was invented here.

## Tests
`TestNoActivationOrCreditIssuanceOnPurchase` (3 tests).
