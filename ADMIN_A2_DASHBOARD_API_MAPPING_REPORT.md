# Admin A2 Dashboard — API Mapping Report

## Ticket-suggested vs. real endpoints

| Ticket suggestion | Real endpoint used |
|---|---|
| `GET /v1/admin/dashboard/summary` | `GET /v1/admin/dashboard/executive-summary` (pre-existing, real) |
| `GET /v1/admin/dashboard/kpis` | Same executive-summary payload (`active_tenants`, `live_operations`, `pending_admin_actions`, `at_risk_tenants`, `critical_alerts`) + `GET /v1/admin/dashboard/platform-health` for the health score |
| `GET /v1/admin/dashboard/tenant-summary` | `GET /v1/admin/dashboard/tenant-lifecycle` (pre-existing, real) |
| `GET /v1/admin/dashboard/home-services-summary` | **New** — `GET /v1/admin/dashboard/home-services-summary`, added this sprint |
| `GET /v1/admin/dashboard/finance-summary` | `GET /v1/admin/dashboard/finance-snapshot` (pre-existing, real, reuses Sprint 28 `PlatformAnalyticsService`) |
| `GET /v1/admin/dashboard/operations-summary` | `GET /v1/admin/dashboard/operations-snapshot` + `GET /v1/admin/dashboard/live-operations` (pre-existing, real) |
| `GET /v1/admin/dashboard/trust-summary` | `GET /v1/admin/dashboard/trust-quality` (pre-existing, real) |
| `GET /v1/admin/dashboard/alerts` | `GET /v1/admin/dashboard/action-queue` (pre-existing, real) |
| `GET /v1/admin/dashboard/activity` | `GET /v1/admin/dashboard/activity-feed` (pre-existing, real, queries the unified `platform_audit_logs` table) |
| `GET /v1/admin/dashboard/engine-status` | `GET /v1/admin/dashboard/engine-health` (pre-existing, real, cross-references `app.engine_registry.registry` + a live `SELECT 1` DB check) |

## New this sprint

`GET /v1/admin/dashboard/home-services-summary` — real SQL against
`tenants` (filtered `vertical = 'home_services'`),
`provider_visibility_statuses` (bookability), `master_services` +
`service_categories` (catalog health, scoped by `vertical_type`),
`service_pricing_rules` (pricing rule health), `tenant_services`
(published services count), `tenant_service_areas` (service area
coverage health) — live-verified returning real data for the seeded Demo
AC Services tenant (1 provider, 15 catalog services, 6 active pricing
rules, 1 active service area).

## Full endpoint inventory (19 total, all pre-existing except the one above)

```
GET  /v1/admin/dashboard/executive-summary
GET  /v1/admin/dashboard/platform-health
GET  /v1/admin/dashboard/finance-snapshot
GET  /v1/admin/dashboard/tenant-lifecycle
GET  /v1/admin/dashboard/home-services-summary        ← new
GET  /v1/admin/dashboard/operations-snapshot
GET  /v1/admin/dashboard/live-operations
GET  /v1/admin/dashboard/trends
GET  /v1/admin/dashboard/action-queue
POST /v1/admin/dashboard/action-queue/{id}/resolve
POST /v1/admin/dashboard/action-queue/{id}/snooze
POST /v1/admin/dashboard/action-queue/{id}/assign
GET  /v1/admin/dashboard/engine-health
GET  /v1/admin/dashboard/at-risk-tenants
GET  /v1/admin/dashboard/compliance-security
GET  /v1/admin/dashboard/trust-quality
GET  /v1/admin/dashboard/activity-feed
GET  /v1/admin/dashboard/category-performance
POST /v1/admin/dashboard/refresh
POST /v1/admin/dashboard/export-snapshot
```

## Live-verified this sprint

All 15 GET endpoints returned `200` with real data for a real
authenticated `super_admin` token; unauthenticated requests correctly
return `401` with `request_id` present in the RFC 7807 error body.

## No mock runtime data

Every field the frontend reads is sourced from a real `useApi()` call
against the endpoints above — confirmed via the page's own header
comment ("PROVEN: every section reads from dashboardApi... no mock
data") and independently verified by reading `DashboardCommandCenterService`,
which issues real parameterized SQL against real tables throughout.
