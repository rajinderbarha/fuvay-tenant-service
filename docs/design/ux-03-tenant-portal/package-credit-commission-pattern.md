# Package / Credit / Commission / Security Deposit Pattern

Four distinct fixture types, deliberately never merged into one "balance":

- `PackageCreditFixture` — plan name, credit balance, issued/consumed this
  cycle, commission rate (bps), cycle end date.
- `SecurityDepositFixture` — required/held amount, status
  (`not_required`/`pending`/`held`/`partially_released`/`released`/`forfeited`),
  history.
- `FinanceTransactionFixture` — a ledger row tagged by `kind`
  (`credit_issue` | `credit_consume_commission` | `deposit_hold` |
  `deposit_release` | `invoice_settlement_record`), never a generic
  "payment" kind.

Commission is deducted FROM the package credit balance on job completion —
never presented as a separate payment the tenant makes. The platform does
not process ordinary on-site customer-to-provider payments, so no
payout/withdrawal/settlement action appears anywhere in this phase's pages;
`invoice_settlement_record` in the finance-transaction `kind` enum is a
read-only record of a settlement that happened elsewhere, not a UI action.

`permissions-and-pipelines.test.ts` asserts the package-credit fixture has
no deposit field and vice versa, guarding against future accidental
merging.
