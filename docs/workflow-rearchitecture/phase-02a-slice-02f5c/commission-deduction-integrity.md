# Commission Calculation and Deduction Integrity — Workstream 7

## Scope note
This document is limited to the exact record type used by
`package_commerce`'s own commission methods (`CommissionRecord`, imported
from `platform_commerce.models` — see `alternate-commerce-route-audit.md`
for the cross-module relationship). Platform-wide Booking/Job ownership
is explicitly not resolved here.

## Routes and methods
- `admin_calculate_commission` → `PackageCommerceService.calculate_commission(job_id, tenant_id, job_value, invoice_id, payment_id)`
- `admin_deduct_commission` → `PackageCommerceService.deduct_commission(job_id, tenant_id)`

Both are gated by `Depends(require_super_admin)` directly (a role check,
not a `require_permission(P.*)` call) — this is a stricter, not weaker,
guard than the rest of the module's `PACKAGES_*`-permission-gated routes,
and is still classified `PLATFORM_PACKAGE_ADMIN_MUTATION` (super-admin
only) since no role but super_admin can pass `require_super_admin`.

## `calculate_commission`
- Dedupes on `job_id`: if a `CommissionRecord` already exists for this
  `job_id`, returns it unchanged (`select(CommissionRecord).where(job_id==job_id)`)
  — a second call is a safe no-op, not a duplicate calculation.
- `job_value` is **client-supplied** (admin-trusted input in the request
  body) — not independently re-derived from an invoice or job record
  within this method. `invoice_id`/`payment_id` are stored as linkage
  metadata only, not used to cross-check `job_value`.
- Commission rate is **server-resolved** via `_resolve_commission_rate(tenant_id)`
  — the client cannot choose the rate.
- Creates a `status="pending"` record; does not touch the wallet.

## `deduct_commission`
- Requires an existing `CommissionRecord` for `job_id` (`COMMISSION_NOT_FOUND`
  if missing).
- **Rejects a tenant mismatch**: `record.tenant_id != tenant_id` raises
  `TENANT_ACCESS_DENIED` — confirmed the wrong tenant cannot deduct
  against another tenant's commission record.
- **Blocks double-deduction**: `record.status == "deducted"` raises
  `COMMISSION_ALREADY_DEDUCTED`.
- Insufficient-balance path sets `status="failed"` and returns without
  debiting — a failed deduction does not mark the commission complete.
- On success, debits via the shared `debit_wallet` ledger primitive with
  a **stable idempotency key**: `f"commission-deduct-{record.id}"` — a
  retried deduct call for the same record cannot double-debit (the
  ledger primitive's own idempotency-key dedup applies here, same
  mechanism verified for `finance_hub`'s `retry_credit_posting` in Slice
  2F-5B).
- Deduction (`debit_wallet` call + `CommissionRecord` status update) and
  ledger update happen within the same request/transaction — no partial-
  commit window was found between debiting the wallet and marking the
  record `deducted`.

## Verified findings
- Client cannot choose the commission amount at deduction time (it was
  already fixed by `calculate_commission` and re-read from the stored
  record, not re-supplied by the caller of `deduct_commission`, which
  takes no amount parameter at all).
- Commission is deducted only once per `CommissionRecord` (job_id-keyed).
- Repeated `deduct_commission` requests do not double-deduct (status
  guard + stable idempotency key — two independent protections).
- Wrong tenant is rejected.
- No "incomplete job cannot be charged" precondition was found inside
  `package_commerce` itself — `calculate_commission`/`deduct_commission`
  trust the caller (a super_admin) to only invoke this for a legitimately
  completed job. This module has no direct linkage to a `Job`/`ServiceJob`
  completion-status field. Not flagged as a defect (job-completion
  policy enforcement, if any, lives in whichever pipeline actually calls
  this — see `alternate-commerce-route-audit.md`), but noted as a
  limitation.
- No cross-pipeline adapter was introduced by this slice.

## Not fixed (would require a product decision or cross-module change)
- `job_value` being trusted, client-admin-supplied input rather than
  independently derived from an invoice.
- The relationship between this two-step (calculate → deduct) commission
  path and the separate, single-step `platform_commerce.CommerceService.deduct_commission`
  path used by the real job-completion billing pipeline (`field_ops`,
  `invoice_payment`) — both write the identical `CommissionRecord` table
  keyed by `job_id`, but a bug analysis of `platform_commerce`'s own code
  is out of scope (that module is not `package_commerce.admin_router`).
  See `alternate-commerce-route-audit.md` for the full disposition and
  `product-decisions-required.md` for the open question this raises.
