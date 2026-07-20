# Product Decisions Required — Workstream 9 equivalent (not resolved this slice)

None of these were resolved or acted on this slice, per the explicit
out-of-scope instructions ("do not grant PACKAGES_* permissions", "do not
grant credit, commission or finance permissions").

## 1. Credit-wallet adapter idempotency-key contract
`admin_topup_wallet`/`admin_adjust_wallet` generate a random idempotency
key when the client omits one, defeating retry-safe deduplication for
that call. See `credit-wallet-adapter-integrity.md` for full detail.
Options for a future slice:
- (a) Require the client to always supply a stable key (breaking change
  for any existing caller that omits it — though none were found live).
- (b) Define a business-meaningful stable key convention for manual
  adjustments (e.g., derived from a ticket/request reference the admin
  UI would need to start collecting) — requires new UI work.
- (c) Accept the current behavior as intentional for this low-traffic
  legacy path and only revisit if/when a frontend caller is built.

## 2. Should `PACKAGES_*` permissions ever be granted to `admin_finance`?
Package definitions and lifecycle are currently super_admin-only. If
finance admins are expected to manage pricing/package catalog
day-to-day, `PACKAGES_UPDATE` (price changes) is the most likely
candidate to consider granting — `PACKAGES_ARCHIVE`/`CREATE` are higher-
risk (structural changes) and probably should stay super_admin-only
longer.

## 3. Cross-pipeline commission reconciliation
Three independent code paths (`package_commerce.PackageCommerceService`,
`platform_commerce.CommerceService`, `invoice_payment.ServiceCommissionService`)
all write to the same `CommissionRecord` table keyed by `job_id`. See
`alternate-commerce-route-audit.md` for the specific risk: `platform_commerce`'s
`deduct_commission` treats "a record exists" as "already deducted,"
which would silently no-op if `package_commerce`'s two-step
`calculate_commission` had only created a `status="pending"` record for
that `job_id` first. Recommend a future slice either (a) unify on one
commission pipeline, or (b) have `platform_commerce.deduct_commission`
check `status == "deducted"` specifically rather than "record exists."
This fix lives in `platform_commerce.service`, not `package_commerce`,
and was correctly out of scope for this slice.

## 4. Audit-event gaps
`create/update/delete_package_feature`, `create/update/delete_package_limit`,
and `admin_calculate_commission` do not raise an audit event. See
`audit-notification-verification.md`. A future slice should decide the
event-name/payload convention and add the missing calls (mechanically
straightforward once the convention is decided, but the convention
choice itself is a small design decision, not made here).

## Recommendation (non-binding)
Lowest-risk first step, if the product team wants to reduce super_admin
operational load: none of the current gaps are urgent enough to require
immediate action, since none has a live exploitation path (all affected
routes have zero frontend callers except the standard package-CRUD
surface, which is correctly super_admin-gated already).
