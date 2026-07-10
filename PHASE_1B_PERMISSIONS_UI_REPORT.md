# Phase 1B — Permissions UI Report

## Backend

Same engine as Roles (`app/engines/roles_permissions/`). Permissions are
derived live from `app/core/permissions.py::class P` (335 constants),
classified by module/app-scope/risk-level via keyword heuristics, and
cross-referenced against `ROLE_PERMISSIONS` for real "assigned roles" data.

| Endpoint | Method | Status |
|---|---|---|
| `/v1/admin/permissions` | GET | ✅ 200, filters (`module`, `app_scope`, `risk_level`, `search`) all live-verified |
| `/v1/admin/permissions/grouped` | GET | ✅ 200, groups by module |
| `/v1/admin/permissions/{permission_key}` | GET | ✅ 200 for real keys, 404 for unknown |

All require `super_admin`.

## Frontend

New page `frontend/super-admin/app/admin/users/permissions/page.tsx`:
- 6 summary cards (Total/Admin/Tenant/Customer Permissions, High Risk,
  Unassigned).
- Filters: search, Module, App Scope, Risk Level — all wired to real query
  params.
- Table: Permission Key / Module / Scope / Risk / Assigned Roles / Status.
- Row click opens a detail drawer showing assigned roles as badges.
- Error state shows `request_id`.
- Sidebar nav item added ("Permissions", under Platform group).

`npx tsc --noEmit` → 0 errors (one bug found and fixed during this build:
`Input` component's `onChange` prop is `(value: string) => void`, not a raw
DOM event handler — my first draft passed `e => e.target.value` which
doesn't typecheck against that signature; fixed to `onChange={setSearch}`).

**Hard gate: Permissions UI exists and loads real backend permissions — PASS.**
