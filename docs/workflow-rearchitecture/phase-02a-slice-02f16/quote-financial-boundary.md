# Quote Financial Boundary

## Finding: zero financial code in quote_checklist itself
Repo-wide search within `app/engines/quote_checklist/*.py` for `Invoice`, `Payment`, `Commission`, `Credit`, `Refund`, `wallet` returns **no matches**. This module contains no invoice, payment, commission, credit, refund, security-deposit, or wallet code whatsoever.

## Finding: a real, one-directional integration exists in `invoice_payment` — and it had a same-record bypass, now fixed
`app/engines/invoice_payment/invoice_service.py` imports `ServiceJobQuote`/`ServiceJobQuoteItem` directly (`_copy_from_quote`) — when a staff member creates an invoice with `source="approved_quote"` and a `quote_id`, the invoice's line items are copied from the referenced quote's items. **Before this slice, this copy happened with NO verification that the referenced quote belonged to the caller's tenant, or was actually in `customer_approved` status** — a staff member could fabricate an invoice from a draft/rejected quote, or (if the UUID were known) copy a DIFFERENT tenant's quote items into their own invoice. The check was also performed AFTER the invoice row had already been inserted (`db.add(inv)`/`await db.flush()`), so a rejected call would still leave a partial `INV_DRAFT` invoice behind.

**Fixed** (smallest safe correction, per this slice's explicit permission to fix a "directly connected same-record bypass"): `create_invoice` now looks up the referenced `ServiceJobQuote` BEFORE any persistence, and requires `quote.tenant_id == tenant_id` (raises `INVOICE_ACCESS_DENIED`) and `quote.status == "customer_approved"` (raises `INVOICE_INVALID_STATUS`) before creating the invoice or copying any item. This is a one-line-of-reasoning fix inside `invoice_payment`'s own service — it does not touch `quote_checklist`'s models, routes, or state machine, and does not build any new financial infrastructure (the invoice creation capability already existed; this only closes its input validation).

## What quote approval actually does
`customer_approve` (the only "approval" action in this module):
1. Validates ownership and legal transition.
2. Updates `ServiceJobQuote.status` → `customer_approved`, sets `locked_at`/`approved_at`.
3. Syncs `ServiceJob.status` → `quote_approved`.
4. Writes a `ServiceJobQuoteEvent` audit row.
5. Sends a notification to the provider side.

**It authorizes future work only** — no invoice is created, no payable amount is changed, no credit is reserved, no commission is deducted, no payment is recorded. The `customer_payable_amount` field is a display/reference figure computed from line items; it is not read or acted upon by any invoice/payment service in this codebase (confirmed — no cross-module reference from `invoice_payment` engine into `quote_checklist` models, and no reference the other direction).

## Verified requirements
| Requirement | Status |
|---|---|
| Customer approval alone cannot record real payment | Trivially true — no payment-writing code exists in this module |
| Rejection creates no invoice/payment | Trivially true — same reason |
| Duplicate approval does not create duplicate invoice | Trivially true — no invoice creation exists to duplicate; the idempotency-key short-circuit additionally prevents even a duplicate STATUS transition |
| Provider cannot use quote routes to record arbitrary payment | Trivially true — no route or service method in this module writes to any payment/invoice/commission table |
| Existing invoice/payment services remain authoritative | Confirmed — this slice made no changes to `app/engines/invoice_payment/*` |
| Cross-tenant financial records cannot be referenced | N/A — no financial record reference exists to be cross-tenant in the first place |
| Denied actions create no financial record | Trivially true |

## Out of scope, not built
Per this slice's explicit instructions, no invoice/payment/refund/credit infrastructure was built to connect quote approval to a real financial consequence. If a future product decision requires "approving a quote automatically creates a draft invoice," that is a new integration requiring its own dedicated slice — not addressed here (see `product-decisions-required.md`).
