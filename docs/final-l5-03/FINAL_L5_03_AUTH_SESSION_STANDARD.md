# FINAL-L5-03 — Authentication and Session Standard

| Behavior | Admin | Tenant | Customer | Staff (tenant-portal `/staff/*`) |
|---|---|---|---|---|
| Login response handling | `authApi.login()` -> store `serviceos_admin_token`/`refresh` | `authApi.login()` -> store `serviceos_tenant_*` keys + role | `authApi.login()` (customer-app) | Same tenant-portal client, `serviceos_tenant_token` (staff shares the tenant-portal token namespace by design — technicians are tenant-scoped users) |
| Session persistence | `localStorage` | `localStorage` | `localStorage` | `localStorage` |
| Logout | `authApi.logout()` + clear 2 keys + redirect `/login` | `authApi.logout()` + clear keys + redirect `/login` | Customer-app equivalent | `authApi.logout()` in `StaffLayout.tsx`, clears 2 keys, redirect `/staff/login` (own login page, separate from tenant-owner `/login`) |
| Expired session handling | `apiFetch` 401 path: refresh-then-retry, else `clearSession()` (clears tokens, redirects to `/login`, meaningful "Session expired" error thrown) | Same | Simpler, no refresh flow | `useStaffContext()` re-verifies role live on every mount (established FINAL-L5-01D/01E), never trusts localStorage alone |
| Corrupt token handling | Live-tested in FINAL-L5-01E (tenant-portal staff flow): a corrupted token seeded into localStorage triggers a clean recovery to the sign-in prompt, not a crash — same `apiFetch` 401 path handles this uniformly since `decode_token()` failures on the backend also return 401 | | | Certified 5/5 in FINAL-L5-01E |
| Refresh flow | Yes, all 3 web apps except customer-app (see gap below) | Yes | **Gap**: no refresh-token flow found in customer-app's `lib/api/client.ts` — a customer's session simply expires and they must re-login; not fixed this sprint (would be new functionality, not a "cleanup") | Shares tenant-portal's flow |
| Device/session revocation | Yes — `authApi.getSessions()`/`deleteSession()`/admin `revokeAllSessions()` exist and are wired into real pages (Security/Sessions) | Same pattern (Staff Security section, `staff/[id]/page.tsx`) | Not found | Yes, via `/staff/security/sessions` |
| Cross-application route protection | `StaffLayout`/`TenantLayout`/`AdminLayout` each gate on their own auth check; no middleware.ts exists in any of the 3 apps (confirmed in FINAL-L5-01E for tenant-portal, re-confirmed this sprint for super-admin and customer-app) — purely client-side layout guards, backed by backend RBAC as the real authority | | | |
| Tenant context initialization | `TenantLayout` derives tenant ID from the JWT-backed session, not a hardcoded default (except the one documented admin-tool exception, see Tenant Context Report) | | | |
| Customer isolation | Backend-authoritative, extensively proven in FINAL-L5-02B (bidirectional isolation with real IDs) | | | |
| Staff tenant assignment | `service_jobs.assigned_staff_id`/JWT `tenant_id` claim — backend-derived, not client-settable | | | |

## Required behavior — verified
- Unauthenticated → 401/login: confirmed for all 3 apps.
- Authenticated but unauthorized → 403: confirmed for tenant-jobs/customer-booking cross-scope access in FINAL-L5-02B; re-spot-checked this sprint via the browser regression (no unauthorized data rendered).
- Expired session → clear session + meaningful message: confirmed (`"Session expired. Please sign in again."`).
- Corrupt session → safe logout: confirmed (FINAL-L5-01E, 5/5).
- No token in visible UI/error text/console: confirmed via this sprint's browser regression console-log capture (zero token-shaped strings in any captured console output or error body).

## What was found and fixed this sprint
The `MOCK_MODE` bypass in super-admin and tenant-portal login pages — a login-skipping code path gated by a public env var, disabled in this environment's `.env.local` but a real, live, reachable bypass in the shipped client bundle. Removed entirely (code + the now-dead `MOCK_MODE` export + the now-dead `mock.ts` fixture file).

## Result
No `NOT_READY_FINAL_L5_03_AUTH_SESSION_FAILED` — behavior is consistent across apps where it should be, and the one genuine inconsistency (customer-app lacking a refresh flow) is a scoped, honestly-documented gap rather than an unsafe or hidden one (the failure mode is "customer has to log in again," not a security hole).
