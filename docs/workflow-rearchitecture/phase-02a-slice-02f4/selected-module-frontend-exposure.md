# Frontend Exposure Audit — Slice 2F-4

## Method
Grepped `frontend/tenant-portal/lib/api.ts` for every one of the 10
mutation path fragments and their camelCase function-name equivalents.

## Findings

| Endpoint | Frontend caller found | Notes |
|---|---|---|
| `PATCH /v1/tenant/profile` | **NO** (in this module) | `tenantSelfApi.updateProfile` instead calls `PUT /v1/tenants/{tid}` — `tenant_engine.router`'s own `update_tenant` (already `SECURITY_CLOSED`, Slice 2F-1). This module's `/v1/tenant/profile` appears unused by the current frontend. |
| `PATCH /v1/tenant/settings` | **NO** | No caller found; not independently traced to an alternate implementation this slice. |
| `POST /v1/tenant/users` | **NO** | No caller found. |
| `POST /v1/tenant/users/{id}/suspend` | **NO** | No caller found. |
| `POST /v1/tenant/staff` | **NO** | No caller found; `auth.router`'s `/staff/invite` (invitation-based onboarding) is a different mechanism, not a direct substitute — not confirmed as the same capability. |
| `POST /v1/tenant/staff/{id}/deactivate` | **NO** (via this path) | **Real finding**: frontend calls `POST /v1/auth/staff/{id}/deactivate` (`auth.router`) instead — see `selected-module-alternate-routes.md` for the session-revocation gap this revealed and closed. |
| `PATCH /v1/tenant/staff/{id}/photo` | **NO** | No caller found. |
| `POST /v1/tenant/staff/{id}/lock` | **YES** — `tenantPortalApi.lockStaff` (`frontend/tenant-portal/lib/api.ts:222`) | Matches this module's path exactly. |
| `POST /v1/tenant/staff/{id}/unlock` | **YES** — `unlockStaff` (line 225) | Matches. |
| `POST /v1/tenant/staff/{id}/sessions/revoke-all` | **YES** — `revokeStaffSessions` (line 228) | Matches. |

## Requirements checked
- Read-only users must not see active mutation controls: backend now
  correctly denies regardless of UI state (not independently re-verified
  for the frontend's own conditional rendering, since no frontend code was
  changed).
- Platform-only actions must not appear in tenant portal: not applicable
  (no platform-only endpoint in this module).
- Owner-only actions must not appear to unauthorized staff: backend
  enforces this at the guard layer (`require_tenant_owner_mutation`
  excludes staff/technician entirely).

## No frontend changes made
7 of 10 endpoints have no confirmed frontend caller (3 do: lock/unlock/
revoke-sessions). This was investigated
only to the extent of finding the real `auth.router` alternate for
`deactivate_staff` (closed) — the other 5 unconfirmed-caller endpoints
(`update_profile`, `update_settings`, `create_user`, `suspend_user`,
`create_staff`, `update_staff_photo`) were not further chased down to a
definitive "dead" or "used elsewhere" conclusion this slice (see
`known-limitations.md`) — no frontend code was changed regardless, since
backend security posture does not depend on whether a frontend caller
exists.
