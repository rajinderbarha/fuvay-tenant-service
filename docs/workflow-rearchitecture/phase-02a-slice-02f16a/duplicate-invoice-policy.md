# Duplicate Invoice Policy

## Classification: **ONE_QUOTE_ONE_INVOICE** (enforced at the Job level, not the Quote level directly)

`create_invoice`'s pre-existing (unchanged) duplicate check:
```python
res = await db.execute(select(ServiceInvoice).where(
    ServiceInvoice.job_id == job.id, ServiceInvoice.status.not_in([INV_CANCELLED])))
if res.scalar_one_or_none():
    raise ValueError(ERR_INVOICE_ALREADY_EXISTS)
```
This is scoped to `job_id`, not `quote_id` directly — but since 2F-16A now requires `quote.job_id == job.id`, and a ServiceJob can only have ONE active invoice at a time, the practical effect is that one APPROVED quote can produce at most one active invoice (a second `create_invoice` call for the same job — regardless of which quote_id is supplied — is rejected while any non-cancelled invoice exists for that job).

## No versioning, no replacement, no credit/reversal records
Confirmed via source read: no invoice-versioning field exists on `ServiceInvoice`, no "replace" or "supersede" capability exists in `invoice_service.py`, and no credit/reversal record is created by `create_invoice`. If a tenant needs to correct an issued invoice, the only mechanism visible in this codebase is cancelling the existing invoice (`status = INV_CANCELLED`, a capability outside this slice's scope) and creating a new one.

## Repeated/concurrent creation
Directly proven by the pre-existing (unaffected by this slice) duplicate-check test coverage in `test_sprint23_invoice_payment.py`, re-verified via full regression. A second `create_invoice` call for the same job while an active invoice exists raises `INVOICE_ALREADY_EXISTS` — no new invoice or invoice item is created.

## No versioning invented
Per this slice's explicit scope limit ("Do not invent versioning"), no change was made to this policy — it is documented as-is.
