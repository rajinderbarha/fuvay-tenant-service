# Slice 2F-6 Implementation Summary

## Scope
Global tenant-facing mutation reconciliation, followed by selection and
full authorization closure of exactly one remaining unclosed module:
`app.engines.invoice_payment.provider_router` (4 mutation routes).

## Reconciliation
Re-ran the runtime mutation inventory tool with no filter. Confirmed
183 tenant-facing mutations platform-wide (exact match to the historical
figure). The previously-reported "~85 protected" figure was independently
re-verified as **correct** (85, using the file's own established
counting convention of scope/role-aware guards only, excluding
`PLATFORM_ADMIN_ONLY` routes from the "protected tenant mutation"
numerator) — an early draft of this slice's own reconciliation doc
initially miscalculated 93/97 by conflating "verified/accepted" with
"protected"; this was caught and corrected before delivery.

## Selection
Ranked all 19 remaining unclosed tenant-facing modules (see
`remaining-module-priority-matrix.csv`). Selected
`invoice_payment.provider_router` — the highest-ranked module in the
mission's priority category 2 ("finance or credit mutations exposed to
tenant personas"), found completely unprotected
(`AUTHENTICATED_ONLY_NO_PERMISSION_CHECK` on all 4 routes: any
authenticated user of any role could issue an invoice or record an
on-site payment for any tenant's job before this slice).

## What changed
1. **`app/engines/invoice_payment/provider_router.py`** —
   `provider_issue_invoice` now requires
   `require_tenant_mutation_permission(P.FIELD_OPS_INVOICE_GEN)` (the
   existing, previously-unwired permission already named for this exact
   capability, granted only to `tenant_owner`). `provider_record_payment`,
   `staff_create_invoice`, `staff_add_invoice_item` now require
   `require_staff_or_above_mutation` (tenant_owner/staff/technician,
   minus read-only access_scope) — matching `FIELD_OPS_JOBS_CLOSE`'s
   documented staff/technician payment-recording capability. No new
   permission was created; both dependencies are pre-existing, reused
   from the platform's canonical guard toolkit (no parallel
   authorization system introduced).
2. **`tests/test_phase2f6_invoice_payment_provider_authorization.py`** —
   new, 39 tests covering persona enforcement, read-only access-scope
   denial, unknown-role fail-closed, tenant-ownership source-inspection
   regression guards, and module-verification tooling parity.
3. **`docs/workflow-rearchitecture/phase-02a-slice-02f/mutation-enforcement-matrix.csv`** —
   updated in place: this module's row and the running TOTAL row.
4. **17 documentation files** in this directory (see `approval-gate.md`
   for the closure statement).

## What did NOT change
No other production file was modified. `finance_hub.admin_router`,
`package_commerce.admin_router`, all six previously-closed tenant-facing
modules, `readonly@`, and migration 144 remain untouched.

## Findings documented but not fixed
- Whether `staff` should be granted `FIELD_OPS_INVOICE_GEN` (open product
  decision).
- No positive-amount validation on payment/invoice-item amounts
  (pre-existing, no in-file precedent to safely mirror).
- No per-job-assignment restriction for staff/technician (consistent with
  the existing `FIELD_OPS_JOBS_CLOSE` permission's own scope, not a new
  gap).
- Frontend "Issue" button not hidden from non-owner roles (backend is
  authoritative; a cosmetic follow-up, not a security gap).

## Outcome
Security posture: closed for the selected module (zero unverified
routes, all persona enforcement proven by direct test, cross-tenant
targeting confirmed rejected). Product-policy posture: intentionally
open (whether to extend invoice-issuing rights to staff remains a future
decision). Global tenant-mutation coverage moves from a confirmed 85/183
to 89/183. See `approval-gate.md` for the full status statement.
