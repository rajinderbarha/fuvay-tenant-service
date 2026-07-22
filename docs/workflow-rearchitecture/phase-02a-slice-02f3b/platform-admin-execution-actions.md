# Platform-Admin Execution Actions — Workstream 8

## The 3 endpoints
`admin_force_close`, `admin_override_status`, `admin_void` — all in
`execution.home_service_router`, gated by
`require_permission(P.ADMIN_JOBS_FORCE_CLOSE / STATUS_OVERRIDE / VOID)`.

## Canonical permission and role
Confirmed via `app/core/permissions.py`: `P.ADMIN_JOBS_FORCE_CLOSE`,
`P.ADMIN_JOBS_STATUS_OVERRIDE`, `P.ADMIN_JOBS_VOID` are granted only to
`admin_operations` — one of the canonical, least-privilege platform admin
roles (per the `FINAL-L5-05L` comment in `permissions.py`), never granted
to `tenant_owner`, `staff`, or `technician`. This is a genuine, real
permission-gate, not merely a role-name check — confirmed to already exist
correctly, unchanged this slice.

## Why no access-scope guard was added
`access_scope` (`TENANT_READONLY_ACCESS_SCOPES` / read-only-support
personas) is a tenant-side concept — it describes a restriction on a
tenant-scoped user (e.g. a support agent operating within a specific
tenant's data). `admin_operations` is a platform-wide role with no tenant
membership at all; applying a tenant access-scope check to it would be a
category error, exactly as `require_tenant_mutation_permission` already
exempts `super_admin` for the same reason. These 3 endpoints correctly
remain `PLATFORM_ADMIN_ONLY` and untouched.

## Frontend exposure
Not independently re-verified this slice (no caller search was performed
specifically for these 3 endpoints) — assumed super-admin-app-only,
consistent with every other `/v1/admin/*` execution endpoint pattern seen
in prior slices (Slice 2F-1/2F-1A's tenant_engine admin endpoints, Slice
2F-2's provider_portal admin_router). Flagged as not independently
re-verified, not silently assumed as verified.

## Confirmation / audit behavior
Not independently re-verified this slice — out of the narrow
guard-composition scope (these 3 endpoints' guard was not changed).

## Test proof
`TestPlatformAdminActionsRetainAccess` (2 tests × 3 endpoints = 6 tests):
confirms `admin_operations` clears the auth layer for all 3, and confirms
`tenant_owner` is denied for all 3 (403). `TestPlatformAdminEndpointsUnaffected`
confirms via source inspection that none of the 3 gained
`require_staff_or_above_mutation` or `require_tenant_owner_mutation` — they
remain exactly as they were.
