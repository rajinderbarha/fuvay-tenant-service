# Model and Table Lineage — Slice 2F-22

## Models actually reached by this route

### `ServicePackage` — `service_packages` (read only)
- PK `id`; unique `slug`.
- Price fields: `package_price`, `security_deposit_amount`,
  `included_credit_amount`, `bonus_credits`, `setup_fee_amount`,
  `renewal_price_amount` — all `Numeric(12,2)`.
- Entitlements: `storage_quota_gb`, `commission_rate`, `lead_credits`,
  `validity_days`, `billing_cycle`, `features` (JSONB).
- `currency` — `String(10)`, `NOT NULL DEFAULT 'INR'`.
- Status: `is_active`; soft delete via `deleted_at`.
- Constraints: `package_price >= 0`, `security_deposit_amount >= 0`,
  `included_credit_amount >= 0`.
- **No tenant key** — packages are global; no tenant-private variant exists.
- Mutation callers: admin package CRUD only. This route never writes it.

### `TenantPackageAssignment` — `tenant_package_assignments` (written)
- Tenant key `tenant_id`; package key `package_id`.
- Snapshot fields written at selection: `package_type`, `price_amount`,
  `security_deposit_amount`, `included_spendable_credits`, `lead_credits`,
  `validity_days`, `billing_cycle`.
- Status: `status`; payment: `paid_at`, `payment_reference_id`.
- Lifecycle dates: `selected_at`, `approved_at`, `activated_at`,
  `starts_at`, `expires_at`.
- Read consumers: `get_packages_status`, `get_package_assignment_summary`,
  `get_tenant_purchases`.
- Mutation callers: the three creators plus admin activate/reject
  (`package-purchase-alternate-route-audit.md`).

### `PackageAuditLog` — `package_audit_logs` (written)
- Written via `_pkg_audit("tenant.package_selected")` after flush.

## Models reached only at activation (NOT by this route)

- `TenantWallet` + wallet transaction ledger — via `credit_wallet`, with
  `idempotency_key`.
- Tenant limits (storage quota) and commission rate — via
  `_apply_storage_quota` / `_apply_commission_rate`.

## Models that DO NOT EXIST — reported, not assumed

The mission's model checklist names many candidates. Verified absent from
this flow:

`PackagePlan`, `PackagePrice`, `TenantSubscription`, `TenantPlan`,
`CreditLedger` (as a package concept), `PackageCredit`, `Entitlement`,
`ModuleEntitlement`, `StorageQuota` (as a distinct model — it is a column on
tenant limits), `PaymentIntent`, `PaymentTransaction`, `Coupon`, `Discount`,
`Tax record`.

There is no `Payment` or `Invoice` record in this path at all.

## Disconnected legacy

`TenantPackagePurchase` / `tenant_package_purchases` — **the table was never
migrated**. `PackageCommerceService.purchase_package` still writes to it and
would fail at runtime; MODULE-L5-30 repointed both live callers away. It
survives only in legacy unit tests that call the dead method directly.
Not removed — out of scope.
