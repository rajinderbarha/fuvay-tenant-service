# Credit / Commission Operations

Built: `components/ux04/CreditCommissionSummary.tsx`, used in Job Detail
Workspace, type `CreditCommissionView`.

Shows: current package credit balance, estimated commission for the
current job, credit-after-deduction, low-credit warning,
insufficient-credit blocker, duplicate-deduction-prevented confirmation,
transaction ref (null when not yet recorded). Explicit footer copy states
credit is not customer money, commission is not a payout, and deposit/
on-site-payment are tracked separately — this is deliberate, not filler,
given how often this distinction gets blurred in provider-ops UIs.

Reconciliation view (`FinanceTransactionFixture[]` history, reused from
UX-03) is not rendered by this component — it consumes the per-job
snapshot only. A separate finance-history route (UX-03 already has one)
is the natural place for the ledger view; not duplicated here.
