# Phase 1 — Admin Setup Backend Report

All checks performed live against a running `uvicorn` instance and real
Postgres (not simulated), building on and re-confirming findings from the
earlier Phase 1 (Admin Setup Certification) sprint in this same session.

## Module 1 — Admin Auth / Login

| Check | Result |
|---|---|
| Super Admin login succeeds | ✅ `POST /v1/auth/login` → 200, role `super_admin` |
| Invalid credentials fail safely | ✅ generic `"Invalid email or password."` for both wrong-password and unknown-email paths |
| Login creates session/token | ✅ JWT access token returned, `GET /v1/auth/me` confirms identity |
| Logout invalidates session | ✅ `POST /v1/auth/logout` → 200 |
| Protected API rejects unauthenticated | ✅ 401 with `request_id` |
| Login event creates audit log | ✅ **login_events table**, now exposed via 2 paths: pre-existing `/v1/auth/audit-log` ("Auth Audit" tab) and this sprint's new `/v1/admin/audit-logs/login-events` |

## Module 2 — Admin Dashboard Shell

`GET /v1/admin/dashboard/executive-summary` (real path — ticket's assumed
`/v1/admin/dashboard/summary` returns 404) confirmed live on the clean Phase 0
baseline: all zero-state fields (`active_tenants.count: 0`,
`live_operations.total: 0`) return proper `0` integers, not `null`/`NaN`.
`GET /v1/admin/catalog/navigation/effective-menu` (real path) → 200.

## Module 3 — Roles & Permissions

Same finding as the earlier Phase 1 sprint: only `super_admin`,
`tenant_owner`, `staff`, `technician`, `customer`, `guest` exist as real
roles (`app/core/permissions.py`); the ticket's `platform_admin`,
`finance_admin`, `operations_admin`, `support_admin`, `compliance_officer`,
`tenant_manager` don't exist. `require_permission()` short-circuits `True`
for `super_admin`. `GET /v1/admin/roles` and `/v1/admin/permissions` (ticket's
assumed paths) both 404 — no dedicated roles/permissions list endpoints
exist; `GET /v1/admin/engines/permissions` (a different, real endpoint)
returns 200.

## Module 4 — Platform Users

`GET /v1/admin/platform-users` (ticket's exact assumed path) **returns 200**
— confirmed live, returns real user list with role/status/mfa fields.

## Module 5 — Platform Settings

All 11 baseline settings re-confirmed exactly correct (see Phase 0's
backend report for the full value table — unchanged). The value-type
validation bug found and fixed in the earlier Phase 1 sprint
(`set_platform_setting`) remains fixed; re-verified no regression.

## Module 6 — Navigation / Menu Governance

`GET /v1/admin/catalog/navigation/effective-menu` → 200. No duplicate
Brands/Pricing items (static-verified in `AdminLayout.tsx`, unchanged from
Phase 0/1).

## Module 7 — Engine Management

`GET /v1/admin/engines/summary` → 39 total, 0 disabled, 0 degraded.
13/14 ticket-named engines map to real `engine_id`s (no dedicated
`finance_usage_credit_engine` — same finding as before, functionality is
real, just not a distinct registry entry).

## Module 8 — Vertical Configuration

`GET /v1/admin/verticals` → Home Services `is_enabled: true`, confirmed live.

## Module 9 — Platform Audit Logs

`GET /v1/admin/audit-logs` works, filters by `action`/`actor_user_id`/
`engine_key` all confirmed live. **Fix this sprint**: added
`GET /v1/admin/audit-logs/login-events` exposing the previously-orphaned
`login_events` table directly under the audit-logs namespace (though it
turned out login events were already separately visible via the pre-existing
`/v1/auth/audit-log` endpoint — this sprint's addition is a convenience,
not a gap-fix, corrected in the bug-fix report).

## Module 10 — Error Handling / request_id

Live-verified all 4 status codes:
- 401 → `{"error_code":"UNAUTHORIZED", "request_id":"req_..."}`
- 403 → `{"error_code":"PERMISSION_DENIED", "request_id":"req_...", "context":{...}}`
- 404 → `{"error_code":"NOT_FOUND", "request_id":"req_..."}`
- 422 → `{"error_code":"VALIDATION_ERROR", "request_id":"req_..."}`

All 4 include `request_id`, `error_code`, and a human-readable `detail`. 500
was not deliberately triggered this sprint (no reproducible clean-baseline
500 was found — would require synthetic fault injection, out of scope).

## Module 11 — Swagger / OpenAPI

`GET /openapi.json` → 200, 1871 total paths. All 8 required endpoint groups
present with non-zero path counts: `/v1/auth/login` (2), `/v1/auth/logout`
(2), `/v1/auth/me` (2), `/v1/admin/settings` (24), `/v1/admin/engines` (41),
`/v1/admin/verticals` (7), `/v1/admin/audit-logs` (2 + new login-events),
`/v1/admin/catalog/navigation/effective-menu` (1). `GET /docs` → 200
(Swagger UI loads).

**All backend hard gates PASS.**
