# Mutation Scope Enforcement Report

All 18 Set A routes and 24 canonically-added Set B routes now carry a
mutation-capable access-scope guard (`require_mutation_access_scope`,
`require_staff_or_above_mutation`, or `require_tenant_mutation_permission`)
that rejects `TENANT_READONLY_ACCESS_SCOPES` callers before any handler
body executes. No route in this slice reused a plain read permission for
write behavior — every swap either reused an existing role-equivalent
guard (preserving the admitted role set) or added the scope-only guard
where no role restriction previously existed.

## Roles admitted, unchanged

- `require_staff_or_above_mutation` admits exactly the same 4 roles as
  the `require_technician` dependency it replaces (`super_admin`,
  `tenant_owner`, `staff`, `technician`) — confirmed by direct source
  comparison (`app/dependencies/auth.py`).
- `require_mutation_access_scope` adds no role restriction at all (used
  only where no role restriction previously existed) — confirmed for
  all 15 routes it was applied to.
- `require_tenant_mutation_permission(P.TENANT_UPDATE)` reuses the exact
  permission previously checked by the bare `require_permission(P.TENANT_UPDATE)`
  it replaces, for all 12 routes it was applied to.

No new role, alias, or permission was added this slice — the mission's
canonical 10-role list is unchanged.
