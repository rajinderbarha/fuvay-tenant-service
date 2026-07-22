# Quote/Job/Item Ownership

## The defect (IDOR)
`ServiceJobQuoteService.get_quote(db, quote_id)` and `ServiceChecklistService.get_checklist(db, checklist_id)` accepted ONLY the record ID — no tenant, no customer, no ownership parameter of any kind. Every router call site (`provider_get_quote`, `staff_get_quote`, `customer_get_quote`, `staff_get_checklist`) called these methods with no scoping argument at all, despite the caller's `tenant_id`/`user_id` being available. This meant **any authenticated user of any role or tenant could fetch any quote's or checklist's full detail by ID alone**, including `provider_internal_notes` (a field explicitly modeled as provider-only) and full customer PII embedded in the quote/checklist.

`list_quote_events` had a `tenant_id` parameter but it defaulted to `None` and was never passed by `customer_quote_events` — the customer-facing event-history route had the same unrestricted-by-ID exposure.

## The fix
- `get_quote(db, quote_id, tenant_id=None, customer_id=None)` — raises `QUOTE_ACCESS_DENIED` if either supplied identifier doesn't match.
- `get_checklist(db, checklist_id, tenant_id=None)` — raises `CHECKLIST_ACCESS_DENIED` on mismatch.
- `list_quote_events(db, quote_id, tenant_id=None, customer_id=None)` — now also accepts and enforces `customer_id`.
- Every router call site updated to pass its own scoping identifier: provider/staff/admin pass `tenant_id=str(user.tenant_id)`; customer passes `customer_id=str(user.user_id)`; `admin_router.py`'s routes intentionally pass neither (super_admin bypasses ownership by design, matching the established platform-admin pattern from every other closed slice in this initiative).

## Job/execution ownership
`create_quote` (pre-existing) and `create_checklist` (fixed this slice) both look up the parent `ServiceJob` and verify `job.tenant_id == tenant_id` before creating any quote/checklist row — a fabricated or cross-tenant `job_id` is rejected with `QUOTE_JOB_NOT_FOUND`/`CHECKLIST_ACCESS_DENIED` before any persistence.

## Line-item/checklist-item parent ownership
`update_item`/`remove_item` query `ServiceJobQuoteItem.id == item_id, ServiceJobQuoteItem.quote_id == q.id` — an item ID belonging to a DIFFERENT quote can never be substituted in (the compound WHERE clause requires both to match; a mismatched item_id simply returns no row, raising `QUOTE_ITEM_INVALID`). `update_checklist_item` uses the identical pattern (`ServiceJobChecklistItem.id == item_id, ServiceJobChecklistItem.checklist_id == cl.id`).

## Cross-tenant/cross-customer/cross-Job/cross-quote substitution — all fail
| Substitution attempt | Mechanism that rejects it |
|---|---|
| Quote for foreign tenant | `_assert_tenant` (pre-existing) |
| Quote for foreign customer (read) | `get_quote`'s new `customer_id` filter (this slice) |
| Foreign quote item substituted into a different quote's update/remove call | Compound `id == item_id AND quote_id == q.id` filter (pre-existing) |
| Job ID from a different tenant supplied to create_quote/create_checklist | `job.tenant_id == tenant_id` check (pre-existing for quote, added this slice for checklist) |
| Customer ID supplied to override ownership | Not possible — `customer_approve`/`reject`/`request_revision` never accept a customer_id from the request body; it is always `user.user_id` from the router |

## Foreign record denials reveal no private details
`QUOTE_NOT_FOUND`, `QUOTE_ACCESS_DENIED`, `QUOTE_ITEM_INVALID`, `CHECKLIST_NOT_FOUND`, `CHECKLIST_ACCESS_DENIED` are generic error codes carrying no information about which tenant/customer/quote actually exists — consistent with the privacy-safe error pattern established across this whole initiative.
