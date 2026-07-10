# FINAL-L5-02 — Bug Fix Register

## BUG-L502-001: Duplicate service-setup-template router mount (7 duplicate operation IDs)
- **Severity**: Medium (API hygiene + likely runtime breakage of the superseded copy)
- **Evidence**: `app.openapi()` reports 7 duplicate operation IDs; both `app.engines.admin_catalog.service_setup_template_router` (`/v1/admin/service-setup/templates`) and `app.engines.service_setup.templates_router` (`/v1/admin/service-setup-templates`) are mounted. FastAPI emits `UserWarning: Duplicate Operation ID` at startup.
- **Root cause**: Two parallel service-setup-template implementations exist (Sprint 34F migration-058 schema vs P0-Enterprise migration-097 schema). The 097 version is canonical (matches the live DB). This is the router-level counterpart of the 058/097 migration conflict.
- **Fix**: **Not applied this sprint** — removing the Sprint 34F mount requires confirming no frontend calls the `/v1/admin/service-setup/templates` prefix (a consumer audit). Deferred to avoid breaking a possible active consumer.
- **Status**: **DOCUMENTED, deferred** — in the deprecated-API register; needs a consumer audit before removal.

## BUG-L502-002 (carried, now FIXED-LIVE): Admin-tenant RBAC — customer can read admin data
- **Severity**: Critical
- Fixed in FINAL-L5-01B (17 GET routes → `require_super_admin`), **and this sprint confirmed the fix is LIVE** — `customer`/`technician`/`tenant_owner` all get 403 on `GET /v1/admin/tenants` against the running server (closing FINAL-L5-01B's live-verification gap).
- **Regression coverage**: 21/21 tests passing.
- **Status**: **FIXED + live-verified + regression-covered.**

## BUG-L502-003 (carried, FIXED): service_setup_templates migration conflict
- Fixed in FINAL-L5-01B-PLUS (DROP IF EXISTS guards in migration 097). Empty-DB replay now reaches head. **Status: FIXED + verified.**

## BUG-L502-004 (carried, FIXED): Admin dashboard 404 in browser
- Diagnosed this session as a corrupted Turbopack dev cache (`Failed to restore task data`), not a code defect. Cleared `.next`; `/admin/dashboard` and `/admin/tenants` now return 200. **Status: FIXED (cache clear, no code change).**

## Not-a-bug items confirmed this sprint
- Source-of-truth: `tenant_wallets` is NOT used as the active credit source (matching engine reads `tenant_billing` + `is_bookable`) — confirmed, no fix needed.
- 6 unmounted routers: 4 intentionally disabled, 2 confirmed-dead — no fix needed (cleanup candidates).
