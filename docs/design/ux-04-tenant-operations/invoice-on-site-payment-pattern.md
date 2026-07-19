# Invoice / On-Site Payment Pattern

Type: `InvoiceView` (`lib/ux04/types.ts`) — `quoteTotal`, `invoiceTotal`,
`state` (`not_generated | draft | issued | payment_expected_on_site |
payment_recorded | partial | disputed | voided`), `paymentMethodRecord`
(a record of what happened on-site, explicitly not a platform-processed
payment), `creditDeductionAmount`, `commissionDeductionAmount`.

Included in `JobDetailView.invoice` and `lib/ux04/fixtures.ts`
(`invoiceFixture`, state `payment_expected_on_site`), but **no dedicated
UI section renders it in the built Job Detail Workspace route yet** — the
type/fixture exist for a one-section addition. No capture/refund/payout
action exists anywhere in the type — by construction there is no field or
method that could carry one.
