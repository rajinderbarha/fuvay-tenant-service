# FINAL-L5-01B — Bug Fix Register

## BUG-001: Customer-to-Admin RBAC vulnerability
- **Summary**: 17 GET endpoints under `/v1/admin/tenants*` used `Depends(get_current_user)` (auth only) instead of `Depends(require_super_admin)` (auth + role check), letting any authenticated user of any role read platform-wide tenant data.
- **Severity**: Critical (real data exposure — tenant billing/credit balance, owner info, audit logs)
- **Evidence**: Reproduced live — `customer1@serviceos.local` received `200` with real tenant data from `GET /v1/admin/tenants` and `GET /v1/admin/tenants/{tenant_id}`.
- **Root cause**: Docstring claimed role restriction; code never enforced it.
- **Fix**: Swapped dependency to `require_super_admin` on all 17 routes (`app/engines/tenant_engine/admin_router.py`).
- **Regression test**: `tests/test_final_l5_01b_admin_tenant_rbac.py`, 21 tests, all passing.
- **API retest**: In-process `TestClient`/`AsyncClient` confirmed 403 for customer/technician/tenant_owner/tenant_manager/tenant_readonly, 401 for anonymous, not-rejected for super_admin.
- **Browser retest**: Not performed (live-server verification limitation this sprint — see RBAC fix report).
- **Status**: **FIXED**, automated-regression-verified. Live-server re-verification recommended as a fast follow-up once the shared dev server is restarted outside this sandboxed session.

## BUG-002: Missing rule seed data (4 of 10 mission-listed domains)
- **Summary**: Reward Rules, Credit Threshold Rules, Provider Verification Rules, and standalone Notification Policy have no dedicated backing table in the current schema.
- **Severity**: Low (data-completeness gap, not a security or correctness bug)
- **Evidence**: `information_schema` search returned zero matches for `%reward%`, `%threshold%`, `%verification_rule%`, `%notification_polic%`.
- **Root cause**: These domains were never built as first-class schema objects in this codebase.
- **Fix**: **Not applied** — per non-negotiable rule "Do not fabricate configuration records that violate existing schemas," no new tables/columns were invented.
- **Regression test**: N/A (nothing to regress against).
- **Status**: **DOCUMENTED, NOT FIXED** — real gap, carried to remaining blockers, requires a schema-design decision outside this sprint's scope.

## BUG-003: Migration bootstrap privilege gap
- **Summary**: `CREATE EXTENSION IF NOT EXISTS vector` in the migration chain requires superuser privilege, which the normal `serviceos` app user correctly lacks.
- **Severity**: Medium (blocks fresh-environment provisioning, does not affect the already-migrated real database)
- **Evidence**: Reproduced live against a fresh throwaway database — `InsufficientPrivilegeError`.
- **Root cause**: Extension creation requires ownership/superuser rights not granted to the least-privilege app role.
- **Fix**: `scripts/bootstrap_database_final_l5_01b.py` — one-time, explicitly-invoked script using a separate superuser connection, never modifying the app user's privileges.
- **Regression test**: Re-run twice (idempotent by construction, `CREATE EXTENSION IF NOT EXISTS`).
- **API retest**: N/A (infrastructure-level fix).
- **Browser retest**: N/A.
- **Status**: **FIXED AND VERIFIED** via real reproduction against a fresh database.

## BUG-004: `service_setup_templates` duplicate table across two migrations
- **Summary**: Migrations 058 and 097 both issue `op.create_table(...)` for `service_setup_templates`, causing `DuplicateTableError` on a from-empty migration replay.
- **Severity**: Medium (blocks full empty-database replay; does not affect the already-migrated real database, which has already absorbed both migrations without conflict since the table existed by the time 097 ran historically — an ordering artifact only visible on a true from-empty replay)
- **Evidence**: Reproduced live during this sprint's empty-database replay attempt.
- **Root cause**: Migration-authoring oversight — 097 was likely intended to be an `ALTER TABLE` against 058's table, or should have targeted a differently-named table, but instead duplicates the `CREATE TABLE`.
- **Fix**: **Not applied this sprint** — per the non-negotiable rule "Never rewrite applied migrations without a formal corrective migration," patching migration 097 in-place was avoided since it may already be applied in other environments; a proper fix requires a dedicated corrective-migration review.
- **Status**: **DOCUMENTED, NOT FIXED** — real blocker for full empty-database replay, carried to remaining blockers.

## BUG-005: Mission's assumed canonical jobs route does not exist
- **Summary**: `/admin/home-services/service-jobs` does not exist anywhere in the mounted API.
- **Severity**: Low (documentation/planning accuracy issue, not a code defect)
- **Evidence**: `app.openapi()` full-path enumeration — zero matches.
- **Root cause**: The route was assumed by the mission document rather than verified against the actual codebase.
- **Fix**: Documented the real, working equivalent endpoints (`/v1/admin/final-records/jobs*`, `/v1/admin/service-job-assignments*`, `/v1/staff/service-jobs*`, `/v1/provider/service-jobs*`, `/v1/customer/my-activity/jobs/*`) — see jobs source-of-truth inventory and decision reports.
- **Status**: **RESOLVED BY DOCUMENTATION** — no code change needed, real endpoints already exist and cover every required role.

## BUG-006: Admin dashboard/tenants pages return 404 in live browser session
- **Summary**: After a real, successful login (200, correct redirect to `/admin/dashboard`), the destination page renders a Next.js 404.
- **Severity**: Unknown — not conclusively diagnosed this sprint.
- **Evidence**: Real Playwright screenshot, `docs/final-l5-01b/evidence/02-post-login.png`.
- **Root cause**: **Not conclusively determined.** Most likely candidate given this sprint's extensive live-server process-management difficulties: dev-server staleness/hot-reload inconsistency from repeated backend restarts during the RBAC investigation, rather than a genuine routing defect (the corresponding `app/admin/dashboard/page.tsx`/`app/admin/tenants/page.tsx` files do exist in the frontend source).
- **Fix**: **Not applied** — root cause not established, so no fix was attempted; a fix without a confirmed diagnosis would risk masking the real issue or introducing an unrelated change.
- **Status**: **OPEN, NOT DIAGNOSED** — flagged as the top follow-up item for a future session with a clean, non-sandboxed server environment.
