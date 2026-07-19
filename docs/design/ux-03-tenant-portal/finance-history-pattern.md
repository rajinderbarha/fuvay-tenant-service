# Finance History Pattern

`/dev/ux-03/finance-history` — `TenantListPage` over
`FinanceTransactionFixture`, columns: type, amount, date, note. `kind`
values (`credit_issue`, `credit_consume_commission`, `deposit_hold`,
`deposit_release`, `invoice_settlement_record`) are read-only records; no
invented mutation actions (no "reverse transaction" or similar button).
Export is presentation-only (no wired download this phase).
