# Admin A3 — Permission-Aware UI Report

## Ticket's 12 example `admin.tenants.*` permissions
Checked against `app/core/permissions.py` and `admin_router.py`.

**Finding: none of the 12 fine-grained `admin.tenants.*`-style permission
constants are wired into the real, frontend-facing tenant admin router.**
Every mutation endpoint in `tenant_engine/admin_router.py` is gated by the
coarse `require_super_admin` dependency only.

A **separate, parallel, unused-by-frontend** router
(`app/engines/tenant_engine/router.py`, prefix `/v1/tenants`) does use
fine-grained permission constants (`TENANT_SUSPEND`, `TENANT_PLAN_MANAGE`,
`TENANT_360_READ`, `TENANT_HEALTH_READ`, `TENANT_BILLING_READ`,
`TENANT_DATA_EXPORT`, etc.) defined in `permissions.py`, but the frontend
never calls it.

## Risk assessment
`permissions.py` defines `"super_admin": [P.ALL]` (wildcard) at line
~496. This means the real admin test account
(`admin@serviceos.in`) already has every fine-grained permission that
would be required, so switching the real router to fine-grained gates
would not change behavior for the current test account — but it is a
non-trivial change across ~15 endpoints with real risk of subtle
regressions for any future non-super-admin admin role, and was out of
the time budget for this sprint.

## Frontend permission-awareness
UI action buttons (Suspend, Change Plan, etc.) are not conditionally
rendered based on permission checks — they render unconditionally for
any authenticated admin session, consistent with the backend's coarse
`require_super_admin` gate (no fine-grained permission ever reaches the
frontend to condition on).

## Verdict
**Gap confirmed, not fixed this sprint.** Documented as a real,
non-blocking (given current wildcard super_admin role) architectural gap
in Remaining Blockers. Recommend a dedicated future sprint to wire the
existing fine-grained permission infrastructure into the real router.
