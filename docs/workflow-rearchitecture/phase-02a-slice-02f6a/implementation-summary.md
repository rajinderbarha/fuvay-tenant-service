# Slice 2F-6A Implementation Summary

## Scope
Close the two financial-integrity questions and one persona-policy
question left open by Slice 2F-6's conditional approval of
`app.engines.invoice_payment.provider_router`.

## What changed

### 1. On-site payment integrity (`payment_service.py`)
`record_onsite_payment` gained:
- An invoice-status precondition (`issued` or `payment_pending` only —
  previously none existed at all).
- Amount validation (`> 0` and `<= customer_payable_amount` — previously
  none existed at all, meaning negative payments could mark an invoice
  "paid," and unlimited overpayment was silently accepted).

Both use pre-existing, previously-unwired error codes
(`ERR_INVOICE_INVALID_STATUS`, `ERR_PAYMENT_AMOUNT_MISMATCH`) already
defined in `constants.py`.

### 2. Invoice item integrity (`invoice_service.py`)
`add_item` gained quantity (`> 0`) and unit-price (`>= 0`) validation —
previously none existed, meaning a negative quantity or price could
silently reduce an invoice's total as an undeclared, unbounded discount.
No distinct discount mechanism exists in this codebase, so negative
values are rejected outright rather than a discount system being
invented. Zero unit-price (a legitimate free line item) remains allowed.

### 3. Technician persona narrowing (`provider_router.py`, `permissions.py`)
Investigation found zero mobile/staff-app caller for
`provider_record_payment`/`staff_create_invoice`/`staff_add_invoice_item`
(tenant-portal web app only) — no product evidence supports technician
access to these 3 capabilities in this module, contrary to Slice 2F-6's
initial assumption-by-analogy to a *different* module's permission
grant. A new, small composed dependency,
`require_owner_or_office_staff_mutation` (admits
`{super_admin, tenant_owner, staff}`, excludes `technician`), was added
to `app/core/permissions.py` and applied to all 3 routes, replacing
`require_staff_or_above_mutation`. `provider_issue_invoice` remains
unchanged (tenant_owner-only via `FIELD_OPS_INVOICE_GEN`).

### 4. Error-handling consistency (`provider_router.py`)
`provider_issue_invoice`, `staff_create_invoice`, `staff_add_invoice_item`
previously had no `ValueError` → HTTP mapping at all (any domain
rejection, including the new validation added this slice, would have
leaked as a 500). Added the same mapping pattern already used by
`provider_record_payment` (MODULE-L5-02's own established convention).

### 5. Tooling (`inventory_mutation_routes.py`)
`guard_status()` extended to recognize
`require_owner_or_office_staff_mutation` as
`TENANT_MUTATION_ROLE_SCOPE_AWARE`.

### 6. Test suite
New: `tests/test_phase2f6a_invoice_payment_integrity.py` (29 tests —
payment amount/state integrity, invoice item integrity, cross-tenant
direct proof, technician-denial HTTP tests, module-verification parity).
Updated: `tests/test_phase2f6_invoice_payment_provider_authorization.py`
(technician role-set correction, docstring updated to reference this
slice's narrowing).

### 7. Regression-test honesty
Two pre-existing "living count" guardrail tests
(`test_phase2d_tenant_access_model.py`,
`test_phase2e_effective_permissions.py`) intentionally fail when new
files start using `require_tenant_mutation_permission` — updated to
reflect Slice 2F-6's already-approved addition of
`invoice_payment/provider_router.py` as a 4th user, per their own
"if this changed, update the count" docstrings.

## What did NOT change
Slice 2F-6's authorization posture (permission/role choices for
`provider_issue_invoice`) is unchanged. No previously-closed module
(`tenant_engine.router`, `provider_portal.router`,
`execution.home_service_router`, `home_service_assignment.*`,
`tenant_engine.portal_router`, `finance_hub.admin_router`,
`package_commerce.admin_router`) was modified. No permission was
granted. No new role was introduced. No frontend file was modified
(one cosmetic gap documented, not fixed).

## Outcome
`SECURITY_AND_INTEGRITY_CLOSED_PRODUCT_POLICY_BLOCKED` — see
`approval-gate.md`. Global tenant-mutation coverage (89/183) is
unchanged, since no route's protection status itself changed this
slice (only the specific role admitted by an already-protected route was
narrowed, and two previously-unenforced business-integrity checks were
added within already-protected routes).
