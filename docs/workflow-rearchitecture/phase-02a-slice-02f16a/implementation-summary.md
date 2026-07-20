# Slice 2F-16A — Implementation Summary

## Scope
Close the 9 items 2F-16 left unapproved: exact quote-to-ServiceJob/customer linkage in invoice creation, hidden-item total effects, invoice/quote item-set equivalence, privacy equivalence of `QUOTE_NOT_FOUND`/`QUOTE_ACCESS_DENIED`, field-level privacy across every customer read, final-state immutability across every customer-visible field, canonical-role behavior of `require_owner_or_office_staff_mutation`, and full SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY closure.

## Code changes

### 1. Invoice cross-ServiceJob/cross-customer lineage (`invoice_payment/invoice_service.py`)
2F-16 validated only `quote.tenant_id == tenant_id`. Added `quote.job_id == job.id` and `quote.customer_id == job.customer_id` checks, both positioned before any persistence. Closes a same-tenant substitution where an approved quote from a DIFFERENT ServiceJob (or customer) could be copied into an unrelated job's invoice.

### 2. Hidden-item total reconciliation (`quote_checklist/quote_service.py::get_quote`)
The stored `total_amount`/`customer_payable_amount` includes ALL items (correct for the provider view). The customer-facing response now recomputes these fields from ONLY the customer-visible items being returned, so the displayed total always reconciles to the itemized list — matching what `invoice_payment._copy_from_quote` actually invoices.

### 3. Privacy-equivalent foreign-vs-missing errors (`get_quote`, `list_quote_events`, `get_checklist`)
Foreign-tenant/foreign-customer ownership mismatches now raise the SAME `*_NOT_FOUND` code as a genuinely missing record (previously `*_ACCESS_DENIED`, externally distinguishable via a different HTTP status).

### 4. Provider-only event filtering (`list_quote_events`)
A customer caller now only sees `CUSTOMER_VISIBLE_QUOTE_EVENT_TYPES` (sent/approved/rejected/revision-requested/revised/expired/cancelled) — draft-editing and internal approval-step events are excluded.

### 5. Customer-decision response filtering (`customer_approve`/`customer_reject`/`customer_request_revision`)
These previously returned `q.to_dict()` directly, bypassing `get_quote`'s own filtering entirely. A new `_customer_dict` helper (async, strips `provider_internal_notes`, recomputes totals from visible items) is now used at every customer-decision return point except the idempotent-repeat-approval short-circuit (kept lightweight by design, see `known-limitations.md`).

## Test results
- New file `tests/test_phase2f16a_quote_invoice_lineage_and_read_privacy.py`: 17/17 passing.
- 5 pre-existing tests updated (expected-error-code changes matching the deliberate privacy fix, and mock-scaffolding additions for new queries) — no behavioral weakening.
- Full regression sweep: **1747 passed, 3 skipped, 0 failed** (live-environment tests excluded and reported separately).
- Runtime verification: all 5 re-checked modules exit 0, unchanged from 2F-16 baseline.
- Canonical coverage unchanged: **186/227** (no route added/removed/reclassified this slice).

## Final status
`SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED_PRODUCT_POLICY_BLOCKED` — see `approval-gate.md`.
