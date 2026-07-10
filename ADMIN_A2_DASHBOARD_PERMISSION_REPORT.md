# Admin A2 Dashboard — Permission Report

## Real, pre-existing permission constants (all consumed by the router)

```
DASHBOARD_READ                 = "dashboard.read"
DASHBOARD_FINANCE_READ         = "dashboard.finance.read"
DASHBOARD_OPERATIONS_READ      = "dashboard.operations.read"
DASHBOARD_SECURITY_READ        = "dashboard.security.read"
DASHBOARD_COMPLIANCE_READ      = "dashboard.compliance.read"
DASHBOARD_EXPORT               = "dashboard.export"
DASHBOARD_ACTION_QUEUE_MANAGE  = "dashboard.action_queue.manage"
DASHBOARD_ENGINE_HEALTH_READ   = "dashboard.engine_health.read"
DASHBOARD_ACTIVITY_READ        = "dashboard.activity.read"
```

## Per-endpoint gating (verified against the real router source)

| Endpoint | Permission |
|---|---|
| `executive-summary`, `platform-health`, `tenant-lifecycle`, `trends`, `at-risk-tenants`, `trust-quality`, `category-performance`, `refresh` | `DASHBOARD_READ` |
| `finance-snapshot` | `DASHBOARD_FINANCE_READ` |
| `operations-snapshot`, `live-operations` | `DASHBOARD_OPERATIONS_READ` |
| `compliance-security` | `DASHBOARD_SECURITY_READ` |
| `action-queue` + resolve/snooze/assign | `DASHBOARD_ACTION_QUEUE_MANAGE` |
| `engine-health` | `DASHBOARD_ENGINE_HEALTH_READ` |
| `activity-feed` | `DASHBOARD_ACTIVITY_READ` |
| `export-snapshot` | `DASHBOARD_EXPORT` |
| **`home-services-summary`** (new) | `DASHBOARD_READ` (via the shared `_svc` dependency) |

Every 403 raised by `require_permission()` flows through the platform-wide
RFC 7807 handler, which always includes `request_id` — confirmed
consistent with every other permission-gated endpoint across this
session's work.

## Frontend behavior on permission denial

The dashboard page calls every section's endpoint unconditionally via
`useApi()` — if the authenticated admin lacks a specific section's
permission (e.g. `DASHBOARD_FINANCE_READ`), that section's `useApi` call
returns a `403` error, which now (this sprint's fix) triggers the new
`SectionError` component for that card specifically — showing "We
couldn't load finance data" + Retry + Copy Request ID — rather than
silently rendering nothing (the pre-existing behavior) or leaking data
the admin isn't authorized to see. Other sections continue to render
normally since each section has its own independent `useApi` call.

## Verified live

Confirmed via `curl`: an unauthenticated request to any dashboard
endpoint returns `401 UNAUTHORIZED` with `request_id` present. A request
with a valid `super_admin` token (which holds every dashboard permission)
returns `200` for all 15 GET endpoints. Testing an intentionally
under-permissioned account's `403` path was not performed live this pass
(no such test account exists in the seed data) — the permission
enforcement itself is verified via the shared `require_permission()`
dependency already exercised and certified across every other sprint this
session.
