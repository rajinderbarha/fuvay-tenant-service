# Alternate Route Audit — Slice 2F-4

## Candidate: `app.engines.auth.router`'s `deactivate_staff` — REAL BYPASS FOUND AND CLOSED
Frontend caller audit (Workstream 10) revealed `frontend/tenant-portal/lib/api.ts`'s
`deactivateStaff()` calls `POST /v1/auth/staff/{userId}/deactivate`
(`app.engines.auth.router`), **not** this module's own
`POST /v1/tenant/staff/{staff_id}/deactivate`. Both routes are live,
mounted, and operate on the same `User` table:

| | `app.engines.auth.router` (frontend-canonical) | `tenant_engine.portal_router` (this module) |
|---|---|---|
| Guard | `require_permission(P.AUTH_STAFF_MANAGE)` (granular permission) | `require_tenant_owner_mutation` (role, this slice) |
| Service | `AuthService.deactivate_staff` | `AdminTenantService.deactivate_staff` |
| Session revocation (before this slice) | YES — DB + Redis (fixed Slice 2F-1) | **NO — missing entirely** |

This is a genuine, directly-connected, exploitable weaker alternate route:
any tenant_owner (not just the frontend's normal flow) could call
`POST /v1/tenant/staff/{id}/deactivate` directly and deactivate a staff
member **without revoking their sessions** — their existing JWT would
continue to authenticate until natural expiry, defeating the purpose of
deactivation. **Fixed**: `AdminTenantService.deactivate_staff` now performs
the identical DB + Redis session-revocation pattern proven in
`AuthService.deactivate_staff` (Slice 2F-1) and
`provider_portal`'s `deactivate_team_member` (Slice 2F-2). See
`selected-module-service-bypass-report.md` for the exact code change.

**Disposition: `BLOCKS_MODULE_CLOSURE` until fixed → `ALTERNATE_PROTECTED`
after the fix.** Both routes now perform equivalent session revocation;
neither is weaker than the other for this specific concern.

## Candidate: `tenant_engine.admin_router`
Exposes the same capabilities on the same `User` table via the same
`AdminTenantService`: `create_user`, `suspend_user`, `create_staff`,
`deactivate_staff` (confirmed via direct source grep — `svc.create_user`,
`svc.suspend_user`, `svc.create_staff`, `svc.deactivate_staff` all appear
in `tenant_engine/admin_router.py`).

**Guard comparison:**
- `tenant_engine.portal_router` (this module): `require_tenant_owner_mutation`
  (role `{tenant_owner, super_admin}` + access-scope check, new this slice).
- `tenant_engine.admin_router`: `require_super_admin` (platform-only,
  confirmed via direct source read of `create_user` — `Depends(require_super_admin)`).

**Disposition: PLATFORM_ONLY** — `require_super_admin` is a strictly
higher-trust gate than `require_tenant_owner_mutation` (only `super_admin`
passes it, and `super_admin` is already exempt from the access-scope check
in `require_tenant_owner_mutation` too). This is not a weaker alternate
route; it is the intentional platform-operations parallel, matching the
identical pattern already confirmed safe in Slice 2F-1/2F-1A
(`tenant_engine.router`'s own admin surface) and Slice 2F-2
(`provider_portal.admin_router`).

## Lock/unlock/session-revocation
No alternate route was found exposing `lock_user`/`unlock_user`/
`admin_revoke_all_sessions` outside this module and `AuthService` itself.
`app.engines.auth.platform_users_router` (19 endpoints,
`PLATFORM_ADMIN_ONLY`) was not confirmed to expose the identical
capability this slice — flagged as not independently verified, not
assumed either way (see `known-limitations.md`).

## Conclusion
One alternate route found, confirmed `PLATFORM_ONLY` and not a bypass — no
closure action required. This module's approval is not blocked by any
alternate-route finding.
