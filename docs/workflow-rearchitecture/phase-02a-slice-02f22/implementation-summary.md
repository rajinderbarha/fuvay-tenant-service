# Implementation Summary — Slice 2F-22

## Module
`app.engines.package_commerce.tenant_router`
Selected mutation: `POST /v1/tenant/packages/{package_id}/purchase`

## The defect

The route accepted an **untyped `payload: dict`** body and read two fields
from it that a tenant has no authority to assert:

```python
create_package_assignment(
    tid, package_id,
    payment_reference=payload.get("payment_reference"),
    is_paid=bool(payload.get("mark_paid")),
)
```

A tenant could therefore POST `{"mark_paid": true, "payment_reference":
"pay_FAKE"}` and produce an assignment in status `paid_pending_approval`
with a `paid_at` timestamp and a fabricated transaction reference — without
any payment occurring.

Classification: **`CLIENT_SETTLEMENT_ATTESTATION_TRUSTED`**, correcting
2F-21's `CLIENT_AMOUNT_TRUSTED`. No monetary amount was ever client-trusted;
every financial value was already server-derived from `ServicePackage`. The
tenant could assert *that* payment happened, not *how much*.

### Why it mattered

The route issued no credits itself, which made it look benign. Two
compounding factors made it serious:

1. `activate_tenant_package_assignment` orders candidates by
   `paid_at DESC NULLS LAST` — a forged `paid_at` sorted **ahead** of honest
   selections. Activation grants wallet credits, storage quota and commission.
2. The admin approving the tenant sees `paid_pending_approval` and a
   plausible reference. The defect manufactured evidence for the human who
   authorizes the money-moving step.

Additionally the route used `require_tenant_owner`, so a **read-only** tenant
owner could commit a purchase.

## Changes made (4 files)

1. **`tenant_router.py`** — added `TenantPackagePurchaseRequest` (no fields,
   `extra="forbid"`), swapped `require_tenant_owner` →
   `require_tenant_owner_mutation`, and made the service call pass
   `is_paid=False`, `payment_reference=None`,
   `payment_authority="tenant_unpaid_request"` as literals.
2. **`service.py`** — `create_package_assignment` gained a `payment_authority`
   parameter. `is_paid=True` without `gateway_signature_verified` or
   `admin_attestation` raises `PAYMENT_AUTHORITY_REQUIRED`; an unpaid
   selection carrying a payment reference raises
   `PAYMENT_REFERENCE_WITHOUT_PAYMENT`. Both fire **before** any DB work.
3. **`admin_router.py`** — declares `payment_authority="admin_attestation"`.
4. **`public_registration/router.py`** — declares
   `payment_authority="gateway_signature_verified"` (its
   `verify_payment_signature` call at line 353 already gates the path).

No role, permission or migration was added. No frontend file was touched.

## What was already correct (verified, not assumed)

- Price, credits, deposit, quota, commission, validity — all server-derived.
- Tenant identity — JWT only; cross-tenant purchase unrepresentable.
- Package eligibility — active + not soft-deleted.
- No activation or credit issuance at purchase.
- Duplicate guard (`PACKAGE_ALREADY_PENDING`), pre-existing.
- Both alternate creators hold real authority — signature proof and admin
  permission respectively.

## Coverage
**206/226 → 207/226.** 19 unprotected across 8 modules. Every numeric recount
assertion repo-wide was located and updated — the step 2F-20 skipped.

## Tests
50 new deterministic tests, all passing. Directly-affected suites: 406
passed, 0 failed. Wider payment/package suites: 752 passed, 5 pre-existing
live-env failures with **byte-identical node IDs** to the pre-change
baseline.

## Final status
**`SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED_PRODUCT_POLICY_BLOCKED`** —
see `approval-gate.md`.
