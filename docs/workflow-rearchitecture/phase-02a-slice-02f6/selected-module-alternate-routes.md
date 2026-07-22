# Alternate Route Audit — Workstream 9

## Method
Searched for every mounted route writing `ServiceInvoice`,
`ServiceInvoiceItem`, or `ServicePaymentRecord`.

## Findings

### `invoice_payment.admin_router`
Platform-admin CRUD/actions over the same tables, gated by
`Depends(require_super_admin)` on every mutation (re-confirmed via
grep — all 14 mutation dependencies in this file are
`require_super_admin`). This is a **stronger**, not weaker, alternate —
no action required.
**Disposition: PLATFORM_ONLY.**

### `invoice_payment.customer_router`
`customer_apply_credit` (applies the customer's own service credit to
their own invoice) and `customer_confirm_payment` (customer confirms
receipt/payment) — both gated by `get_current_user` only, but both
independently verify ownership via `user.user_id` matching
(`get_invoice_for_customer(db, invoice_id, user.user_id)` and
`customer_confirm_payment(db, invoice_id, user.user_id, ...)`). This is
a **distinct capability** (customer-side confirmation/credit-application,
not provider-side issuance/payment-recording) with its own, already-
correct ownership enforcement — not a weaker alternate for the 4 routes
this slice protects.
**Disposition: CUSTOMER_ONLY.**

### `field_ops` / `home_service_assignment`
Grepped for any direct write to `service_invoices`/
`service_payment_records` outside `invoice_payment/*` — none found.
ServiceJob status is updated by `issue_invoice` itself (`JOB_STATUS_INVOICE_ISSUED`),
not by a separate job-pipeline route reaching back into invoice tables.
**No alternate route found in this domain.**

## Summary table

| Capability | Selected route | Alternate | Canonical owner | Disposition |
|---|---|---|---|---|
| Invoice issue/create/item-add, payment recording | `invoice_payment.provider_router` (this slice) | `invoice_payment.admin_router` (super_admin) | `invoice_payment.provider_router` for provider/staff persona | PLATFORM_ONLY (alternate is stronger) |
| Customer credit-apply / payment-confirm | `invoice_payment.customer_router` | none | `invoice_payment.customer_router` | CUSTOMER_ONLY |

## Conclusion
No weaker connected alternate route was found. Both alternates are
either stronger (`admin_router`) or a distinct, already-correctly-scoped
capability (`customer_router`). Nothing to close.
