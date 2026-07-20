# Mutation-Scope Enforcement Report (WS4)

All 11 routes reuse the existing canonical mutation-guard framework — no
parallel authorization system was created.

- `DELETE /v1/webhooks/endpoints/{endpoint_id}`, both `security` routes,
  and all 5 `documents`/`rag` `P.TENANT_UPDATE` routes — guard changed
  from `require_permission(P.TENANT_UPDATE)` to `require_tenant_mutation_
  permission(P.TENANT_UPDATE)`. Same pre-existing function used across
  the codebase since earlier slices; wraps `require_permission` with the
  same `TENANT_READONLY_ACCESS_SCOPES` rejection every other `*_mutation`
  guard uses. The role/permission gate itself is byte-identical to
  before; only the access-scope layer is new.
- `POST /v1/rag/query` — guard changed from bare `get_current_user` to
  `require_mutation_access_scope` (the minimal scope-only guard
  introduced in Slice 2F-31A, reused unchanged here for this route's
  mixed-persona shape).

## Proof requirements

- Authenticated canonical principal: unchanged on all 11 routes.
- Valid canonical role or tenant-scoped StaffPermission grant: unchanged
  — `require_tenant_mutation_permission`'s underlying `permission_
  checker.has()` call is identical to the pre-existing `require_
  permission` check for every route.
- Explicit deny overrides grant: preserved — `permission_checker.has()`
  was not modified by this slice.
- Cross-tenant grants do not admit: StaffPermission grants are already
  tenant-scoped by the existing permission system; this slice's fix adds
  an independent, additional tenant check at the service layer, strictly
  more restrictive, never less.
- Mutation-capable access scope: enforced on all 11 routes (live
  verification: `verify_2f35.py` condition R05).
- Unknown role/scope fail closed: unchanged behavior of the reused
  guards.
- Principal tenant is server-derived: `WebhookService.actor_tenant_id`,
  `RAGService.actor_tenant_id`, `SecurityService.actor_tenant_id`,
  `DocumentService.actor_tenant_id` all come from `UserContext.tenant_id`
  (the JWT-derived value), never the request body/path/query.
- Client tenant fields cannot widen authority: `_require_trusted_tenant`
  (webhook, security, document) and `_get_kb_trusted`/inline predicates
  (rag) all reject mismatch.
- Permission is appropriate for the mutation: `P.TENANT_UPDATE` was
  already the correct permission for all 10 `require_permission`-guarded
  routes (unchanged); `rag_query` correctly uses no role-restrictive
  permission (mixed persona, scope-only enforcement is the appropriate
  control).
- No read-only permission is used for a write: confirmed for all 11
  routes — none used a read permission.
