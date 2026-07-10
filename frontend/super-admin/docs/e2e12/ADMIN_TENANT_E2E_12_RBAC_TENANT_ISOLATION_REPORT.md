# E2E-12 RBAC + Tenant Isolation Report

**Date:** 2026-07-10  
**Method:** Static analysis only

---

## Scope

Role-based access control and tenant isolation coverage.

---

## Backend Isolation (from Sprint 31)

The following scope services were implemented and tested (Sprint 31):

- `TenantScopeService` — all tenant-scoped queries filter by `tenant_id`
- `CustomerScopeService` — customer operations scoped to owning tenant
- `StaffScopeService` — staff operations scoped to tenant
- `require_customer` dependency — customer auth guard
- `require_technician` dependency — staff/technician auth guard
- Invoice tenant-scope P0 fix applied

Sprint 31 had 41 tests passing for scope isolation.

---

## Frontend Role Guards

### Admin Portal
- Admin routes protected by admin auth token (`serviceos_admin_token` in localStorage)
- Login page redirects to `/admin/dashboard` on success
- Session expiry / missing token shows login page

### Tenant Portal
- Tenant routes protected by `serviceos_tenant_token`
- Staff routes protected by `serviceos_staff_token`
- Change-password-required guard applied on login
- Force password change flow implemented (migration 053)

---

## Known P2 Gap (from E2E-10)

Frontend role guards for tenant job mutations are incomplete. Staff members assigned to a job can see some mutation actions that should be tenant-only. This is a P2 frontend guard issue — the backend correctly enforces role scope, but the frontend does not hide inaccessible actions.

---

## Status

**PASS (backend, static analysis)** — Tenant isolation enforced at backend. Frontend role guard completeness is a known P2 gap. Browser verification of IDOR edge cases not performed.
