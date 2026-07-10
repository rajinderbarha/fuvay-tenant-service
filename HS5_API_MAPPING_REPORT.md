# HS5 — API Mapping Report

## Real endpoints (confirmed via source this sprint)
| Ticket-suggested | Real |
|---|---|
| `GET/POST/PUT/DELETE .../service-areas` | Real, under `providerServiceAreasApi` (serviceability engine), confirmed working from an earlier sprint |
| `GET .../coverage-options`, `PUT .../service-areas/{id}/coverage` | Not independently re-verified this sprint (see Coverage Report) |
| `GET/PUT .../availability` | Real — `GET/POST/PUT/DELETE /v1/provider/availability[/{rule_id}]`, **fixed this sprint** (time-range validation added) |
| `POST/PUT/DELETE .../availability/exceptions` | **Does not exist** — no exceptions/holidays data model found in this codebase |
| `GET /v1/tenant/setup/checklist` | No dedicated endpoint — checklist computed client-side in `TenantLayout.tsx` |
| `GET /v1/tenant/home-services/readiness` | `GET /v1/provider/status` (fixed in HS4B) |
| `GET /v1/tenant/package/limits` | Real — `tenant_limits` table, `max_service_areas` field used by the area-limit check |

## No mock data
All service-area and availability data confirmed real, DB-backed.

## Verdict
API integration: **mostly real**, with 2 confirmed gaps (coverage-by-
area API not re-verified, exceptions/holidays API doesn't exist at
all) — documented, not fabricated.
