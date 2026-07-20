# Alternate Commerce Route Audit — Workstream 13

## Package definitions and assignment
No alternate route was found that writes `ServicePackage`,
`PackageFeature`, `PackageLimit`, or `TenantPackageAssignment` outside
`package_commerce.admin_router` and `package_commerce.tenant_router`.
Both are `package_commerce`'s own intentional, persona-specific entry
points into the same canonical `create_package_assignment` service
method (see `package-assignment-integrity.md`).
**Disposition: SHARED_CANONICAL_SERVICE** (not a duplicate — intentional
dual-persona design).

## Security deposits
Canonically owned by `finance_hub.admin_router` (Slice 2F-5B, unchanged
this slice). `package_commerce`'s own 3 mutation routes for
`SecurityDeposit` are blocked (410) and their backing service methods are
uncalled dead code. **Disposition: DEPRECATED_410** (re-confirmed, not
`BLOCKS_SECURITY_CLOSURE` — the weaker write path is inert, not live).

## Credit ledger
Canonically owned by `UsageCreditService` / `UsageCreditLedger` +
`TenantBilling`. `package_commerce.admin_router`'s 2 credit-wallet routes
(`admin_topup_wallet`, `admin_adjust_wallet`) are thin adapters directly
over this same canonical service (re-verified this slice, see
`credit-wallet-adapter-integrity.md`). **Disposition: CANONICAL_PLATFORM_WRITE**
(the adapter posts to the one true ledger, not a parallel one).

A **separate**, older ledger exists: `platform_commerce.ledger`'s
`credit_wallet`/`debit_wallet` primitives, writing to `TenantWallet`
(a *different* table from `TenantBilling`/`UsageCreditLedger`). This is
used by `package_commerce`'s own `deduct_commission`/`calculate_commission`
(via `_get_wallet`, reading `TenantWallet`) and by `platform_commerce.CommerceService`'s
own credit/debit/commission methods. This is a **pre-existing, dual-
ledger architecture** (`TenantWallet`-based "platform_commerce ledger" for
commission/wallet operations vs. `TenantBilling`/`UsageCreditLedger`-based
"usage credits" for the admin credit-wallet adapter and topup/adjust
operations) — not introduced by this slice, and merging these two ledgers
is explicitly out of scope ("do not merge finance models"). **Disposition:
DISTINCT_CAPABILITY** (two genuinely different ledger domains — usage
credits vs. commission/wallet balance — that happen to share the word
"credit" but are architecturally separate; re-verified this is the
existing, intentional shape, not an accidental duplication).

## Commission
`package_commerce.admin_router`'s `admin_calculate_commission`/
`admin_deduct_commission` write to `CommissionRecord` (imported from
`platform_commerce.models`) via `debit_wallet`/`credit_wallet`
(imported from `platform_commerce.ledger`) — i.e., they operate on
**the exact same table and ledger primitives** as `platform_commerce.CommerceService`'s
own `deduct_commission` (called from `platform_commerce/router.py`,
`platform_commerce/billing_router.py`, and `field_ops/billing_service.py`
as the real job-completion commission pipeline), and as
`invoice_payment.commission_service.ServiceCommissionService` (called
automatically from `invoice_payment/payment_service.py` on invoice
payment).

Three independent commission-deduction code paths write to the same
`CommissionRecord` table, all keyed on `job_id` uniqueness:
1. `package_commerce.PackageCommerceService` (two-step: calculate then
   deduct) — reachable only via this slice's `require_super_admin`-gated
   router, zero live frontend/pipeline caller found.
2. `platform_commerce.CommerceService` (one-step: calculate+deduct
   inline) — reachable via `platform_commerce/router.py`,
   `platform_commerce/billing_router.py`, and `field_ops`'s real
   job-completion billing flow.
3. `invoice_payment.ServiceCommissionService` — reachable via the real
   invoice-payment flow.

All three dedupe on `job_id` against the same table, so calling any one
of them first "claims" that `job_id` for all three (the others' own
existence checks will see the row and treat it as already-processed).
This makes accidental **double-deduction across pipelines** unlikely
(the shared table + shared key is itself a safety net) but raises a
subtler risk: `platform_commerce.CommerceService.deduct_commission`
treats "a `CommissionRecord` row already exists for this job_id" as
equivalent to "already fully deducted" and returns early
(`idempotent: true`) — but `package_commerce`'s own `calculate_commission`
creates a `status="pending"` record *without* debiting the wallet. If an
operator called `package_commerce`'s `calculate-commission` for a
`job_id` first, and then the real pipeline (`platform_commerce`/
`field_ops`) later tried to process that same `job_id`, the real
pipeline would silently no-op (report "idempotent") without ever
actually debiting the wallet for that job.

**This is a genuine cross-module risk, but it lives in
`platform_commerce.service`'s own `deduct_commission` logic (its
early-return doesn't distinguish `status="pending"` from
`status="deducted"`), not in `package_commerce.admin_router`.** Fixing it
would require modifying `platform_commerce.service` — explicitly a
different module than this slice's mission target. **Disposition:
DISTINCT_CAPABILITY, with a documented cross-module risk** — not
`BLOCKS_SECURITY_CLOSURE` because (a) `package_commerce`'s own commission
routes have zero live callers today (confirmed via frontend/pipeline
grep), so the risk is latent/manual-only, not exercised by real traffic,
and (b) the module actually in scope for this slice (`package_commerce`)
has no defect of its own — its `calculate_commission`/`deduct_commission`
pair is internally consistent and correctly guarded. Logged in
`product-decisions-required.md` as a recommendation for a future
cross-commission-pipeline reconciliation slice.

## Storage quota
`get_storage_quota` (a GET, not a mutation) is the only storage-quota
route in this module. No alternate write route was found elsewhere for
tenant storage quota within this audit's scope.

## Summary table

| Capability | package_commerce route | Alternate | Canonical owner | Disposition |
|---|---|---|---|---|
| Package definitions | 13 CRUD/lifecycle routes | none | package_commerce | CANONICAL_PLATFORM_WRITE |
| Package assignment | `admin_purchase_package` | `tenant_router.tenant_purchase_package` | shared `create_package_assignment` | SHARED_CANONICAL_SERVICE |
| Security deposit | 3 blocked routes | `finance_hub.admin_router` | finance_hub | DEPRECATED_410 |
| Usage credit ledger | `admin_topup_wallet`/`admin_adjust_wallet` | none (adapter only) | UsageCreditService | CANONICAL_PLATFORM_WRITE |
| Commission (job_id-keyed) | `admin_deduct_commission`/`admin_calculate_commission` | `platform_commerce.CommerceService`, `invoice_payment.ServiceCommissionService` | shared `CommissionRecord` table, 3 independent code paths | DISTINCT_CAPABILITY (documented cross-module risk, not fixed — out of this module's scope) |
