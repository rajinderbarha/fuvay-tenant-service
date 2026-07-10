# ADMIN-TENANT-E2E-09B — Backend RBAC Fix Report

## Real fix (code changes, not documentation)

1. **`app/engines/auth/service.py`** — `_issue_tokens` (login) and the refresh-token path both
   now include `"access_scope": getattr(user, "access_scope", None)` in the JWT `extra_claims`,
   so the caller's DB `access_scope` column travels in the access token for the first time.
2. **`app/dependencies/auth.py`** — `UserContext` gained an `access_scope: str | None = None`
   field; `get_current_user()` now populates it from `payload.get("access_scope")`.
3. **`app/core/permissions.py`** — new shared dependency factory
   `require_tenant_mutation_permission(permission)`:
   - Runs the existing `require_permission(permission)` role check first (unchanged behavior
     for Owner/Manager/super_admin — no regression).
   - Then denies (403, `PERMISSION_DENIED`, with `request_id`) any non-super_admin caller whose
     `access_scope` is in `TENANT_READONLY_ACCESS_SCOPES = {"customer_support_limited"}`.
   - This check happens entirely inside the FastAPI dependency, which FastAPI resolves before
     the endpoint body executes — so a read-only caller is rejected before any request-body
     parsing/business validation the handler performs.
4. **`app/engines/admin_catalog/tenant_router.py`** — all 9 mutation endpoints switched from
   `require_permission(P.TENANT_UPDATE)` to `require_tenant_mutation_permission(P.TENANT_UPDATE)`.
5. **`app/engines/provider_portal/router.py`** — `set_area_coverage` (service-area coverage
   mutation) switched from `require_tenant_owner` to
   `require_tenant_mutation_permission(P.TENANT_SERVICE_AREA_SERVICE_UPDATE)`.

One shared dependency factory is used everywhere (not copy-pasted per endpoint), per the
spec's preference.

## Live verification (after backend restart)

- Read-only user, **invalid** payload (`tenant_min_price=99999, tenant_max_price=-5`) on
  `PUT .../pricing` → **403 PERMISSION_DENIED** (not 422). Proves auth runs before validation.
- Read-only user, valid payload → **403** (same).
- Read-only user on `types`, `publish`, `save-draft` → **403** on all.
- Read-only user, cross-tenant coverage payload with garbage `service_id` → **403** (not 422).
- Unauthenticated → **401**.
- Owner, valid mutation → **200**, real DB write confirmed (see Owner/Manager Regression report).
- Manager (`access_scope=tenant_scoped`), valid mutation → **200**; invalid (below admin floor)
  → **422** (proves Manager passes auth and reaches real business validation, as intended).
- Read-only GET (read-only path) → **200** (reads remain unaffected).

## Scope note

Fix applied to the 9 admin_catalog/tenant_router.py endpoints (service setup / types / brands
/ pricing / publish / draft) + 1 service-coverage endpoint in provider_portal/router.py = 10
real mutation endpoints hardened. `provider_portal/router.py` and `tenant_engine/portal_router.py`
contain dozens of additional `require_tenant_owner`-gated endpoints (team-members, availability
rules, offerings, packages, etc.) that are **out of this sprint's strict scope** (not
service-setup/coverage/pricing) and were intentionally left untouched — flagged in Remaining
Blockers as a candidate for a dedicated future RBAC-hardening sprint, since they share the
identical `access_scope`-blind pattern.

No route returns 422 for a read-only caller anymore. Verdict is **not**
NOT_READY_TENANT_READONLY_RBAC_FAILED for the in-scope endpoints.
