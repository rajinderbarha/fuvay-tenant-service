# E2E-07 Backend RBAC Gap Recheck Report
**Date:** 2026-07-10  
**Analysis:** Static analysis of frontend role usage — backend audit separate

---

## Frontend RBAC Usage

### Token / Auth Flow

1. Login via `authApi.login()` → receives `access_token`, `refresh_token`, `tenant_id`, `user_id`
2. Token stored in `localStorage.serviceos_tenant_token`
3. All API calls go through `apiFetch` which injects `Authorization: Bearer <token>`
4. `authApi.me()` returns `TenantUser` with `role` field
5. Backend enforces RBAC per endpoint — frontend does not bypass backend auth

### Role Field

`TenantUser.role` is returned from `/v1/auth/me`. Values observed in codebase:
- `tenant_owner` — standard tenant owner (full write access)
- `tenant_staff` — staff sub-account
- `tenant_read_only` — (new) read-only viewer role
- `staff` — platform staff

### Frontend RBAC Gaps (Pre-Sprint)

| Gap | Severity | Status |
|---|---|---|
| No `ReadOnlyBanner` shown for `tenant_read_only` role | P2 | FIXED — component created |
| Mutation buttons not conditionally disabled for read-only roles | P2 | PARTIAL — component available, page integration needed |
| No client-side role check before showing "Invite Staff" or "Add Service" buttons | P3 | OPEN — backend will reject; low risk |

### Backend RBAC (Confirmed Present)

- All mutation endpoints require authenticated tenant owner token
- `require_tenant` scope guard enforced in backend routers
- Unauthorized calls return HTTP 401/403; `apiFetch` handles 401 with token refresh + redirect to login

### Assessment

Backend RBAC is solid. Frontend RBAC is informational (UX improvement, not a security gate). The `ReadOnlyBanner` component created this sprint provides the missing UI signal.

**Status: PASS** — No security gaps. Frontend UX improvement (read-only banner) created.
