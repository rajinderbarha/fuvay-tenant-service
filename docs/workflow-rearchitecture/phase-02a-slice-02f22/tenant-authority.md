# Tenant Authority — Slice 2F-22

## Verdict: server-derived, and already correct before this slice

Unlike the compliance module closed in 2F-20 (where tenant authority could be
`None`), this route's tenant handling was sound. Verified rather than assumed:

- Tenant identity comes from `_tenant_id(user)`, which reads `user.tenant_id`
  from the authenticated principal (JWT claim) and raises
  `TENANT_ACCESS_DENIED` when absent. It never reads the body.
- The request body accepts **no** `tenant_id` field — previously because the
  handler never looked for one, and now structurally, because the schema
  forbids all extra fields.
- The purchase tenant therefore cannot be overridden or substituted.
- `TenantPackageAssignment.tenant_id` is written from that server value only.
- Cross-tenant purchase is not merely rejected — it is **unrepresentable**
  through this route.
- The duplicate guard is scoped to `tenant_id AND package_id`, so it cannot
  leak the existence of another tenant's selection.
- Wallet/credit/entitlement effects (all at activation) key off the same
  server-derived `tenant_id`.

## Super-admin targeting

There is no tenant-targeting parameter. A `super_admin` calling this route
acts within whatever tenant context its own token carries; it cannot direct
the purchase at an arbitrary tenant. Platform-side targeting exists only on
`admin_router.admin_purchase_package`, which takes `tenant_id` as an explicit
path parameter under `P.PACKAGES_CREATE` — server-controlled and explicit, as
required.

## Tests
`TestTenantAuthority` (3 tests).
