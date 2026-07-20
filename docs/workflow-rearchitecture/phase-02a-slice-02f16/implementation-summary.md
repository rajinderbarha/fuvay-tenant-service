# Slice 2F-16 — Implementation Summary

## Module discovered
`app.engines.quote_checklist` (Sprint 22 "Quote Approval + Checklist Engine"): 6 mounted routers (`provider_router`, `staff_router`, `checklist_router` — all defined in `provider_router.py`; `customer_router`; `admin_router`, `admin_quote_router` — both in `admin_router.py`). Parent pipeline confirmed as `app.engines.final_records.models.ServiceJob` (NOT `field_ops.Job`, which has its own separate `JobQuote` model/pipeline; NOT `Booking`/`ServiceBooking` directly).

## Defects found and fixed

1. **Zero authorization on 11 provider/staff/checklist mutation routes.** `provider_router.py`'s mutation routes used only `Depends(get_current_user)` — any authenticated user of any role/tenant (customer, technician, cross-tenant staff) could create/edit/delete quote items, send quotes to customers, cancel quotes, or complete checklists for any job in any tenant. Fixed with `require_owner_or_office_staff_mutation` (existing dependency, no new role/permission; excludes technician — no technician frontend caller was found, only tenant-portal web staff UI calls these routes).

2. **IDOR on `get_quote`/`get_checklist`/`list_quote_events`.** No ownership filter existed at all — any authenticated user could fetch any quote or checklist's full detail by ID, including `provider_internal_notes`. Fixed: these methods now accept and enforce `tenant_id`/`customer_id`.

3. **No explicit canonical-customer role check on `customer_router.py`.** Ownership already made cross-customer impersonation impractical (customer_id was always server-derived), but non-customer roles could still reach these routes. Fixed with `require_customer`.

4. **`create_checklist` trusted client-supplied `job_id`/`tenant_id` with zero validation.** Fixed to mirror `create_quote`'s own job-ownership check.

5. **No negative quantity/price validation** on `add_item`/`update_item`. Fixed.

6. **Post-final/post-send item mutation was possible.** `_assert_not_locked` only checked `locked_at` (set only on customer approval) — a `sent_to_customer` or rejected/expired/cancelled quote could still have its items silently mutated. Fixed with `ITEM_EDITABLE_QUOTE_STATUSES`.

7. **`invoice_payment.create_invoice`'s `source="approved_quote"` path had a same-record bypass** (found via alternate-route audit, in a different module but directly connected): it copied line items from ANY `quote_id` with no tenant/status validation, and the (fixed) validation initially would have run after persistence. Fixed: validates the referenced `ServiceJobQuote`'s tenant and `customer_approved` status BEFORE any invoice row is created.

8. **Provider-internal fields leaked to customer reads.** `get_quote` returned `provider_internal_notes` and non-`is_customer_visible` items to every caller, including customers. Fixed: both are now stripped whenever the caller supplies `customer_id`.

## Boundaries confirmed, not touched
- `field_ops.JobQuote` — a distinct model/table/pipeline tied to `field_ops.Job`, already closed in the 2F-14 series; no same-record bypass exists (no ID overlap possible).
- `PartsRequest` — zero reference anywhere in `quote_checklist`; "part"/"material" quote line items are cost entries only, never linked to an actual `PartsRequest` row.
- `Booking`/`ServiceBooking` — `booking_id` is denormalized for query convenience only; no FK relationship, no authorization logic depends on it.

## Test results
- New file `tests/test_phase2f16_quote_checklist_authorization.py`: 21/21 passing.
- 1 pre-existing test fixed (additive mock scaffolding only).
- Canonical coverage test updated: 227/186.
- Full broad partition sweep: **1753 passed, 9 skipped, 0 failed**.
- Runtime verification: `quote_checklist.provider_router` (11/11), `.customer_router` (3/3), `.admin_router` (2/2) all exit 0; `field_ops.router` (28/28), `field_ops.staff_router` (6/6), `booking.router` (11/11) unaffected.

## Final status
`SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED_PRODUCT_POLICY_BLOCKED` — see `approval-gate.md`.
