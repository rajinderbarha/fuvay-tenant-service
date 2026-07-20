# Selected Module Boundaries — Slice 2F-22 (package_commerce.tenant_router)

## In scope for Slice 2F-22
- `POST /v1/tenant/packages/{package_id}/purchase` (`tenant_purchase_package`)
  — the sole mutation route in `app.engines.package_commerce.tenant_router`.
- Upgrading its dependency from `require_tenant_owner` to
  `require_tenant_owner_mutation` (existing dependency, no new code).
- Resolving the `mark_paid` client-trust gap via an authorization/scope
  change (see `selected-next-module-security-plan.csv`) — NOT a new
  payment-gateway integration.
- Adding a duplicate-purchase / idempotency guard if the product decision
  permits (flagged, not mandated, this slice).
- Direct tests proving the fix (dependency swap + mark_paid handling).

## Explicitly out of scope for Slice 2F-22
- The 4 GET read routes in the same file (`/available`, `/purchases`,
  `/onboarding/package-summary`, `/security-deposit`) — confirmed
  non-mutating this slice; only touch if a defect is found DIRECTLY
  connected to the purchase route's fix.
- The admin-side package-activation path
  (`activate_tenant_package_assignment` and its owning module) — a
  distinct, already-scoped platform-admin capability.
- Any of the other 19 remaining routes / 8 other modules — each is a
  separate future slice per `non-selected-module-queue.csv`.
- Reopening compliance (`app.engines.compliance.provider_router`) —
  closed in 2F-20, domain-integrity gap (export worker) remains
  intentionally open per 2F-20's own scope, not touched here.
- Adding a payment gateway, Celery worker, or any new infrastructure.
- Any schema migration (`TenantPackageAssignment` schema unchanged).
- Frontend/mobile changes.
