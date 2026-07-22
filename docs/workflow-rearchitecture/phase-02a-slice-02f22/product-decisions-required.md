# Product Decisions Required — Slice 2F-22

Questions this slice deliberately did NOT decide, each within an explicit
prohibition (no new payment gateway, no migration, no invented pricing,
renewal or stacking policy).

## 1. Payment gateway for `ServicePackage` purchases — PRIMARY
No initiate/confirm pair exists for tenant package purchases, so a tenant
cannot actually pay for a package through the product. Post-2F-22 a purchase
is an unpaid request awaiting admin approval, which is safe but means paid
self-service does not exist. Wiring the existing, working Razorpay
verification (already used by `public_registration` and `platform_commerce`)
to this flow is the natural closure. Requires product/commercial decisions
about checkout UX, order lifecycle and refunds.

## 2. Duplicate-pending concurrency (needs a migration)
The duplicate guard is SELECT-then-INSERT; concurrent identical requests can
create two `pending_review` rows. It cannot duplicate benefits (activation is
`LIMIT 1` and one-shot per tenant), so the impact is an orphan row. The
correct fix is a partial unique index on `(tenant_id, package_id)` filtered
by pending statuses — a migration, prohibited this slice.

## 3. Package eligibility controls that do not exist
None was invented. Each is a product decision:
- `is_purchasable` distinct from `is_active`
- tenant-private / tenant-restricted packages (no column exists)
- vertical/category purchase restriction (`vertical_type` exists but is not
  enforced)
- availability window (no start/end columns)
- admin-only/internal package flag

## 4. Renewal, upgrade, stacking and replacement
No such semantics exist in code. Current observed policy is one pending
selection per (tenant, package), with multiple distinct packages permitted.
Whether a tenant may renew, upgrade, or hold stacked packages is undecided.

## 5. Refund and reversal
`rejected` is terminal and issues nothing; there is no refund or reversal
path for an activated package. Policy undefined.

## 6. Should `staff` ever purchase?
Currently denied. No canonical permission distinguishes a staff member
authorised to commit the tenant financially. Adding one would be a new
permission — prohibited here.

## 7. Free-package fast path
A zero-price package still routes through admin approval before activation.
Whether `package_price == 0` should activate immediately is a product
decision; this slice deliberately did not add a bypass, since an automatic
activation path is exactly where payment-state assumptions become dangerous.

## 8. Razorpay dev-mode verification bypass
`verify_payment_signature` returns `True` when the gateway is not configured,
so unconfigured environments accept any signature. Pre-existing, deliberate,
in `platform_commerce`'s domain, and it does not affect this route (which
never marks paid). Whether production configuration is enforced at boot is a
platform decision.

## 9. Legacy dead code removal
`purchase_package` / `TenantPackagePurchase` / `tenant_package_purchases`
remain in the codebase though the table was never migrated. Removal is a
cleanup decision, out of scope here.
