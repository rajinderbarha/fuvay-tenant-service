# Same-Record Alternate Route Audit — Slice 2F-22

Every writer of `TenantPackageAssignment` was enumerated by grepping for
`create_package_assignment`, `activate_tenant_package_assignment`,
`reject_tenant_package_assignment`, and direct `.status =` writes.

## Writers of the same record

| Path | Persona | Payment authority | Price authority | Classification |
|---|---|---|---|---|
| `tenant_router.tenant_purchase_package` (SELECTED) | `tenant_owner` via `require_tenant_owner_mutation` | none — always unpaid | server | **PROTECTED (this slice)** |
| `admin_router.admin_purchase_package` | platform admin, `P.PACKAGES_CREATE` | `admin_attestation` (human) | server | `SAME_RECORD_DISTINCT_PERSONA` |
| `public_registration` signup flow | guest → new tenant | `gateway_signature_verified` (HMAC checked at line 353, before creation at ~448) | server | `ALTERNATE_PROTECTED` |
| `admin_service.verify_tenant` → `activate_tenant_package_assignment` | platform admin | inherits assignment state | server | `ALTERNATE_PROTECTED` (one-shot; see below) |
| `admin_service.reject_verification` → `reject_tenant_package_assignment` | platform admin | n/a — issues nothing | n/a | `ALTERNATE_PROTECTED` |

**No `WEAKER_SAME_RECORD_ROUTE` remains.** The tenant route was the weakest
path — the only one permitting an unverified party to declare payment — and
it is now the most constrained of the three creators.

## Distinct models explicitly ruled out

These handle payment/credit but do **not** touch
`ServicePackage`/`TenantPackageAssignment`, so they are `DISTINCT_MODEL` and
out of scope:

- `platform_commerce` wallet purchase initiate/confirm — operates on
  `CreditPackage` / `CreditTopupOrder` (finance_hub). Signature-verified and
  idempotent in its own right.
- `platform_commerce` deposit initiate/confirm/admin-adjust — `SecurityDeposit`.
- `invoice_payment` engine — invoices, not package assignments.
- `usage_credits` / `UsageCreditService` — usage ledger.
- `admin_router` security-deposit family — already blocked (410) by
  FINAL-L5-05U.

## Deprecated / disconnected

- `PackageCommerceService.purchase_package` and the
  `TenantPackagePurchase` / `tenant_package_purchases` table —
  **`DISCONNECTED`**. The table was never migrated; MODULE-L5-30 repointed
  both live callers away from it. It remains referenced only by legacy unit
  tests (`test_sprint5_packages.py`), which exercise the dead method
  directly and were unaffected by this slice. Not removed here — deletion is
  out of scope and would be a separate cleanup.

## The one-shot activation guard

`verify_tenant` raises `TENANT_VERIFICATION_INVALID_STATUS` unless the tenant
is in `("not_started", "pending", "changes_requested")`. This makes
activation — and therefore credit issuance — run at most once per tenant, and
is the guard that prevents the duplicate-pending TOCTOU race from becoming a
double-credit defect (`duplicate-idempotency-policy.md`).

## Tests
`TestLegitimateCallersPreserved` (4 tests), including a source-ordering
assertion that signature verification precedes the paid assignment in
`public_registration` — so a future refactor reordering them fails the suite.
