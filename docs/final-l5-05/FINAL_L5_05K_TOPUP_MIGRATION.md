# FINAL-L5-05K — Finance Hub Credit Top-up Migration, Concurrency & Runtime Certification

## Part 2 — Finance Hub top-up domain inventory

| Component | File | Purpose | Reads | Writes | Reachability |
|---|---|---|---|---|---|
| `CreditTopupOrder` model | `app/engines/finance_hub/models.py` | Full lifecycle tracker for a credit top-up purchase (`initiated → paid_pending_credit → credited/failed/cancelled/refunded/partially_refunded`) | — | `credit_topup_orders` | Live, real table |
| `CommerceService.initiate_purchase` | `app/engines/platform_commerce/service.py:283` | Creates a Razorpay order + a `CreditTopupOrder` row (`payment_status="initiated"`) | `CreditPackage`, `SecurityDeposit` | `credit_topup_orders` | Live, `POST /v1/commerce/tenants/{id}/wallet/purchase/initiate`, `require_permission(P.TENANT_BILLING_MANAGE)` |
| `CommerceService.confirm_purchase` | `app/engines/platform_commerce/service.py:313` | Verifies the Razorpay signature (the real payment proof) and, on success, grants credit + replenishes the Security Deposit | `CreditPackage`, `CreditTopupOrder` | **Migrated this sprint**: `UsageCreditService.grant_topup_credit` (was `ledger.credit_wallet`); `credit_deposit` (Security Deposit, unchanged) | Live, `POST /v1/commerce/tenants/{id}/wallet/purchase/confirm`, **no auth** (`_svc_open`) — correct for a gateway-callback-style endpoint; the Razorpay signature itself is the authorization |
| `FinanceHubService.retry_credit_posting` | `app/engines/finance_hub/service.py:411` | Admin-triggered retry for a top-up stuck in `wallet_credit_status != "credited"` | `CreditTopupOrder` | **Migrated this sprint**: `UsageCreditService.grant_topup_credit` (was `ledger.credit_wallet`) | Live, `POST /v1/admin/finance/topups/{id}/retry-credit`, `require_permission(P.FINANCE_TOPUPS_UPDATE)` |
| `FinanceHubService.refund_topup` | `app/engines/finance_hub/service.py:429` | Records a refund against a top-up (bookkeeping only) | `CreditTopupOrder` | `credit_topup_orders.refunded_amount/payment_status` — **no balance/ledger mutation of any kind, before or after this sprint** | Live, `POST /v1/admin/finance/topups/{id}/refund`, `require_permission(P.FINANCE_TOPUPS_REFUND)` |
| `FinanceHubService.get_topup_detail` | `app/engines/finance_hub/service.py:391` | Detail view incl. linked ledger event | `CreditTopupOrder`, `UsageCreditLedger` (was `WalletTransaction`) | — | Live, `GET /v1/admin/finance/topups/{id}` |
| `FinanceHubService.list_topups`/`get_topups_summary`/`export_topups` | `app/engines/finance_hub/service.py` | List/summary/export | `CreditTopupOrder` | — | Live, all `require_permission(P.FINANCE_TOPUPS_READ)` |
| Frontend | `frontend/super-admin/app/admin/finance/topups/{page.tsx,[topup_id]/page.tsx}` | Existing enterprise Top-ups list + detail UI | real backend | — | Live, verified via real Chromium this sprint |

**No background job, no separate Finance Hub "approval" workflow, and no separate "approve/reject" endpoints exist anywhere in the real codebase.** Confirmed via `grep -rn "credit_topup\|CreditTopupOrder"` across `app/` — the only writers are `confirm_purchase` and `retry_credit_posting`, both covered above.

## Part 3 — Top-up order data model (field classification)

| Field | Classification |
|---|---|
| `id`, `tenant_id`, `credit_package_id`, `order_ref` | AVAILABLE |
| `credits_purchased`, `bonus_credits`, `amount_paid`, `currency`, `payment_method` | AVAILABLE |
| `payment_status` (`initiated\|paid_pending_credit\|credited\|failed\|cancelled\|refunded\|partially_refunded`) | AVAILABLE — the real status field |
| `wallet_credit_status` (`pending\|credited\|failed`) | AVAILABLE, LEGACY-NAMED — kept as-is (schema rename out of scope; doubles as the real "has this order been granted" flag) |
| `wallet_transaction_id` | LEGACY — no longer written by new code; retained for historical top-ups only (none exist in this environment: 0 real rows) |
| `usage_credit_ledger_event_id` | **NEW this sprint** (migration 134) — the canonical ledger reference |
| `gateway_order_id`, `gateway_payment_id` | AVAILABLE — the real payment proof fields |
| `failure_reason`, `refunded_amount` | AVAILABLE |
| `created_at`, `updated_at` | AVAILABLE |
| Approval fields (`approved_by`, `approved_at`, `rejected_by`, `rejected_at`, `rejection_reason`) | **MISSING — and correctly so.** No manual-approval workflow exists in the real product (see Part 5). Adding these fields would violate rule 13 ("do not invent payment-success semantics unsupported by the current model"). Not added. |
| Version/revision field | MISSING — not needed: a `CreditTopupOrder` can only ever be graduated `initiated → credited` once, enforced by (a) `retry_credit_posting`'s explicit `wallet_credit_status == "credited"` guard and (b) the DB-unique `usage_credit_ledger.idempotency_key`, which is the real single-grant guarantee (see Part 9). |

**0 fields were invented.** Only one field was added (`usage_credit_ledger_event_id`), and only because the pre-existing `wallet_transaction_id` field could no longer be meaningfully populated once the grant moved off `TenantWallet`.

## Part 4 — Top-up lifecycle (actual, from real code)

```
initiated ──(signature verify fails)──> failed  [terminal, no grant]
initiated ──(signature verify succeeds)──> credited  [grant via UsageCreditService, exactly once]
credited ──(admin refund)──> refunded | partially_refunded  [bookkeeping only, no balance reversal exists]
[stuck: initiated/paid_pending_credit with wallet_credit_status != "credited"] ──(admin retry-credit)──> credited
```

There is no `cancelled` transition anywhere in the real code (the enum value exists on the column but no code path sets it) and no `pending_approval`/`approved`/`rejected` states — those are mission-suggested example states, not real ones (Part 4's "example only" framing). Building a synthetic state machine around statuses the product doesn't use would violate rule 13.

**Required invariants, evaluated against real code:**
1. Pending order cannot grant credits — **holds**: `confirm_purchase` and `retry_credit_posting` are the only 2 grant call sites, and both gate on payment verification (signature) or an explicit re-check.
2. Rejected order cannot grant credits — N/A, no rejection state exists.
3. Cancelled order cannot grant credits — N/A, no code path sets `cancelled`; if it were ever set manually, no grant call site would be reachable for it (grants only fire from `confirm_purchase`/`retry_credit_posting`, not from a generic status-based dispatcher).
4. Failed-payment order cannot grant credits — **holds**: `confirm_purchase` sets `failed` and raises before reaching the grant call.
5. "Approved" order may grant credits only through canonical service — **holds** (both grant call sites now use `UsageCreditService.grant_topup_credit`).
6. Credit-granted order cannot grant again — **holds**, enforced at 2 levels: `retry_credit_posting`'s explicit status check (`409 CONFLICT`) and the DB-unique `usage_credit_ledger.idempotency_key` (belt-and-suspenders — verified by the true-concurrency test in Part 18).
7. Reversal creates a new ledger event, does not delete history — N/A this sprint: no top-up credit reversal exists in the real product (`refund_topup` never reverses credits, before or after this sprint — see Part 2). Not implemented (would be inventing new behavior).

## Part 5 — Payment and approval policy (evidence-based)

1. Is payment collected by the platform for a top-up? **Yes** — via Razorpay, for the package-purchase/credit-top-up flow specifically (distinct from Home Services job payments, which are certified as customer-pays-provider-directly).
2. Manual or gateway-based? **Gateway-based** (Razorpay).
3. Which field proves payment? `razorpay_client.verify_payment_signature(order_id, payment_id, signature)` — a cryptographic check, not a database flag set by a human.
4. Who verifies payment? The gateway signature check itself — no human verification step exists.
5. Who approves a top-up? **Nobody, in the real product.** There is no Finance Admin approval action anywhere in the codebase.
6. Can payment verification and approval be the same action? Yes — they are the same action (signature verification IS the trigger).
7. Can approval happen without payment proof? N/A — no separate approval exists.
8. Can an order be partially granted? No — the grant amount is always `credits_purchased + bonus_credits`, fixed at order-creation time.
9. Can approved credit differ from requested credit? No.
10. Can an order be reversed? No (see Part 4, invariant 7).

**Selected policy: C — "Gateway success triggers automatic grant, with Admin review only for exceptions."** The "Admin review" exception path is `retry_credit_posting`, for orders whose signature verified successfully but the credit posting itself failed to complete (e.g., a crash between signature verification and the grant call) — not a business-approval step, a technical-recovery step.

## Part 6 — Canonical source event

```
event_type:   TOPUP_CREDIT_GRANTED   (stored as "topup_credit_granted", app.engines.usage_credits.service.EVENT_TOPUP_CREDIT_GRANTED)
source_type:  FINANCE_HUB_CREDIT_TOPUP
source_id:    <credit_topup_orders.id>
idempotency_key: topup_credit_grant:{topup_order_id}:1
```

`grant_version` is always `1` — proven by Part 4/5: a `CreditTopupOrder` has no multi-approval-version concept in the real schema or code (no version/revision column, no re-approval flow). Both real call sites (`confirm_purchase`, `retry_credit_posting`) resolve to the *same* `topup_order_id` for a given order and therefore the *same* idempotency key, which is what makes the two independent trigger paths safe against each other (proven in Part 18).

## Part 7/8 — Grant service + transaction

No new `FinanceHubTopUpService` class was created — the mission explicitly allows "or extend the existing Finance Hub service," and the two real grant call sites (`confirm_purchase` in `platform_commerce`, `retry_credit_posting` in `finance_hub`) were extended in place rather than introducing a third intermediary service, since neither needed new orchestration logic beyond "call the canonical grant." `UsageCreditService.grant_topup_credit` (`app/engines/usage_credits/service.py`) is the one new method, and it is a thin, typed wrapper around the existing `_post()` transactional primitive (row lock, idempotency check, ledger write, balance write, audit — all atomic, all pre-existing from FINAL-L5-05J, reused unchanged).

Transaction shape (matches the mission's preferred sequence): lock `tenant_billing` row (`SELECT ... FOR UPDATE`, with a race-safe `INSERT ... ON CONFLICT DO NOTHING` for brand-new tenants — see Part 18's concurrency finding) → check idempotency key → apply the credit → write the ledger row → write the audit event → return before/after balance. Both grant call sites `await db.commit()` immediately after, matching the codebase's established per-request commit pattern.

## Part 9 — UsageCreditService integration

`grant_topup_credit(tenant_id, topup_order_id, amount, reason, grant_version=1)` calls `_post()` with `event_type=EVENT_TOPUP_CREDIT_GRANTED`, `source_type="FINANCE_HUB_CREDIT_TOPUP"`, `source_id=str(topup_order_id)`, `reason_code="credit_topup_purchase"`, `idempotency_key=f"topup_credit_grant:{topup_order_id}:{grant_version}"`. Result includes `ledger_id`, `balance_before`/`balance_after`, `event_type`, `idempotent` flag — verified live (Part 24).

Metadata: `confirm_purchase` passes the package name in `reason`; the `CreditTopupOrder` row itself carries `gateway_payment_id`, `amount_paid`, `currency` — a full metadata trail is reconstructable by joining `usage_credit_ledger.source_id` back to `credit_topup_orders.id`, rather than duplicating those fields into the ledger row itself (avoids denormalization; matches how `grant_package_credit` was designed in FINAL-L5-05J).

## Part 10/11 — Existing top-up record reconciliation

**`credit_topup_orders` has 0 rows in this environment** (verified live via direct SQL, both before and after this sprint's changes). There is nothing to reconcile. This was independently re-confirmed — not assumed — via `SELECT count(*) FROM credit_topup_orders` at the start of this sprint.

Consequently, Part 10's classification table is trivial: 0 `NOT_GRANTED`, 0 `CANONICALLY_GRANTED`, 0 `LEGACY_GRANTED_WITHOUT_LEDGER`, 0 `DUPLICATE_GRANT_RISK`, 0 `REJECTED`/`CANCELLED`, 0 `UNKNOWN`. No silent corrections were made because none were needed.

## Part 12 — Database migration

Migration 134 (`134_finance_hub_topup_usage_credit_migration.py`): adds `credit_topup_orders.usage_credit_ledger_event_id` (nullable UUID). Applied live (`alembic current` → `134 (head)`). `wallet_transaction_id` is untouched (no data to migrate, no drop — historical column preserved). No new unique constraint was needed on `credit_topup_orders` itself; the single-grant guarantee lives in `usage_credit_ledger.idempotency_key`'s pre-existing unique index (migration 133), which is the correct place for it (the constraint must be on the ledger, the actual place a duplicate grant would physically manifest).

## Part 15 — Legacy Finance Hub grant path decision

**CANONICAL_ADAPTER** for both `confirm_purchase` and `retry_credit_posting` — neither was blocked/removed (both remain the real, only entry points for granting top-up credit); both now delegate to `UsageCreditService.grant_topup_credit`, preserve their stable idempotency identity, never write `TenantWallet`/`wallet_transactions`, and return canonical ledger information (`usage_credit_ledger_event_id`, verified live in `get_topup_detail`).

## Part 16 — RBAC

Reused existing, real, already-correctly-scoped permissions (no new permission keys needed): `P.FINANCE_TOPUPS_READ` (list/summary/export/detail), `P.FINANCE_TOPUPS_UPDATE` (retry-credit), `P.FINANCE_TOPUPS_REFUND` (refund), plus the FINAL-L5-05J `P.FINANCE_USAGE_CREDITS_*` family for balance/ledger/adjustments. Live-verified: unauthenticated request → `401`; non-existent tenant → `404`.

**Honest limitation, re-confirmed this sprint**: distinct "Finance-capable Admin" / "Admin Read Only" / "Operations Admin" roles do not exist as backend concepts — `admin.readonly@serviceos.local` was checked directly against the live database and its `role` column is `super_admin`, identical to every other admin account. A true 403-for-insufficient-permission test could not be constructed against a real distinct low-privilege role because none exists yet; the permission-check mechanism itself (`require_permission`) is real and correctly wired (proven via architecture guards + the 401/404 live checks), but the full expected-roles matrix (Part 16) remains unverifiable until those roles exist.

## Part 17 — Audit

`UsageCreditService._post()` writes `topup_credit.granted` for every `TOPUP_CREDIT_GRANTED` event (actor, tenant, amount, before/after balance, source_type/id, reason, idempotency_key, request_id — all present, verified live). `FinanceHubService._audit()` separately writes `topup.retry_credit`/`topup.refund` events with full before/after `CreditTopupOrder` snapshots (pre-existing, unchanged). `CREDIT_TOPUP_ORDER_CREATED`/`CREDIT_TOPUP_PAYMENT_VERIFIED` as distinct audit events were not added — `confirm_purchase` doesn't currently call `_audit()` at all for the creation/verification steps (a pre-existing gap, not introduced or fixed this sprint; documented, not silently ignored).

## Part 18 — True concurrency testing (real Postgres, not unit tests)

`tests/test_final_l5_05k_topup_migration.py::TestTrueConcurrency` opens its own real `AsyncEngine` against the live database (bypassing the test suite's autouse DB mock) and runs genuinely concurrent `asyncio.gather()` calls:

1. **Two concurrent grants, same idempotency key** — exactly 1 `usage_credit_ledger` row resulted (verified via `SELECT count(*) ... WHERE idempotency_key = ...`), balance increased exactly once. **Passed.**
2. **Top-up grant concurrent with a manual adjustment on the same brand-new tenant** — this test **found a real bug**: `_post()`'s "create the `tenant_billing` row if missing" logic had a TOCTOU race (two concurrent transactions both see "no row," both attempt a plain `INSERT`, the loser hits `IntegrityError` on the unique `tenant_id` constraint). Fixed with `INSERT ... ON CONFLICT (tenant_id) DO NOTHING` followed by an unconditional locked re-select. Re-run after the fix: both mutations applied, final balance correct (500 + 300 = 800), no lost update. **Passed after fix.**

This is exactly the kind of defect unit tests (which mock the DB and therefore cannot race) cannot find — the mission's rule 20 ("do not claim true concurrency based only on unit tests") is taken seriously here: this bug was only found because a real concurrent-request test was run against a real database.

## Part 19 — Global Usage Credit path re-inventory

Repository-wide search after this sprint's migration (`credit_wallet(`, `debit_wallet(`, `TenantWallet`, `wallet_transactions` combined with `grant_`/`adjust_`/`topup` context):

| Active Usage Credit mutation path | Canonical service used | Balance target | Ledger target |
|---|---|---|---|
| `UsageCreditService.adjust_credit` (manual admin adjustment) | itself (canonical) | `tenant_billing` | `usage_credit_ledger` |
| `UsageCreditService.grant_package_credit` (package purchase) | itself (canonical) | `tenant_billing` | `usage_credit_ledger` |
| `UsageCreditService.grant_topup_credit` (Finance Hub top-up, **this sprint**) | itself (canonical) | `tenant_billing` | `usage_credit_ledger` |
| `UsageCreditService.deduct_for_completed_job` (delegate) | `execution.usage_credit_deduction.deduct_for_completed_job` (certified, unchanged) | `tenant_billing` | `usage_credit_ledger` |
| `tenant_engine.add_usage_credits` admin endpoint | `UsageCreditService.adjust_credit` (adapter, FINAL-L5-05J) | `tenant_billing` | `usage_credit_ledger` |
| `package_commerce`'s `credit-wallet/*` endpoints | `UsageCreditService` (adapter, FINAL-L5-05J) | `tenant_billing` | `usage_credit_ledger` |

**Remaining, explicitly out-of-scope, unchanged Usage-Credit-adjacent code** (Commission/field-ops/provider-earning domains, per this mission's own scope limit — not migrated): `platform_commerce.admin_credit_wallet` (`/v1/commerce/.../wallet/credit`), `field_ops.BillingService.admin_wallet_topup/adjust`, `invoice_payment.ProviderCreditWalletService.admin_credit`. These write `TenantWallet`, but none of them are labeled or reachable as "Usage Credits" — they remain the Commission/provider-wallet domain's own (separately-scoped) architecture debt.

**Result: 0 active Usage Credit grants outside `UsageCreditService`. 0 active Usage Credit balance writes outside `UsageCreditService`/the certified Completed Job Deduction adapter. 0 active Usage Credit writes to `TenantWallet`. 0 active Usage Credit writes to `wallet_transactions`** — confirmed by grep, architecture guard tests, and live DB row counts (`tenant_wallets`/`wallet_transactions` still 0 after a real live-API grant was performed and later cleaned up).
