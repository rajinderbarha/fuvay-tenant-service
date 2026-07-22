# Real-Money vs. Platform-Credit Boundary — Workstream 5

| Mutation | Amount classification | Money moves? | Client-supplied? | Server-derived? | Validated against canonical data? |
|---|---|---|---|---|---|
| `admin_topup_wallet` | PLATFORM_CREDIT | NO (internal ledger only) | YES (`payload.get("amount")`) | NO | Delegates to `UsageCreditService` (not re-audited for internal validation) |
| `admin_adjust_wallet` | PLATFORM_CREDIT | NO | YES | NO | Same; requires a non-empty `reason` (enforced) |
| `admin_purchase_package` | PACKAGE_PRICE (recorded, not charged) | Records a `payment_reference` string only — does not itself call any payment gateway | Reference string, not amount, is client-supplied | Price comes from the `Package` record (canonical), not client input | YES — package price is server-side, only the payment reference is client-supplied |
| `adjust_deposit`/`approve_deposit`/`refund_deposit`/`record_offline_deposit`/`reject_deposit` (finance_hub) | SECURITY_DEPOSIT | Represents a real, tenant-facing security deposit (may correspond to real money held/returned) | Not traced this slice (internals of `_svc` not re-audited) | Not traced this slice | Not traced this slice — flagged in `known-limitations.md` |
| `approve_payout`/`mark_completed`/`mark_failed`/`mark_processing`/`reject_payout` | REAL_MONEY_PAYMENT (provider payout) | Represents real money leaving the platform to a provider — the highest-stakes classification in either module | Not traced this slice | Not traced this slice | Not traced this slice — flagged, and separately blocked from `admin_finance` by the permission-grant gap (see `product-decisions-required.md`) |
| `approve_claim`/`assign_reviewer`/`reject_claim`/`request_documents`/`settle_claim` | ACCOUNTING_RECORD / potentially REAL_MONEY_PAYMENT if settlement pays out | Settlement (`settle_claim`) likely triggers a real payment or credit — internals not traced this slice | Not traced | Not traced | Not traced — flagged |
| `refund_topup`/`retry_credit` | PLATFORM_CREDIT (reversal of a prior top-up) | NO (internal ledger reversal) | Not traced | Not traced | Not traced — flagged |
| `admin_calculate_commission`/`admin_deduct_commission` | COMMISSION_AMOUNT | Represents platform commission deducted from a completed job — real accounting impact, not necessarily cash movement | Not traced (internals not re-audited) | Not traced | Not traced — flagged |
| Security-deposit mark-paid/refund/forfeit (package_commerce, deprecated) | N/A | NO — endpoints always raise 410 before any logic runs | N/A | N/A | N/A |

## Conclusions
- **Internal platform credit** (`TenantWallet`/`UsageCreditService`) is
  correctly NOT treated as a cash wallet anywhere in this module — it
  represents a usage-quota-style internal ledger, consistent with its
  historical fix (FINAL-L5-05J) away from a naive balance field.
- **The highest real-money stakes** are `finance_hub.admin_router`'s
  payout endpoints — and these are exactly the ones currently unreachable
  by `admin_finance` (permission-bundle gap), meaning the highest-stakes
  capability in either module has the least-verified real-world usage
  path today. This is the central finding motivating this slice's module
  selection (see `module-readiness-decision.md`).
- **No payout behavior was added or changed** this slice, consistent with
  the mission's explicit prohibition.
