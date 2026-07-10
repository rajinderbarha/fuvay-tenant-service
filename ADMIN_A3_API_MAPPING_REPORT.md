# Admin A3 Tenant Management — API Mapping Report

## Ticket-suggested vs. real endpoints (all under `/v1/admin/tenants`)

| Ticket suggestion | Real endpoint |
|---|---|
| `GET /v1/admin/tenants` | Real, pre-existing (`list_tenants`) — full search/filter/sort/pagination |
| `GET /v1/admin/tenants/{id}` | Real, pre-existing (`get_tenant`) |
| `GET /v1/admin/tenants/{id}/summary` | `GET /v1/admin/tenants/summary` (platform-wide) + `GET /v1/admin/tenants/{id}/overview` (per-tenant) |
| `GET /v1/admin/tenants/{id}/readiness` | Not a backend endpoint — the Provider Readiness checklist is computed **client-side** in the detail page from data already fetched via other calls (see Remaining Blockers) |
| `GET /v1/admin/tenants/{id}/setup` | `GET /v1/admin/tenants/{id}/settings` (partial) |
| `GET /v1/admin/tenants/{id}/jobs` | Real, but served by the Job/Field-Ops engine directly, not tenant_engine (frontend calls the jobs API filtered by `tenant_id`) |
| `GET /v1/admin/tenants/{id}/bookings` | Same pattern — served by the Booking engine, filtered by `tenant_id` |
| `GET /v1/admin/tenants/{id}/reviews` | Same pattern — served by the Review engine |
| `GET /v1/admin/tenants/{id}/finance` | Composed client-side from `GET /v1/admin/tenants/{id}/overview` + package/commerce endpoints |
| `GET /v1/admin/tenants/{id}/usage-credit-ledger` | Real — served by `platform_commerce`/finance engine, filtered by `tenant_id` |
| `GET /v1/admin/tenants/{id}/security-deposit` | Real — **`app/engines/package_commerce/admin_router.py`**, `/v1/admin/tenants/{tenant_id}/security-deposit` (deliberately relocated there per an explicit dedup comment in the codebase — confirmed live-verified 200) |
| `GET /v1/admin/tenants/{id}/health` | Real, but on a **different, unused-by-frontend** router: `GET /v1/tenants/{tenant_id}/health` (`tenant_engine/router.py`, backed by real `compute_health_score()` in `health.py`) — the admin frontend does not currently call this |
| `GET /v1/admin/tenants/{id}/media` | Real — served by the Media Vault engine, filtered by tenant |
| `GET /v1/admin/tenants/{id}/audit` | Real — `GET /v1/admin/tenants/{id}/audit-logs` (live-verified 200, real `TenantAuditLog` rows) |
| `POST /v1/admin/tenants/{id}/usage-credits/add` | Real — `POST /v1/admin/tenants/{id}/add-usage-credits` |
| `POST /v1/admin/tenants/{id}/change-plan` | Real, pre-existing, live-verified 200 |
| `POST /v1/admin/tenants/{id}/suspend` | Real, pre-existing |
| `POST /v1/admin/tenants/{id}/unsuspend` | Real — `POST /v1/admin/tenants/{id}/reactivate` |
| `POST /v1/admin/tenants/{id}/approve` | Real — `POST /v1/admin/tenants/{id}/verify` |
| `POST /v1/admin/tenants/{id}/reject` | Real — `POST /v1/admin/tenants/{id}/reject-verification` |
| `POST /v1/admin/tenants/{id}/security-deposit/adjust` | Real — `package_commerce/admin_router.py` |
| `POST /v1/admin/tenants/{id}/notes` | **New this sprint** — did not exist before; added with a real backend method reusing the existing audit-log table |

## Two parallel tenant routers exist — only one is wired to the frontend

`app/engines/tenant_engine/admin_router.py` (prefix `/v1/admin/tenants`) is
the one the super-admin frontend actually calls, backed by
`AdminTenantService` (`admin_service.py`). A second, more fully RBAC-wired
router (`app/engines/tenant_engine/router.py`, prefix `/v1/tenants`,
backed by `TenantService` in `service.py`) exposes a real `/360`
aggregation endpoint and the real health-score endpoint, but the frontend
never calls it — it uses its own composed set of calls instead
(equivalent data, different endpoint shape). Documented, not fixed this
sprint (see Remaining Blockers) — the actual Provider 360 page works
correctly either way since it composes the same underlying data via other
real calls.

## Bug found and fixed: tenant admin mutations invisible in platform-wide audit

`AdminTenantService._audit()` (used by every mutation above) only wrote
to `TenantAuditLog` — never `record_platform_audit()`. Fixed this sprint:
now writes to both. Live-verified: adding an admin note now appears in
`GET /v1/admin/dashboard/activity-feed` (the A2 Platform Command Center's
Recent Activity panel) within the same request cycle.

## No mock runtime data

Every endpoint above is real, DB-backed. Live-verified via curl: tenant
list, tenant detail, security deposit, audit logs, and a live
`change-plan` mutation all returned real data / 200 status.
