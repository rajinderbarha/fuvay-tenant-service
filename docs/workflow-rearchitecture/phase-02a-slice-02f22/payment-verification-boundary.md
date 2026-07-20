# Payment Verification Boundary — Slice 2F-22

## Headline finding

**`PAYMENT_VERIFICATION_NOT_IMPLEMENTED` — for the ServicePackage /
TenantPackageAssignment flow specifically.**

This must NOT be read as "the repository has no payment verification." It
does, and it is real. The accurate finding is narrower and more useful:

> Authoritative payment verification exists in this codebase and is correctly
> used elsewhere, but **no verifier is wired to a tenant-initiated
> ServicePackage purchase**.

Reporting a blanket "not implemented" would have been false, and would have
justified building payment infrastructure this slice explicitly forbids.

## Mechanisms capable of proving payment

| Mechanism | Location | Verification | Trust boundary | Reaches this route's model? |
|---|---|---|---|---|
| Razorpay payment signature | `app/integrations/razorpay_client.py::verify_payment_signature` | HMAC-SHA256 of `order_id\|payment_id` keyed with `RAZORPAY_KEY_SECRET`, `hmac.compare_digest` | cryptographic | **Yes — via `public_registration` signup only** |
| Razorpay webhook signature | same module, `verify_webhook_signature` | HMAC over raw body | cryptographic, server-to-server | No |
| Signup registration path | `public_registration/router.py:353` | calls `verify_payment_signature` **before** creating the assignment at ~line 448 | gateway-proven | **Yes** |
| Admin manual settlement | `package_commerce/admin_router.py::admin_purchase_package` | `P.PACKAGES_CREATE` permission | human attestation | **Yes** |
| Credit top-up confirm | `platform_commerce/router.py::confirm_purchase` | `verify_payment_signature` + idempotency on topup id | cryptographic | No — distinct model (`CreditPackage`/`CreditTopupOrder`) |
| Invoice settlement | `invoice_payment` engine | — | — | No — distinct model |

## The gap

The tenant-facing route `POST /v1/tenant/packages/{package_id}/purchase` has
**no initiate/confirm pair**. There is no order creation, no gateway
redirect, no payment intent, and no confirm endpoint that could verify a
signature for a `ServicePackage`. The route was the *only* one of three
`create_package_assignment` callers with no authority behind its paid state —
and it was the one exposed to the least trusted principal.

## Disposition applied (per mission)

Because no authoritative mechanism exists for this flow:

- The tenant purchase creates **only the unpaid/pending state the model
  already supports** (`pending_review`). No new state was invented.
- **No credits, quota, commission or entitlement activate.** All of those
  remain behind `activate_tenant_package_assignment`, which is reachable only
  from admin approval (`tenant_engine/admin_service.verify_tenant`).
- **No paid ledger entry is created.**
- **No payment record is fabricated.** No `paid_at`, no
  `payment_reference_id`.

## Why the two remaining paid callers are correct, not exceptions

Both were verified by direct source reading, not assumed:

- `public_registration` — `verify_payment_signature(...)` at line 353 gates
  the request; execution only reaches the assignment creation (~line 448) if
  the HMAC validated. Test
  `test_public_registration_verifies_signature_before_marking_paid` asserts
  the source ordering, so a future refactor that moves the assignment above
  the check will fail.
- `admin_router` — a human admin holding `P.PACKAGES_CREATE` recording an
  out-of-band payment. This is an accepted attestation authority, materially
  different from a tenant attesting for itself.

## Residual (documented, not fixed)

`verify_payment_signature` returns `True` when Razorpay is not configured
(`is_configured()` false), so dev/test environments work end to end. That is
a deliberate pre-existing design in `platform_commerce`'s domain, out of
scope here, and it does not affect this route — which never marks paid under
any configuration. Recorded in `known-limitations.md`.

## Future work (blocked by product policy, not by this slice)

Wiring a real initiate/confirm pair for `ServicePackage` purchases is the
natural closure of this gap. It requires payment-gateway product decisions
this slice is explicitly barred from making. See
`product-decisions-required.md`.
