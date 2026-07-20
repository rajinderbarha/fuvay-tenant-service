# Exact Invoice Creation Contract

## Mounted route
`POST /v1/provider/invoices` (or equivalent staff route) → `ServiceInvoiceService.create_invoice` (`app/engines/invoice_payment/invoice_service.py`). Router-level authorization (persona/permission/mutation-scope) was already closed in a prior slice ("Invoice and Payment closure", preserved this slice, unchanged) — this slice's focus is the SERVICE-layer lineage validation inside `create_invoice` itself.

## Accepted identifiers and monetary fields
| Field | Classification |
|---|---|
| `job_id` | CLIENT_SUPPLIED_VALIDATED — resolved via `_get_job`, tenant-checked |
| `tenant_id` | SERVER_DERIVED — from the authenticated `UserContext`, never client body |
| `source` | CLIENT_SUPPLIED_VALIDATED — must be in `VALID_INVOICE_SOURCES` |
| `quote_id` | CLIENT_SUPPLIED_VALIDATED — **this slice adds**: must resolve to a `ServiceJobQuote` belonging to the same tenant, the EXACT `job_id` being invoiced, and a customer matching that job's customer, in `customer_approved` status |
| `notes` | CLIENT_SUPPLIED_UNSAFE in the sense of unvalidated free text, but not a security-relevant field (stored as-is, no injection surface given ORM parameterization) |
| `user_id` | SERVER_DERIVED |
| `request_id` | SERVER_DERIVED (from request middleware) |
| Currency | QUOTE_DERIVED implicitly — the invoice does not carry its own currency field distinct from the quote's (both hardcoded `"INR"` codebase-wide; no explicit currency-match check exists because there is only one currency value possible, so a mismatch cannot occur) |
| Line items | QUOTE_DERIVED — `_copy_from_quote` copies `ServiceJobQuoteItem` rows filtered to `is_customer_visible == True` |
| Subtotal/tax/discount/total | SERVICEJOB_DERIVED / recomputed — `_refresh_totals` recalculates from the copied `ServiceInvoiceItem` rows via `_recalculate` (unchanged, pre-existing), then adds the platform fee on top (unchanged, pre-existing) |

## Models
- `ServiceInvoice`/`ServiceInvoiceItem` (`app/engines/invoice_payment/models.py`).
- `ServiceJobQuote`/`ServiceJobQuoteItem` (`app/engines/quote_checklist/models.py`) — read-only reference, no write.
- `ServiceJob` (`app/engines/final_records/models.py`) — read-only reference for tenant/customer/booking/category/offering.

## Duplicate-invoice check (unchanged, pre-existing)
`create_invoice` rejects a second active (non-cancelled) invoice for the same `job_id` before any new invoice is created.

## Commit ordering (this slice reordered validation, not effects)
Before this slice: `db.add(inv)` → `db.flush()` → quote validation (AFTER persistence). After this slice: ALL validation (duplicate check, quote tenant/ServiceJob/customer/status match) happens BEFORE `db.add(inv)` — a rejected `create_invoice` call now leaves zero trace in the database (see `no-partial-persistence-proof.md`).

## Audit/notification
`_log_event(db, inv, FEV_INVOICE_CREATED, "staff", user_id, ...)` — unchanged, runs after all persistence, before `db.commit()`.
