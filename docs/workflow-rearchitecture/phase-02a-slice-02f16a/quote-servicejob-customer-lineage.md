# Quote → ServiceJob → Customer Lineage

## The gap 2F-16 left open
2F-16's `create_invoice` fix validated only `quote.tenant_id == tenant_id`. It never checked:
- `quote.job_id == job.id` (the SPECIFIC ServiceJob being invoiced)
- `quote.customer_id == job.customer_id`

Both are same-tenant checks — a malicious or buggy staff-side caller within ONE tenant could supply `job_id=<Job A>` and `quote_id=<Job B's approved quote>` (both belonging to the same tenant) and the 2F-16-era check would pass, silently attributing Job B's negotiated price/items to Job A's invoice (and, transitively, to Job A's customer — who never approved that quote).

## The fix
```python
if quote.job_id != job.id:
    raise ValueError(ERR_INVOICE_ACCESS_DENIED)
if quote.customer_id != job.customer_id:
    raise ValueError(ERR_INVOICE_ACCESS_DENIED)
```
Both checks run immediately after the tenant check, before any persistence (`db.add(inv)` has not yet been called at this point — see `exact-invoice-creation-contract.md`).

## Proof: genuine same-tenant mismatched fixtures used
`TestInvoiceQuoteServiceJobCustomerLinkage` (`tests/test_phase2f16a_quote_invoice_lineage_and_read_privacy.py`) uses a SINGLE `tenant_id` shared between the ServiceJob and the quote in every test — the fixtures never rely on cross-tenant mismatch (already covered by 2F-16's own tenant check) to prove this gap; they specifically construct a same-tenant, different-`job_id` quote and a same-tenant-same-job, different-`customer_id` quote.

## Relationships proven
| Relationship | Enforced by |
|---|---|
| Quote belongs to principal tenant | `quote.tenant_id == tenant_id` (2F-16, unchanged) |
| ServiceJob belongs to principal tenant | `job.tenant_id == tenant_id` (pre-existing, unchanged) |
| `Quote.job_id` equals the invoice ServiceJob | **New this slice**: `quote.job_id == job.id` |
| Quote customer equals ServiceJob customer | **New this slice**: `quote.customer_id == job.customer_id` |
| Invoice customer is derived from ServiceJob | `customer_id=job.customer_id` in the `ServiceInvoice(...)` constructor (pre-existing, unchanged) — never taken from the quote or the request body directly |
| Request customer_id cannot override authoritative customer | Confirmed — `create_invoice`'s signature has no `customer_id` parameter at all; it is ALWAYS `job.customer_id` |
| Quote is approved | `quote.status != "customer_approved"` check (2F-16, unchanged) |
| Quote items belong to the Quote | `ServiceJobQuoteItem.quote_id == uuid.UUID(quote_id)` filter in `_copy_from_quote` (pre-existing, unchanged) |
| Invoice items originate only from the validated Quote | `_copy_from_quote` is the ONLY item-seeding path for `source="approved_quote"` (pre-existing, unchanged) |
| A Quote from ServiceJob A cannot invoice ServiceJob B | **New this slice** — proven by test |
| A Quote for Customer A cannot invoice Customer B | **New this slice** — proven by test |
