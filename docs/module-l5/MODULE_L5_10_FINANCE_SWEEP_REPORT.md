# MODULE-L5-10 — Finance, Ledger, Invoice & Commission — Sweep Report

## Status
Deep sweep complete. **8 real defects fixed + 3 revenue features built**, every fix
proven live and regression-locked. 505 finance-domain tests pass.

This report is honest about scope: it certifies the money-movement core
(wallet / deposit / commission / invoice / credits) that was swept line-by-line.
It does **not** claim every peripheral finance report/export is exhaustively
audited.

## Defects fixed (all were live money/security bugs)

| # | Defect | Why it mattered |
|---|--------|-----------------|
| 1 | `reverse_commission` credited the wallet with no status guard | Reversing a never-deducted commission minted free provider credits |
| 2 | `confirm_purchase` had no idempotency guard | A duplicate top-up confirm (client + webhook / retry) replenished the deposit twice and double-counted revenue |
| 3 | `refund_deposit` unguarded | Negative amount inflated the deposit; a partial refund left `status=refunded` with balance>0, so a second call drew more money out |
| 4 | `refund_topup` overwrote `refunded_amount`, no cap | Lost prior partial refunds; allowed recording a refund larger than paid |
| 5 | `record_offline_deposit` unguarded | Negative amount reduced the deposit; same bank reference double-credited it |
| 6 | Ledger primitives had no amount guard | `debit_wallet`/`credit_wallet`/`debit_deposit`/`credit_deposit` moved money the WRONG way on a negative amount — root-cause class |
| 7 | `get_payment_timeline` ignored its `tenant_id` | Cross-tenant IDOR: any provider could read any other tenant's invoice payment records |
| 8 | Commission was a hardcoded flat 10% | No way to price a Rs.200 salon visit differently from a Rs.50,000 real-estate deal |

## Revenue features built

- **Per-category provider commission** (migration 139) — `service_categories.commission_pct`,
  category-aware `_resolve_rate`, admin API + page.
- **Per-category customer charge** (migration 140) — a platform fee added to what
  the customer pays, shown as included in the booking price snapshot.
- **Invoice-level revenue capture** (migration 141) — `platform_fee_amount` on the
  invoice; `customer_payable_amount` = service value + fee; commission charged on
  the service value only (never on the platform's own fee); the fee is booked as
  a `platform_customer_fee_charged` financial event at payment.

Proven live on a Rs.500 Home Services job (commission 10% + customer charge 10%):
customer pays Rs.550; platform earns Rs.50 (customer fee) + Rs.50 (commission) =
Rs.100.

## Invariants verified sound (and regression-locked)

- Security-deposit balance is a derived property → cannot be over-drawn.
- A plain wallet credit never phantom-replenishes the deposit.
- `confirm_deposit` is idempotent on its payment reference.
- Dispute-settlement execution is guarded against double-execution.
- Job-completion usage-credit deduction is idempotent (DB unique index
  `uq_ucl_job_event_once`) — bulletproof even under concurrency.
- Invoice cancellation is blocked once paid/collected, so commission can never be
  orphaned by a cancel.
- Customer-credit redemption never over-applies and never drives payable negative.

## The single through-line

The finance code was correct on the happy path but systematically missing the
three invariants a payment system must never lack: **amount validation,
idempotency, and double-action guards**. Every entry point that moved money had a
sibling right next to it that already had the guard the buggy one lacked
(`confirm_deposit` was idempotent; `confirm_purchase` was not — etc.). Those are
now enforced at both the service layer and the ledger-primitive layer.
