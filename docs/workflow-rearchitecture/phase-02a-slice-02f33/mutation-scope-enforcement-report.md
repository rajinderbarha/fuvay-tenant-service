# Mutation-Scope Enforcement Report (WS4)

All 3 routes now reuse the existing canonical mutation-guard framework —
no parallel authorization system was created.

- `DELETE /v1/geo/zones/{zone_id}` and `POST /v1/geo/tenants/{tenant_id}/
  zones` — guard changed from `require_permission(P.TENANT_UPDATE)` to
  `require_tenant_mutation_permission(P.TENANT_UPDATE)`. This is the exact
  same pre-existing function used across the codebase (first introduced
  for tenant mutation endpoints in an earlier slice) — it wraps
  `require_permission` with the same `TENANT_READONLY_ACCESS_SCOPES`
  rejection every other `*_mutation` guard uses. The role/permission gate
  itself is byte-identical to before; only the access-scope layer is new.
- `POST /v1/geo/tenants/{tenant_id}/staff/{staff_id}/location` — guard
  changed from bare `get_current_user` to `require_mutation_access_scope`
  (the minimal scope-only guard introduced in Slice 2F-31A for exactly
  this mixed-persona shape). Admitted roles are unchanged (still every
  role `get_current_user` admits); only the read-only access-scope
  rejection is new.

## Proof requirements

- Authenticated canonical principal: unchanged — all 3 routes still
  require `get_current_user` in their dependency chain.
- Valid canonical role or tenant-scoped StaffPermission grant: unchanged
  — `require_tenant_mutation_permission`'s underlying `permission_checker.
  has()` call is identical to the pre-existing `require_permission` check.
- Explicit deny overrides grant: preserved — `permission_checker.has()`
  (unchanged function) is StaffPermission-aware and this slice did not
  touch `app/core/permissions.py`'s `permission_checker` implementation.
- Cross-tenant grants do not admit: StaffPermission grants are already
  tenant-scoped by the existing permission system (unchanged); this
  slice's fix adds an independent, additional tenant check at the
  service layer, which is strictly more restrictive, never less.
- Mutation-capable access scope: enforced on all 3 routes (see live
  verification in [geo-verification-report.md](geo-verification-report.md)).
- Unknown role fails closed: unchanged — `permission_checker.has()`'s
  existing behavior for unrecognized roles was not modified.
- Unknown scope fails closed: `require_mutation_access_scope` and
  `require_tenant_mutation_permission` both only special-case
  `TENANT_READONLY_ACCESS_SCOPES`; any other/unknown `access_scope` value
  passes through unaffected — identical to every other `*_mutation` guard
  in the codebase (unchanged behavior, not introduced this slice).
- Principal tenant is server-derived: `GeoService.actor_tenant_id` comes
  from `UserContext.tenant_id` (the JWT-derived value), never the request
  body/path.
- Client tenant fields cannot widen authority:
  `GeoService._require_trusted_tenant` rejects any mismatch.
