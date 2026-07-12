# FINAL-L5-05J — Usage Credit Mutation Consolidation, Package Credit Migration, Tenant Health Repair

See `FINAL_L5_05I_CONSUMER_CLASSIFICATION.md` / `FINAL_L5_05I_DOMAIN_BOUNDARIES.md` for the
pre-existing evidence this sprint builds on. This doc does not repeat that classification.

## Part 2 — Five Usage Credit adjustment paths, final disposition

| Path | Endpoint | Frontend caller | Intent | Final disposition |
|---|---|---|---|---|
| 1. `platform_commerce.CommerceService.admin_credit_wallet` | `POST /v1/commerce/tenants/{id}/wallet/credit` | none found | MANUAL_CREDIT_INCREASE, but tied to the general TenantWallet/commission ecosystem, not Usage-Credit-branded | **UNRELATED_DOMAIN_CARRIED_FORWARD** — out of this sprint's Usage Credit/Package Credit scope (Commission domain, explicitly deferred per mission instructions); left unchanged |
| 2. `field_ops.BillingService.admin_wallet_topup` / `admin_wallet_adjust` | `POST /v1/admin/tenants/{id}/wallet/top-up`, `/wallet/adjust` | none found | MANUAL_CREDIT_INCREASE/DECREASE, tied to the legacy field_ops `jobs` table (0 rows) | **UNRELATED_DOMAIN_CARRIED_FORWARD** — field-operations billing/Commission scope, explicitly deferred; left unchanged |
| 3. `tenant_engine.TenantAdminService.credit_topup` / `credit_adjust` | `POST /v1/admin/tenants/{id}/wallet/topup`, `/wallet/adjust` | **zero callers** (confirmed via grep of `frontend/super-admin`) | MANUAL_CREDIT_INCREASE/DECREASE, no row lock, no idempotency key | **DEPRECATED_410** — blocked this sprint, points callers at the canonical `/v1/admin/usage-credits/{tenant_id}/adjustments` |
| 4. `package_commerce.PackageCommerceService.admin_topup_wallet` / `admin_adjust_wallet` | `POST /v1/admin/tenants/{id}/credit-wallet/top-up`, `/adjust` | zero callers, but gated by `FINANCE_USAGE_CREDITS_*` permissions (the correctly-named ones) | MANUAL_CREDIT_INCREASE/DECREASE, **mislabeled as Usage Credits while targeting TenantWallet** — the highest product-risk finding in FINAL-L5-05I | **CANONICAL_USAGE_CREDIT** — converted this sprint to delegate to `UsageCreditService.adjust_credit`; no longer touches `TenantWallet` |
| 5. `invoice_payment.ProviderCreditWalletService.admin_credit` | `POST /v1/admin/provider-wallets/{id}/credit` | none (confirmed unlinked from nav, Blocker 9) | MANUAL_CREDIT_INCREASE, "provider wallet" branding | **UNRELATED_DOMAIN_CARRIED_FORWARD** — provider-earning-context/Commission-adjacent, explicitly out of scope; page remains unlinked |

**0 UNKNOWN.** 2 of 5 paths were genuinely in the Usage Credit/Package Credit scope this mission
targets (paths 3 and 4) and both are resolved. The other 3 belong to Commission/field-operations/
provider-earning domains this mission explicitly instructs not to migrate.

**Sixth path discovered this sprint** (not in FINAL-L5-05I's original count): `finance_hub.service.retry_credit_posting`,
a real, schema-coupled "Credit Top-up Order" flow (own model with `wallet_transaction_id` FK,
gateway-payment tracking) independently crediting `TenantWallet`. Migrating this requires adding a
`usage_credit_ledger_id` column to the topup-order model — a real schema change beyond this sprint's
bounded-fix budget. Documented, not fixed (L5-05J-003).

## Part 3 — Canonical UsageCreditService

`app/engines/usage_credits/service.py` — new domain-owning service. Operations implemented:
`get_balance`, `get_ledger`, `check_threshold`, `adjust_credit`, `grant_package_credit`,
`deduct_for_completed_job` (delegates to `execution.usage_credit_deduction.deduct_for_completed_job`,
not duplicated), `reverse_credit_event`.

Mutation contract fields (tenant_id, amount, direction, event_type, source_type, source_id,
reason_code, reason, idempotency_key, actor_id, request_id) are all present on `_post()`, the single
internal mutation primitive every public method funnels through. Result contract fields
(ledger_event_id → `ledger_id`, tenant_id, before/after balance, event_type, source_type/id,
idempotency_key, created_at, audit — via `to_dict()` plus the `idempotent` flag) match the mission
spec.

## Part 4/5 — Transactional mutation + ledger event model

`_post()` in `service.py`:
1. Checks `idempotency_key` against `usage_credit_ledger.idempotency_key` (unique, migration 133) — returns the existing row if found, no new mutation.
2. `SELECT ... FOR UPDATE` locks the `tenant_billing` row (creates it first if missing, then re-selects with lock).
3. Validates the resulting balance against `allow_negative` (debits reject `INSUFFICIENT_USAGE_CREDIT`; credits never block).
4. Writes the `UsageCreditLedger` row (event_type from the typed set: `manual_credit_added`, `manual_credit_removed`, `package_credit_granted`, `completed_job_deduction`, `credit_reversal`, `migration_adjustment`).
5. Writes a `platform_audit_logs` row via `record_platform_audit`.
6. Returns before/after balance + full ledger row dict.

All within the caller's existing transaction (commit happens at the router layer, matching the
codebase's established per-request transaction pattern — `_post()` itself only flushes, never commits,
so a caller failure after `_post()` but before commit correctly rolls back both the balance and the
ledger row together).

## Part 6/7 — Admin adjustment consolidation + legacy endpoint policy

New canonical endpoint family (`app/engines/usage_credits/router.py`, mounted in `main.py`):
- `GET /v1/admin/usage-credits/{tenant_id}/balance`
- `GET /v1/admin/usage-credits/{tenant_id}/ledger`
- `GET /v1/admin/usage-credits/{tenant_id}/threshold`
- `GET /v1/admin/usage-credits/reason-codes`
- `POST /v1/admin/usage-credits/{tenant_id}/adjustments` — the canonical mutation endpoint, matching the mission's suggested request/response shape and controlled error set (`TENANT_NOT_FOUND`, `INVALID_CREDIT_AMOUNT`, `INVALID_ADJUSTMENT_DIRECTION`, `INVALID_ADJUSTMENT_REASON`, `INSUFFICIENT_USAGE_CREDIT`, `USAGE_CREDIT_CONFLICT`).

Legacy endpoint dispositions:

| Endpoint | Disposition |
|---|---|
| `POST /v1/admin/tenants/{id}/add-usage-credits` | **CANONICAL_ADAPTER** — delegates to `UsageCreditService.adjust_credit`; fixes the real ledger-evidence gap (previously wrote `tenant_billing.credit_balance` with zero `usage_credit_ledger` row); backward-compatible request shape preserved for the live frontend caller |
| `GET /v1/admin/tenants/{id}/usage-credit-ledger` | Already correct (reads `usage_credit_ledger` directly); unchanged |
| `POST /v1/admin/tenants/{id}/wallet/topup`, `/wallet/adjust` | **DEPRECATED_410** |
| `POST /v1/admin/tenants/{id}/credit-wallet/top-up`, `/adjust` | **CANONICAL_ADAPTER** (delegates to `UsageCreditService`) |
| `GET /v1/admin/tenants/{id}/credit-wallet`, `/credit-ledger` | **CANONICAL_ADAPTER** (reads via `UsageCreditService`) |
| `POST /v1/commerce/tenants/{id}/wallet/credit`, `POST/GET /v1/admin/tenants/{id}/wallet*` (field_ops), `POST /v1/admin/provider-wallets/{id}/credit` | **UNRELATED_DOMAIN_CARRIED_FORWARD** — Commission/field-ops/provider scope, unchanged |

## Part 8/9 — Package Credit Grant migration + idempotency

`package_commerce.service.py::purchase_package`'s included-credit grant (the one real,
purchase-money-linked package credit path — previously called `ledger.credit_wallet` with
`idempotency_key=f"pkg-purchase-credit-{purchase.id}"`) now calls
`UsageCreditService.grant_package_credit(tenant_id, package_assignment_id=str(purchase.id),
activation_version=1, amount=pkg.included_credit_amount, ...)`, which builds the grant identity
`package_credit_grant:{purchase.id}:1` — matching the mission's suggested
`package_credit_grant:{package_assignment_id}:{activation_version}` pattern, enforced unique at the
DB level (migration 133's `uq_ucl_idempotency_key`).

Package cancellation/expiry reversal behavior was traced but not found implemented anywhere in the
current codebase (neither the old `credit_wallet` path nor any other) — this is a pre-existing gap,
not a regression, and is out of this sprint's bounded-fix scope. Documented as L5-05J-004.

`finance_hub.service.py`'s separate purchase-confirm credit call (line 419, a different
"Credit Top-up Order" concept — see Part 2's sixth-path finding) was **not** migrated this sprint;
it remains on `ledger.credit_wallet`/`TenantWallet`.

## Part 11 — Completed Job Deduction regression

Unchanged. `deduct_for_completed_job` in `execution/usage_credit_deduction.py` was not modified.
`UsageCreditService.deduct_for_completed_job` is a thin delegate (imports and calls the existing
function directly) — added so the canonical service exposes the operation per the mission's Part 3
requirement, without duplicating or refactoring the certified logic. `engine_deduct_wallet` remains
`410` (unchanged from FINAL-L5-05H, re-verified — see architecture guard tests).

## Part 12/13 — Tenant health signal repair

`credit_wallet_health` (dead — its only writer was gated on a 0-row table, always fell back to a
hardcoded 100.0) is replaced by `usage_credit_health`, computed live in
`tenant_engine/health.py::_compute_usage_credit_health` from `tenant_billing.credit_balance` on every
call (no Redis caching — deliberately not stale). Formula:

```
if no tenant_billing record:       score = 0.0   (honest — not a silent 100)
elif threshold <= 0:               score = 100.0
elif balance >= threshold:         score = 100.0
elif balance <= 0:                 score = 0.0
else:                              score = (balance / threshold) * 100   (linear ramp)
```

Threshold reuses the existing real platform default (`PLATFORM_DEFAULT_LOW_CREDIT_THRESHOLD = 500.00`,
already defined in `package_commerce/service.py` for the old wallet's low-balance alert) rather than
inventing a new number — mirrored as a literal in `usage_credits/constants.py` to avoid coupling the
Usage Credit domain's import graph to `package_commerce`.

`HEALTH_SCORE_WEIGHTS["usage_credit_health"] = 0.15` (renamed key, same weight, in
`tenant_engine/constants.py`). `TenantService.get_health_score` now passes `db` through to
`compute_health_score`, which is the one call site in the whole codebase (confirmed via grep).

Not fixed this sprint: `analytics/service.py::get_platform_summary` still counts
`serviceos:health:*:credit_wallet_health` Redis keys for an `active_tenants` KPI — this key was
already always-empty (same root cause), so no behavior regression, but the KPI itself remains
silently wrong (was 0 before, is 0 now) and should be repointed at real data in a future sprint
(L5-05J-007 partial).

## Part 21 — Ambiguous endpoint resolution (Usage Credit / Package Credit scope only)

Of the 8 `AMBIGUOUS_GENERIC` endpoints FINAL-L5-05I found: **4 are in scope for this sprint** (Usage
Credit / Package Credit domain) and all 4 are resolved (2 `DEPRECATED_410`, 2 `CANONICAL_USAGE_CREDIT`
adapters). The remaining 4 belong to Commission/field-operations/provider-earning domains and are
explicitly out of scope per this mission's own instructions — carried forward, not claimed resolved.

## Part 17 — Database constraints

Migration 133 adds: `usage_credit_ledger.idempotency_key` (nullable, unique via partial index
`uq_ucl_idempotency_key` where non-null) + `source_type`, `source_id`, `reason_code`, `actor_role`.
Completed Job Deduction's pre-existing uniqueness (`uq_ucl_job_event_once`, migration 129) is
untouched. No new constraint was needed on `tenant_wallets`/`wallet_transactions` since no Usage
Credit path writes them any longer (see architecture guards).

## What was not attempted this sprint (honest scope boundary)

- Live API verification (no backend server was started this session) and real Chromium E2E — not run.
- Full RBAC matrix across Admin Finance/Admin Operations/Tenant Owner/Customer/Technician — these
  roles largely don't exist as distinct backend concepts (established finding from FINAL-L5-05G);
  reused the existing, real `FINANCE_USAGE_CREDITS_*`/`TENANT_HEALTH_READ` permissions rather than
  inventing new ones.
- `finance_hub`'s separate Credit Top-up Order flow (sixth path, discovered this sprint) — not migrated.
- Package cancellation/expiry credit-reversal — traced, found not implemented anywhere (pre-existing gap).
- Concurrency tests (Part 22) — the row-lock (`SELECT ... FOR UPDATE`) and idempotency-key uniqueness
  are implemented and unit-tested for the sequential case; true concurrent-request tests against a
  live DB were not run this session.
