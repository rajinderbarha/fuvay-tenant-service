# FINAL-L5-05I — Endpoint Inventory, Source-of-Truth Matrix, Domain Boundaries, Strategy, Migration Plan

See `FINAL_L5_05I_CONSUMER_CLASSIFICATION.md` for the per-consumer (C1–C11) evidence this
document builds on.

## Part 4 — Endpoint Inventory (generic-wallet-mutation surface)

| Method/Path | Router | Backing service | Consumer | Classification |
|---|---|---|---|---|
| `POST /v1/commerce/tenants/{id}/wallet/deduct` | `platform_commerce/router.py` | `CommerceService.engine_deduct_wallet` | C10 | **DEPRECATED_BLOCKED** (FINAL-L5-05H, 410) |
| `POST /v1/commerce/tenants/{id}/wallet/credit` | `platform_commerce/router.py` | `CommerceService.admin_credit_wallet` | C10 | AMBIGUOUS_GENERIC — generic manual credit, no domain typing, no job/package/deposit link required |
| `GET /v1/commerce/tenants/{id}/wallet/balance`, `/projection` | `platform_commerce/router.py` | `CommerceService.get_wallet*` | C10 | READ_ONLY |
| `POST /v1/admin/tenants/{id}/wallet/top-up` | `field_ops/admin_finance_router.py` | `BillingService.admin_wallet_topup` | C2 | AMBIGUOUS_GENERIC — duplicate of the above, different router |
| `POST /v1/admin/tenants/{id}/wallet/adjust` | `field_ops/admin_finance_router.py` | `BillingService.admin_wallet_adjust` | C2 | AMBIGUOUS_GENERIC — duplicate |
| `GET /v1/admin/tenants/{id}/wallet`, `/ledger` | `field_ops/admin_finance_router.py` | `BillingService.get_tenant_wallet*` | C2 | READ_ONLY (duplicate read surface) |
| `POST /v1/admin/tenants/{id}/wallet/topup` (no hyphen) | `tenant_engine/admin_router.py` | `TenantAdminService.credit_topup` | C11 | AMBIGUOUS_GENERIC — third distinct route string for the same conceptual action |
| `POST /v1/admin/tenants/{id}/wallet/adjust` | `tenant_engine/admin_router.py` | `TenantAdminService.credit_adjust` | C11 | AMBIGUOUS_GENERIC — no row lock, no idempotency key at all (weakest of the five) |
| `GET /v1/admin/tenants/{id}/wallet/ledger` | `tenant_engine/admin_router.py` | `TenantAdminService.get_credit_ledger` | C11 | READ_ONLY |
| `POST /v1/admin/tenants/{id}/credit-wallet/top-up`, `/adjust` | `package_commerce/admin_router.py` | `PackageCommerceService.admin_topup_wallet/admin_adjust_wallet` | C7 | **AMBIGUOUS_GENERIC + MISNAMED** — gated by `FINANCE_USAGE_CREDITS_*` permissions but mutates `TenantWallet`, not `tenant_billing` |
| `GET /v1/admin/tenants/{id}/credit-wallet`, `/credit-ledger` | `package_commerce/admin_router.py` | same | C7 | READ_ONLY, same mislabel |
| `POST /v1/admin/provider-wallets/{id}/credit` | `invoice_payment/admin_router.py` | `ProviderCreditWalletService.admin_credit` | C6 | AMBIGUOUS_GENERIC, but **confirmed unlinked from nav** (Blocker 9) |
| `GET /v1/admin/finance/wallets`, `/{id}/ledger` | `finance_hub/admin_router.py` | `finance_hub.service.list_wallets/get_wallet_ledger` | C4 | READ_ONLY, **confirmed unlinked from nav** (Blocker 9) |
| `POST /v1/admin/dispute-settlements/{id}/execute` | `customer_credits` router (Sprint 75) | `DisputeSettlementService.execute_settlement` | C1 | DOMAIN_SPECIFIC_BUT_MISNAMED — real domain logic (deposit/wallet-recovery waterfall), not generic, but still mutates `TenantWallet` fields directly without the shared locked primitive |
| `POST /v1/admin/tenants/{id}/security-deposit/mark-paid`, deposit routes | `finance_hub` / `platform_commerce` | `credit_deposit`/`debit_deposit` | C4 | CANONICAL (Security Deposit — correctly isolated, see Part 10) |
| Commission routes (Sprint 23) | `invoice_payment` router | `ServiceCommissionService` | C5 | CANONICAL_CANDIDATE (see Part 9) |
| `POST /v1/jobs/*` financial actions (invoice/payment/commission/close) | `field_ops/router.py`, `admin_finance_router.py`, `tenant_finance_router.py` | `BillingService` | C2 | LEGACY_COMPATIBILITY — built for the superseded `jobs` table, 0 real rows |

**Result: 8 active mutation endpoints remain classified AMBIGUOUS_GENERIC** (the `POST /wallet/*top-up|adjust|credit*` family across `platform_commerce`, `field_ops`, `tenant_engine`, `package_commerce`). This is a real, hard finding: **the mission's acceptance criterion #4 ("0 active mutation endpoints classified AMBIGUOUS_GENERIC") is not met.** All 8 are real, live, RBAC'd (super-admin-only), and none are linked from primary Finance navigation beyond the ones already-known-orphaned in Blocker 9 — but `package_commerce`'s and `tenant_engine`'s versions back real, discoverable admin actions (Usage Credits admin page, Tenant 360 wallet tab), so they are not simply dead/orphaned like the Blocker-9 pages.

## Part 5 — Mutation Graph (abbreviated — full per-operation graphs in Part 2's table)

Every operation traced in Part 2 has: trigger, actor, tenant, before/after balance, and an
idempotency mechanism identified per-row. The two gaps found:
1. `tenant_engine.TenantAdminService.credit_topup/credit_adjust` (C11) has **no lock and no
   idempotency key** — a genuine concurrency risk (double-submit of the same admin action could
   double-credit).
2. `tenant_engine.TenantAdminService.add_usage_credits` (C11) mutates `tenant_billing.credit_balance`
   directly with **zero `UsageCreditLedger` row** — violates rule 14 ("every mutation must have
   ledger evidence"). This is the one gap in this entire investigation that touches the actually-
   canonical Usage Credit table, making it the highest-priority remediation candidate.

## Part 6 / 7 — Source-of-Truth Matrix

| Domain | Canonical table (per certified rules) | Actual current table(s) in use | Status |
|---|---|---|---|
| Usage Credit current balance | `tenant_billing.credit_balance` | `tenant_billing.credit_balance` (Completed Job Deduction, correct) **and** `TenantWallet.credit_balance` (5 separate admin-adjustment code paths, `package_commerce`'s Usage-Credits-permissioned endpoints, field_ops commission deduction) | **VIOLATED** — two active current balances exist under the "Usage Credit" label depending on which admin surface is used |
| Usage Credit history | `usage_credit_ledger` | `usage_credit_ledger` (1 row, from Completed Job Deduction) — `add_usage_credits` bypasses it entirely | **PARTIALLY VIOLATED** — one write path with no ledger evidence |
| Package purchase state | package domain (`service_packages`/`tenant_package_purchases`/`tenant_package_assignments`) | `package_commerce/models.py`, correctly owned | OK |
| Package Credit Grant | should post through canonical Usage Credit service | Currently: `package_commerce.service.py`'s wallet endpoints credit `TenantWallet`; `finance_hub.service.py` ALSO independently credits `TenantWallet` on purchase-confirm (`TxnType.PURCHASE`) | **VIOLATED** — package credit grants two different implementations, both targeting the non-canonical wallet table |
| Commission assessment/collection | one canonical owner required | Real, executed code exists in 2 independent, never-yet-triggered implementations (`invoice_payment.ServiceCommissionService` for `service_jobs`, `platform_commerce.CommerceService.deduct_commission` for the legacy `jobs` table via field_ops) plus the blocked `engine_deduct_wallet` (05H) | **VIOLATED** — no single canonical commission owner exists yet; see Part 9 |
| Security Deposit held amount / history | `security_deposits` / `security_deposit_transactions`, isolated from wallet | Confirmed isolated — `credit_deposit`/`debit_deposit` never touch `tenant_billing` or `usage_credit_ledger` | **OK — invariant holds** |
| Field-operations billing | should not duplicate Completed Job Deduction | `field_ops.BillingService` operates on a wholly separate `jobs` table with 0 real rows — no live overlap risk today, but the code exists and could collide if ever reactivated | LATENT RISK, not active |
| Tenant financial health signal | should read `tenant_billing.credit_balance` | Reads nothing live — `credit_wallet_health` has never been written (its only writer, `_update_wallet_signal`, is unreachable because C2/C10's commission path has 0 real rows); always falls back to hardcoded `100.0` | **VIOLATED** (dead signal, wrong source even if it did fire) |
| Customer payment context | `CustomerServiceCredit`/`CustomerCreditLedger`, isolated from Usage Credits | Confirmed isolated (C1b) | OK |
| Provider earning context | not implemented — certified as out of scope (no payouts in active model) | No live code found that treats `TenantWallet` as provider earnings | OK (NOT_IMPLEMENTED, consistent with certified rules) |
| Subscription billing | separate source of truth | `platform_commerce/billing_constants.py` defines `SUBSCRIPTION_LEADS`/`SUBSCRIPTION_BOOKING` billing modes marked "soon"/"future" — no live implementation | **NOT_IMPLEMENTED** (Part 13 requirement satisfied — confirmed not misused) |

**Required invariants from Part 7, evaluated:**
1. "No domain has two active current balances" — **FAILS** for Usage Credit (see above).
2. "No domain has two active ledgers without explicit separation" — holds for Security Deposit and Customer Credit; **fails** for Package Credit (two independent grant implementations) and Commission (two independent implementations, neither yet triggered with real data).
3. "No job-linked charge competes with Completed Job Deduction" — **holds**, verified in FINAL-L5-05H (Part 7 gate) and re-confirmed this sprint (`engine_deduct_wallet` still 410, no new job-linked wallet endpoint was found).
4. Security Deposit separate from Usage Credits — **holds**.
5. Provider earning context separate from Usage Credits — **holds** (not implemented).
6. Customer payment context separate from Usage Credits — **holds**.

## Part 8 — Package-Credit Boundary

1. Package purchase event: `tenant_package_purchases` row created (package_commerce domain — correctly owned).
2. Package activation: same service, correctly owned.
3. **What grants Usage Credits**: currently **nothing does, correctly** — the real `tenant_billing.credit_balance` row was never populated by any package-purchase code path found in this investigation (the 1 real row's origin was not traceable to a package purchase; most likely a manual/seed value). Both `package_commerce.service.py`'s and `finance_hub.service.py`'s purchase-confirmation code independently credit `TenantWallet`, not `tenant_billing`.
4. Package state table: `tenant_package_purchases`/`tenant_package_assignments` (package_commerce, correct).
5. Credit balance table (actual, today): `TenantWallet.credit_balance` — **not** the certified `tenant_billing.credit_balance`.
6. Grant ledger (actual, today): `WalletTransaction` — **not** `usage_credit_ledger`.
7. Can activation retry duplicate credits? Each purchase-confirm call carries its own idempotency key at the wallet-write level, so no — but the two independent implementations (package_commerce vs finance_hub) have never been proven mutually idempotent against each other (no shared idempotency namespace).
8. Grant idempotency: yes, per-implementation, not cross-implementation.
9. Does cancellation reverse credits? Not found in this investigation — out of the time budget to trace.
10. Does expiry modify existing credits? Not found — same.

**Required target boundary is not met.** Package Credit Grant should post through the canonical
Usage Credit service (`tenant_billing`/`usage_credit_ledger`); today it posts to `TenantWallet` via
two independent, non-cross-checked implementations. **Migration required**: both `package_commerce.service.py`'s
and `finance_hub.service.py`'s purchase-confirm credit calls need to be re-pointed at a canonical
`grant_package_credit()` function in the Usage Credit domain (mirroring `deduct_for_completed_job`'s
pattern) instead of `ledger.credit_wallet`. **Not implemented this sprint** — this is a real behavior
change to a live purchase-money code path and requires its own dedicated, tested migration (Phase 3
of the migration plan below), not a rushed same-session fix.

## Part 9 — Commission Boundary

Two real, wired, tested, but never-yet-triggered-in-production commission implementations exist:

| Path | Decision |
|---|---|
| `invoice_payment.ServiceCommissionService` (C5) — built explicitly "for service_jobs" per its own docstring, best idempotency/reversal/audit coverage | **SEPARATE_CANONICAL_CHARGE** — recommend as the target canonical commission implementation |
| `platform_commerce.CommerceService.deduct_commission` via `field_ops.BillingService` (C2/C10) — built for the superseded `jobs` table | **LEGACY_DUPLICATE** — recommend deprecation once C5 is confirmed as sole owner |
| `engine_deduct_wallet` (already blocked, FINAL-L5-05H) | Was job-linked but zero callers; not a commission path per se (used `TxnType.COMMISSION` but had no relationship to either real commission implementation) |

**Required invariant**: "One business event must not charge the tenant twice." **Holds today** only
because neither implementation has ever actually fired against real data (both commission tables
have 0 rows) — there is no evidence of an actual double-charge, but there is also no code-level
guard preventing both C5 and C2/C10 from firing against the same `service_jobs`/`jobs` job if both
were ever wired into the same completion flow. This is a **latent** risk, not an active one.

## Part 10 — Security Deposit Boundary

Confirmed via source read (`platform_commerce/ledger.py::credit_deposit/debit_deposit`,
`finance_hub/service.py`, `customer_credits/service.py`):
- Canonical state table: `security_deposits`. Canonical history: `security_deposit_transactions`.
- Canonical service: `finance_hub.service.py` (collection, mark-paid, refund) + `customer_credits.DisputeSettlementService` (deduction leg only, for dispute recovery).
- **Invariant 1 (does not mutate `tenant_billing.credit_balance`): holds.**
- **Invariant 2 (does not write Usage Credit Ledger events): holds.**
- **Invariant 3 (domain-specific event types): holds** — `DepositTxnType` is a distinct enum from `TxnType`.
- **Invariant 4 (not exposed as Wallet Balance): holds** in the API response shape (deposit fields are named `total_paid`/`current_balance`/`warranty_drawn`, not "wallet").
- **Invariant 5 (shared posting infra only behind domain wrappers): holds** — `credit_deposit`/`debit_deposit` are deposit-typed functions, not the generic `credit_wallet`/`debit_wallet`.

**Security Deposit is the one domain in this entire investigation with a fully clean, correctly-isolated boundary today.** No changes needed or recommended.

## Part 11 — Field-Operations Billing Boundary

1. What is charged: commission on a completed job's invoice total.
2. Who: the tenant.
3. Trigger: `record_payment` → auto-calls `deduct_commission` (C2).
4. Job-linked: yes, but to the legacy `jobs` table, not `service_jobs`.
5. Overlap with Completed Job Deduction: **no direct overlap** — different table, different job entity — but conceptually both are "money taken from a tenant when a job finishes," which is exactly the kind of terminology/concept collision the mission is trying to eliminate.
6/7. Balance/ledger affected: `TenantWallet`/`WalletTransaction`.
8. Still active: **no** — 0 rows in `jobs` table, confirmed live.
9. UI/API: `/v1/jobs/*`, `/v1/admin/finance/*`, `/v1/tenant/finance/*`, `/v1/customer/jobs/*` — all mounted.
10. Role: super_admin (finance actions), staff/technician (job actions), tenant_owner, customer.

**Classification: LEGACY_DUPLICATE.** Per the rule "do not preserve a second job-completion charge,"
this should ultimately be deprecated the same way `engine_deduct_wallet` was — but unlike that
endpoint, this one has multiple real callers within its own subsystem (invoice generation, payment
recording, job closure all chain through it), so blocking it outright would need its own dependency
proof first. **Not blocked this sprint** — flagged as the top Phase-1 candidate after the `add_usage_credits`
ledger-evidence fix.

## Part 12 — Tenant Health Financial Signal

Confirmed via trace: `credit_wallet_health` (15% weight) is written **only** by
`CommerceService._update_wallet_signal`, called **only** from `CommerceService.deduct_commission`,
called **only** from `field_ops.BillingService.deduct_commission`, gated on the `jobs` table having
rows — which it never has. **The signal has never been written in this environment.** Every tenant's
health score today silently uses the hardcoded default (`100.0`) for 15% of its weight, regardless
of actual Usage Credit balance.

Required target: "Low-credit health uses `tenant_billing.credit_balance`." **Not met today.**
Remediation (not implemented this sprint, needs its own test coverage): replace `_update_wallet_signal`'s
call site with a read of `tenant_billing.credit_balance` against a low-balance threshold, computed
independent of whether any commission has ever been deducted — likely a small, low-risk, single-file
change, but out of this session's remaining time budget to implement and test safely.

## Part 13 — Subscription Billing Check

Confirmed: `SUBSCRIPTION_LEADS`/`SUBSCRIPTION_BOOKING` billing modes exist only as forward-looking
constants (`platform_commerce/billing_constants.py`, marked "soon"/"future"). No live consumer
implements them. **Classification: NOT_IMPLEMENTED.** All three required invariants trivially hold
because there is no code to violate them.

## Part 14 — Shared Ledger Primitive Decision

`platform_commerce/ledger.py` evaluated against the four options:
- It has real, correct low-level posting mechanics (row locking, idempotency-key uniqueness).
- It has **no domain typing** — `credit_wallet`/`debit_wallet` accept any `TxnType` and any caller, with no requirement that the caller declare which financial domain (Usage Credit / Package / Commission / Field-Ops) the posting belongs to.
- It is called both by legitimate shared-infrastructure use (Security Deposit's `credit_deposit`/`debit_deposit`, which are already domain-typed wrappers) and by at least 5 independent "generic admin adjustment" call sites that use it as an untyped wallet API.

**Decision: C — Mixed module containing both infrastructure and policy.** The deposit-specific
functions (`credit_deposit`/`debit_deposit`) are already correctly-scoped domain wrappers and should
stay. The generic `credit_wallet`/`debit_wallet` functions are simultaneously (a) legitimate internal
posting primitives when called from a properly-scoped domain service, and (b) the mechanism every
untyped "admin adjusts a wallet" endpoint uses to bypass domain boundaries entirely.

**Recommended follow-up (not implemented this sprint)**: `SPLIT_INFRASTRUCTURE_FROM_DOMAIN_POLICY`
— keep `get_wallet_locked`/the row-locking mechanics as pure infrastructure, and require every caller
to go through a typed domain wrapper (`grant_package_credit`, `assess_commission`, `adjust_security_deposit`)
the way `credit_deposit`/`debit_deposit` already do, rather than calling `credit_wallet`/`debit_wallet`
directly. This directly eliminates the 5-implementations-of-the-same-generic-action problem found in
Part 2 without requiring a full service extraction.

## Part 15 — Architecture Strategy

**Selected: Strategy A — Domain services over shared posting infrastructure**, informed directly by
Part 14's finding that the shared primitive itself is sound and does not need replacing (Strategy B)
or a stricter typed-engine rewrite (Strategy C) — the actual defect is that domain services were never
required to exist as the sole callers, not that the posting primitive is broken.

| Domain | Owner (target) |
|---|---|
| Usage Credit | `app/engines/execution/usage_credit_deduction.py` extended into a full `UsageCreditService` (grant + deduct + adjust, all writing `tenant_billing` + `usage_credit_ledger`) |
| Package Credit | `package_commerce` engine, calling the new `UsageCreditService.grant()` instead of `ledger.credit_wallet` directly |
| Commission | `invoice_payment.ServiceCommissionService` (C5) — already the better-built implementation; `platform_commerce`/`field_ops`'s duplicate is deprecated in Phase 4 |
| Security Deposit | `finance_hub` (collection/refund) + `customer_credits` (dispute-recovery deduction leg) — already correctly isolated, no change needed |
| Field-operations billing | Deprecated after C2's dependency chain is proven safe to remove (Phase 6) |
| Tenant health data | `tenant_engine.health` reads `tenant_billing.credit_balance` directly instead of the dead Redis signal (Phase 7) |
| Subscription billing | Not yet implemented — deferred until a real vertical needs it |
| Shared infrastructure | `platform_commerce/ledger.py`'s locking primitives remain, but new callers must go through a domain wrapper, not `credit_wallet`/`debit_wallet` directly (enforced by an architecture guard test in Phase 1) |
| Public API policy | No new generic wallet mutation endpoints (rule 10, already honored); existing 8 AMBIGUOUS_GENERIC endpoints are consolidated/deprecated over Phases 2-6, not this sprint |
| Table disposition | `tenant_wallets`/`wallet_transactions`: `RETAIN_AS_INTERNAL_POSTING_INFRASTRUCTURE` for now (still 0 rows, still load-bearing for Security Deposit's shared locking code path) — final `DROP_IN_LATER_MIGRATION` decision deferred until Phases 3/4 complete and no domain still targets it directly |

## Part 16 — Domain Boundary Decision Records (concise)

- **Usage Credit**: current state = correct canonical implementation exists (Completed Job Deduction) but is not the only writer of `tenant_billing.credit_balance` (see `add_usage_credits` gap). Owner: `execution/usage_credit_deduction.py`. Migration required: extend it into `UsageCreditService`; fix `add_usage_credits`'s missing ledger row. Status: **PARTIALLY CERTIFIED — 1 concrete gap identified, not yet fixed.**
- **Package Credit**: current state = two independent implementations, both wrong-tabled. Owner (target): `package_commerce` via `UsageCreditService.grant()`. Status: **NOT CERTIFIED — migration required, not started.**
- **Commission**: current state = two independent implementations, neither ever executed against real data. Owner (target): `invoice_payment.ServiceCommissionService`. Status: **NOT CERTIFIED — migration required, not started.**
- **Security Deposit**: current state = correctly isolated. Owner: `finance_hub` + `customer_credits`. Status: **CERTIFIED — no migration required.**
- **Field-operations billing**: current state = legacy, unreachable in practice (0 rows), real dependency chain not yet fully proven safe to remove. Owner: none (deprecation candidate). Status: **NOT CERTIFIED — investigation required before any code change.**
- **Tenant financial health**: current state = dead signal, wrong source even if alive. Owner (target): `tenant_engine.health` reading `tenant_billing` directly. Status: **NOT CERTIFIED — concrete fix identified, not yet implemented.**
- **Subscription billing**: current state = not implemented. Status: **N/A, no violation possible.**
- **Shared posting infrastructure**: current state = sound primitives, no domain-typing enforcement. Owner: `platform_commerce/ledger.py` (infrastructure only, going forward). Status: **PARTIALLY CERTIFIED — decision made (split infra from policy), not yet enforced.**

## Part 17 — Migration Plan (sequenced, not executed this sprint beyond Phase 0)

- **Phase 0 (this sprint)**: classification, source-of-truth matrix, decision records, architecture guard tests for what's already true. *(Executed.)*
- **Phase 1**: Fix `add_usage_credits`'s missing ledger row (tests: 1 new focused test). Add a lock + idempotency key to `tenant_engine.credit_topup/credit_adjust` OR deprecate them in favor of one canonical admin-adjustment endpoint. Certification gate: full backend suite + new focused tests green.
- **Phase 2**: Extend `usage_credit_deduction.py` into `UsageCreditService` with an explicit `grant()` method; no callers migrated yet. Gate: unit tests for `grant()` idempotency.
- **Phase 3**: Migrate `package_commerce.service.py` and `finance_hub.service.py`'s purchase-confirm calls to `UsageCreditService.grant()` instead of `ledger.credit_wallet`. Requires a compatibility window (dual-write or feature flag) since this touches live purchase-money code. Gate: package purchase E2E + Usage Credit balance reconciliation test.
- **Phase 4**: Deprecate `platform_commerce.CommerceService.deduct_commission`/`field_ops.BillingService.deduct_commission` in favor of `invoice_payment.ServiceCommissionService`, once field_ops's `jobs` table dependency chain (Phase 6) is proven safe. Gate: commission double-charge guard test across both former paths.
- **Phase 5**: Consolidate the 5 generic admin-wallet-adjustment endpoints into one canonical, domain-typed endpoint (or deprecate 4 of the 5 the way `engine_deduct_wallet` was). Gate: architecture guard test asserting 0 AMBIGUOUS_GENERIC endpoints remain.
- **Phase 6**: Full dependency-chain proof for `field_ops.BillingService`/the `jobs` table (does anything outside this subsystem read `jobs`, `InvoiceRecord`(field_ops), `PaymentRecord`(field_ops)?) before blocking `/v1/jobs/*` financial actions the way `engine_deduct_wallet` was blocked.
- **Phase 7**: Repoint `tenant_engine.health`'s `credit_wallet_health` signal to read `tenant_billing.credit_balance` directly; remove the dead `_update_wallet_signal` call site once Phase 4 completes.
- **Phase 8**: Remove/return-410 the remaining AMBIGUOUS_GENERIC wallet endpoints not already consolidated in Phase 5.
- **Phase 9**: Decide final disposition of `tenant_wallets`/`wallet_transactions` (retain as internal infra vs. drop) once Phases 3-8 confirm no domain still targets them directly for its canonical balance.
- **Phase 10**: Frontend terminology cleanup on the two still-unlinked wallet pages (Blocker 9) and the "credit-wallet" URL naming in `package_commerce`.

Each phase is its own dedicated-sprint-scale unit of work; none were executed this sprint beyond
Phase 0's classification and the guard tests below, consistent with the mission's explicit
instruction not to attempt broad extraction before classification is complete.
