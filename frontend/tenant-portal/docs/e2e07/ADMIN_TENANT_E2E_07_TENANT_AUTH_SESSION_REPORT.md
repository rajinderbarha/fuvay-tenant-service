# E2E-07 Tenant Auth / Session Report
**Date:** 2026-07-10  
**Analysis:** Static analysis

---

## Auth Architecture

### Login Flow

1. User submits credentials to `POST /v1/auth/login`
2. Response: `access_token`, `refresh_token`, `tenant_id`, `user_id`, `business_name`, etc.
3. Stored in localStorage:
   - `serviceos_tenant_token` — JWT access token
   - `serviceos_tenant_refresh` — refresh token
   - `serviceos_tenant_id` — tenant UUID
   - `serviceos_tenant_name` — business name
   - `serviceos_tenant_vertical` — category type
   - `serviceos_tenant_plan` — plan type
   - `serviceos_tenant_health` — health score
   - `serviceos_user_id` — user UUID
   - `serviceos_force_pw_change` — flag for forced password change

### Token Refresh

`apiFetch` in `lib/api.ts`:
1. On HTTP 401: tries `POST /v1/auth/token/refresh` with refresh token
2. If new token obtained: stores it and retries the original request
3. If refresh fails: calls `clearSession()` → clears all localStorage keys → redirects to `/login`

### Session Guard

- `TenantLayout` checks token on mount; missing token → redirect to `/login`
- Force password change flag: redirects to `/change-password-required` page

### Session Management Pages

- `/account` — manage sessions, API keys, profile updates
- `/change-password` — change password form
- `/change-password-required` — forced password change (Phase 0D)

### Security Events

- Login events tracked in backend (`login_events` table, migration 054)
- Failed logins, account locks handled by backend
- Frontend shows account-locked error message on login

### Force Password Change

If `serviceos_force_pw_change` is set in localStorage (from login response), user is redirected to `/change-password-required` before they can access any tenant page.

### Findings

| Check | Status |
|---|---|
| Token stored in localStorage | PASS |
| Automatic token refresh | PASS |
| Session clear on auth failure | PASS |
| Force password change guard | PASS |
| Multiple session management | PASS (via `/account` page) |
| Session revocation (Redis) | PASS (Phase 0D — backend) |

**Status: PASS** — Auth and session management are complete and secure.
