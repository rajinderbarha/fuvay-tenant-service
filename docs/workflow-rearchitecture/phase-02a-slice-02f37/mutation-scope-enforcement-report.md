# Mutation Scope Enforcement Report

All 3 Set A routes and 16 canonically-added Set B routes now carry a
mutation-capable access-scope guard (`require_tenant_mutation_permission`
or `require_mutation_access_scope`) that rejects
`TENANT_READONLY_ACCESS_SCOPES` callers before any handler body executes.

## Read-permission-for-write defect found and fixed

`POST /v1/commerce/tenants/{tenant_id}/badges/recalculate` was guarded
by `require_permission(P.TENANT_HEALTH_READ)` — a READ permission
protecting a WRITE (badge recalculation persists `TenantBadge` rows).
Swapped to `require_tenant_mutation_permission(P.TENANT_UPDATE)`, the
established mutation permission used throughout this program for
generic tenant-scoped writes.

## Roles admitted, unchanged

- `require_tenant_mutation_permission` reuses each route's exact
  pre-existing permission (`TENANT_UPDATE`, `TENANT_BILLING_READ`,
  `TENANT_BILLING_MANAGE`) — same admitted role set as before.
- `require_mutation_access_scope` (compute_price, warranty claims,
  compliance requests) adds no role restriction — used only where none
  previously existed (mixed-persona routes).

No new role, alias, or permission was added this slice.
