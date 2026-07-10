# Phase 1B — Roles UI Report

## Backend

New engine `app/engines/roles_permissions/` (service.py + admin_router.py),
mounted at `/v1/admin/roles*`. ServiceOS RBAC is code-defined
(`app/core/permissions.py::ROLE_PERMISSIONS`), not a DB table — this engine
does **not** introduce a parallel roles table; it exposes the real,
authoritative code data as read endpoints, enriched with live `users` table
counts.

| Endpoint | Method | Status |
|---|---|---|
| `/v1/admin/roles` | GET | ✅ 200, live-verified |
| `/v1/admin/roles/{role_id}` | GET | ✅ 200 for implemented roles, 404 for genuinely unknown ones |
| `/v1/admin/roles` | POST | 501 `NOT_IMPLEMENTED` — honest, roles aren't DB-editable |
| `/v1/admin/roles/{role_id}` | PUT | 501 `NOT_IMPLEMENTED` |
| `/v1/admin/roles/{role_id}/enable` | POST | 501 `NOT_IMPLEMENTED` |
| `/v1/admin/roles/{role_id}/disable` | POST | 501 `NOT_IMPLEMENTED` |

All GET endpoints require `super_admin` (confirmed 403 for `tenant_owner`
token, live). All 10 ticket-required roles appear in `GET /v1/admin/roles`,
each flagged `is_implemented: true/false` — 4 are real
(`super_admin`, `tenant_owner`, `technician`, `customer`), 6 are documented
gaps (`platform_admin`, `finance_admin`, `operations_admin`,
`support_admin`, `compliance_officer`, `tenant_manager` — same finding
carried from Phase 1, not fabricated here).

Live-verified: `super_admin` role detail returns `permission_count: 335`
(all `P.*` constants, since `super_admin` has the `P.ALL` wildcard),
`assigned_users` lists real users from the `users` table.

## Frontend

New page `frontend/super-admin/app/admin/users/roles/page.tsx`:
- 6 summary cards (Total/System/Custom/Active Roles, Users Assigned,
  Permission Gaps) — all from real API data.
- Table: Role / Type / Scope / Users / Permissions / Status / Actions.
- Detail drawer: Overview, Permission Matrix (full list), Assigned Users.
- Not-implemented roles show a clear inline warning banner in the drawer
  rather than fabricated data.
- Error state shows `request_id` via `EmptyState` + `useApi`'s `requestId`.
- Sidebar nav item added ("Roles", under Platform group).

`npx tsc --noEmit` → 0 errors for this page.

**Hard gate: Roles UI exists and loads real backend roles — PASS.**
