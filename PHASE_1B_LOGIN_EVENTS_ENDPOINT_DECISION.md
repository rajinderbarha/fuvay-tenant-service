# Phase 1B — Login Events Endpoint Decision

## Decision: **Option C — Keep, documented as a convenience alias, not a gap-fix**

## 1. Existing Auth Audit coverage

`GET /v1/auth/audit-log` (pre-existing, `app/engines/auth/router.py`) is
wired to the frontend's "Auth Audit" tab on `/admin/audit-logs`
(`app/admin/audit-logs/page.tsx:97`, `TAB_CONFIG.auth.endpoint`). Live-verified
this sprint: returns real `login.success`/`login.failed` events with
`actor_id`, `ip_address`, `created_at`. **This endpoint already fully
satisfies the ticket's Module 8 requirement that "admin login" be
audited and visible.**

## 2. New endpoint purpose

`GET /v1/admin/audit-logs/login-events` (added in the earlier Phase 1
sprint) queries the raw `login_events` table directly, under the
`/admin/audit-logs` namespace rather than `/v1/auth/`. It was originally
believed to close a gap; verification in this same earlier sprint already
corrected that belief — the gap didn't exist.

## 3. Whether it remains

**Kept.** Reasons:
- It is harmless — read-only, `super_admin`-gated, no side effects.
- It offers a genuinely different query surface: `/v1/auth/audit-log` is
  scoped to auth-service-recorded events via `ComplianceAuditLog`-style
  records; `/v1/admin/audit-logs/login-events` reads the separate
  `login_events` table directly, which has slightly different columns
  (`email_attempted`, `device_id`, `failure_reason` as a distinct field)
  and lives under the more discoverable `/admin/audit-logs/*` URL family
  alongside the other audit endpoints.
- Removing already-shipped, tested, harmless API surface for the sake of
  tidiness is lower value than clearly documenting it (this file) so future
  engineers don't have to re-discover the redundancy themselves.

## 4. Swagger/OpenAPI status

Documented — `summary="Admin login/logout audit trail (login_events
table)"` with an inline docstring explaining the redundancy, visible in
`/docs`. Confirmed present in `openapi.json` under
`/v1/admin/audit-logs/login-events`.

## 5. Tests adjusted

`tests/test_phase1b_admin_setup_closure.py::test_login_events_endpoint_still_mounted`
confirms the endpoint remains mounted (regression guard against accidental
removal, given the decision to keep it).

## Not pursued: consolidating all 3 parallel audit systems

This remains the real, more valuable fix (`platform_audit_logs` vs the
platform_notifications engine-audit table vs `login_events`/
`/v1/auth/audit-log`) — flagged again in `PHASE_1B_REMAINING_BLOCKERS.md`,
out of scope for this closure sprint per its explicit "do not add unrelated
features" boundary.
