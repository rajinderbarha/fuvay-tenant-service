# FINAL-L5-02 — Backend Architecture Inventory

## Shape
- **Framework**: FastAPI, single ASGI app (`app/main.py`, lifespan-managed startup)
- **Domain engines**: 67 under `app/engines/*` (65 with a router, 58 with a service layer, 51 with models)
- **Router files**: 143 (137 mounted — see router mount report)
- **Endpoints**: 2,253 (see endpoint registry)
- **Migrations**: 124 (001→131), now proven runnable base→head (FINAL-L5-01B-PLUS)
- **Test files**: ~200, 8,936 collected tests

## Cross-cutting infrastructure (verified present)
| Concern | Location |
|---|---|
| App entry / lifespan | `app/main.py` (DB → Redis → EventBus → routers → compliance SLA loop) |
| Middleware | `app/middleware.py` (request_id, logging, CORS chain) |
| Authentication dep | `app/dependencies/auth.py` — `get_current_user` |
| Authorization deps | `require_super_admin`, `require_tenant_owner`, `require_staff_or_above`, `require_customer`, `require_technician` (+ `require_permission(P.*)` in tenant_engine) |
| DB sessions | `app/database.py` (`create_engine`, `get_session_factory`, async sessions) |
| Background jobs | `app/jobs/compliance_sla.py` (15-min loop) |
| Event bus | Redis pub/sub, `set_event_bus` |
| OpenAPI | auto-generated, 2,253 ops, 254 tags |

## Machine-readable
`backend-architecture-inventory.json` — per-engine router/service/models/schemas presence.

## Known issues surfaced this sprint
1. **Duplicate service-setup-template system** (2 engines, 2 routers, 2 migration schemas 058/097) — the 097/P0-Enterprise version is canonical; the Sprint 34F version is likely runtime-broken against the current schema. See endpoint registry + bug register.
2. **2 dead brand routers** (`app/engines/brands/*`) unmounted, superseded by `admin_catalog`.
3. **~190 tenant-scoped tables lack DB-level FK to `tenants`** (tracked in FINAL-L5-01B FK gap register) — application-layer isolation only.

## Result
Architecture is coherent and fully inventoried. The engine/router/service/model layering is consistent across the 67 engines. Known issues are duplication/cleanup items, not structural failures.
