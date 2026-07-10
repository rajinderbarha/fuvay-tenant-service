# ADMIN_TENANT_E2E_01 — Test Users / Roles Report

All passwords: `Password123!` (bcrypt, hashed via `app.engines.auth.utils.hash_password`, same
CryptContext used by the real auth engine — not a synthetic/fake hash).

| Role | Email | Status | tenant_id | role col | platform_role | access_scope |
|---|---|---|---|---|---|---|
| Super Admin | admin@serviceos.in | pre-existing, verified working | — | super_admin | super_admin | global |
| Super Admin (alt) | admin@serviceos.local | pre-existing | — | super_admin | — | — |
| Admin Operator | admin.operator@serviceos.in | **created this sprint** | — | super_admin | platform_admin | operations |
| Tenant Owner | provider@serviceos.in | pre-existing, verified working | 34b427a7-...(Demo AC Services) | tenant_owner | — | — |
| Tenant Owner (stale) | provider@serviceos.local | pre-existing, orphaned tenant_id (f002bb6b-...) — not used | f002bb6b-... | tenant_owner | — | — |
| Tenant Manager | tenant.manager@serviceos.in | **created this sprint** | 34b427a7-...(Demo AC Services) | tenant_owner | — | tenant_scoped |
| Tenant Read Only | tenant.readonly@serviceos.in | **created this sprint** | 34b427a7-...(Demo AC Services) | tenant_owner | — | customer_support_limited |
| Technician/Staff | staff@serviceos.in | pre-existing, verified working | 34b427a7-... | technician | — | — |
| Staff (alt) | developer04.fuvaytech@gmail.com | pre-existing | 34b427a7-... | staff | — | — |
| Customer One | customer@serviceos.in | pre-existing, verified working | — | customer | — | — |
| Customer Two | customer2@serviceos.in | pre-existing, verified working | — | customer | — | — |

## Creation method
No admin "create user" UI/endpoint was cleanly usable for arbitrary role+access_scope combos in time
for this sprint, so the 3 new users (Admin Operator, Tenant Manager, Tenant Read Only) were inserted
directly into `users` via psql, matching the exact column set/format of pre-existing rows (same bcrypt
hash format `$2b$12$...` produced by the real `hash_password()` function, same `is_active`/`is_verified`
flags as existing seed users). The `users` table has no CHECK constraint on `role` (verified via
`pg_get_constraintdef`), so this is schema-consistent with existing rows. `VALID_PLATFORM_ROLES` (from
`app/engines/auth/service.py`) includes `platform_admin`, used for Admin Operator. `access_scope` values
used (`tenant_scoped`, `customer_support_limited`) are both in `VALID_ACCESS_SCOPES`.

## Browser login verified this sprint (minimum required set)
- Super Admin (admin@serviceos.in) — PASS (Part 6)
- Tenant Owner (provider@serviceos.in) — PASS (Part 7)
- Tenant Read Only (tenant.readonly@serviceos.in) — PASS (Part 8, login only; no distinct read-only UI)

## API login verified for all 7 users listed above with `Password123!`, via real `POST /v1/auth/login`.

## Gap
No dedicated "Admin Operator" or "Tenant Manager"/"Tenant Read Only" UI role distinction exists in
either frontend today — both frontends only branch behavior on the base `role` column
(`super_admin`/`tenant_owner`/etc.), not on `platform_role`/`access_scope`. This is a genuine, documented
gap for a future RBAC-focused sprint (see READONLY_PERMISSION_SMOKE_REPORT.md for the concrete backend
consequence).

## Result
PASS with one documented gap (no UI-level role branching yet — backend columns exist and are populated
correctly).
