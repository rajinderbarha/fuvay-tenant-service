# ADMIN-TENANT-E2E-09B — RBAC Endpoint Inventory Report

Real router file (the "tenant_router.py" referred to by the prior sprint's finding) is
`app/engines/admin_catalog/tenant_router.py`. It contains 9 mutation endpoints (not 12 — 12
was the prior sprint's estimate; the real count, read in full, is 9), all previously gated only
by `require_permission(P.TENANT_UPDATE)` (a pure role check — `tenant_owner` role passes
regardless of `access_scope`):

| Method | Path | Old dependency | New dependency |
|---|---|---|---|
| POST | /v1/tenant/catalog/enable-service | require_permission(TENANT_UPDATE) | require_tenant_mutation_permission(TENANT_UPDATE) |
| PUT | /v1/tenant/catalog/enabled-services/{id} | same | same (fixed) |
| POST | /v1/tenant/catalog/disable-service | same | same (fixed) |
| PUT | /v1/tenant/catalog/enabled-services/{id}/types | same | same (fixed) |
| PUT | /v1/tenant/catalog/enabled-services/{id}/brands | same | same (fixed) |
| PUT | /v1/tenant/catalog/enabled-services/{id}/types/{type_id}/pricing | same | same (fixed) |
| PUT | /v1/tenant/catalog/enabled-services/{id}/brands/{brand_id}/pricing | same | same (fixed) |
| POST | /v1/tenant/catalog/enabled-services/{id}/publish | same | same (fixed) |
| POST | /v1/tenant/catalog/enabled-services/{id}/save-draft | same | same (fixed) |

One additional real mutation endpoint in scope (service coverage), found via
`grep -rln "require_tenant_owner" app/engines/`:

| Method | Path | Old dependency | New dependency |
|---|---|---|---|
| PUT | /v1/provider/service-areas/{area_id}/coverage | require_tenant_owner | require_tenant_mutation_permission(TENANT_SERVICE_AREA_SERVICE_UPDATE) |

No `PUT /v1/provider/business-profile` route exists anywhere in the current codebase
(`grep -rn "business-profile|business_profile" app/` returns no `@router` matches) — the
prior sprint's finding about a business-profile RBAC gap refers to a route that either never
shipped or was removed; there is nothing to fix for that specific instance in this sprint.

Root cause confirmed by reading `app/core/permissions.py` and `app/dependencies/auth.py`:
`access_scope` is a real DB column (`app/engines/auth/models.py:60`) used ONLY by the
super_admin/platform_users feature (`VALID_ACCESS_SCOPES = {global, operations, finance,
compliance, support, tenant_scoped, customer_support_limited}`), and was **never included in
the JWT claims** — `get_current_user()` never read it, so no endpoint anywhere could ever see
a caller's access_scope. Any user with `role=tenant_owner` (owner, manager, or read-only test
account) passed every `require_permission(P.TENANT_UPDATE)` check identically. This explains
why the prior sprint observed 422 (business validation) instead of 403 for the read-only user
— the endpoint had zero read/write distinction to enforce in the first place.

Confirmed live before the fix (git-equivalent: read the file, then curl'd the endpoint) that
the bug was real: `PUT .../pricing` as `tenant.readonly@serviceos.in` returned `422
TENANT_PRICE_BELOW_ADMIN_MIN` for an invalid payload, proving business validation ran before
any authorization check.
