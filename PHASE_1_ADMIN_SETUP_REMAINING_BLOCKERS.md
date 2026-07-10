# Phase 1 — Admin Setup Frontend + Backend Certification — Remaining Blockers

None of these are hard-gate failures per the ticket's own rules (which only
hard-stop on backend/frontend/integration failure or missing audit logs for
mutations — all of which pass). These carry forward for a future sprint.

1. **No live browser smoke was performed** — caps the final recommendation
   at `PARTIAL_READY_WITH_ADMIN_SETUP_BLOCKERS` per the ticket's explicit
   rule, same as Phase 0.

2. **No dedicated Roles or Permissions management UI exists.** Role
   assignment happens only via the Users page's role dropdown; there is no
   standalone `/admin/roles` or `/admin/permissions` CRUD page, and no
   backend `GET /v1/admin/roles` / `/v1/admin/permissions` list endpoints
   (both 404). This is the same finding carried forward from the earlier
   Phase 1 sprint, not yet resolved — it's a real feature gap, not a bug.

3. **Role taxonomy gap** — `platform_admin`/`finance_admin`/
   `operations_admin`/`support_admin`/`compliance_officer`/`tenant_manager`
   don't exist as real roles. Same finding as before.

4. **Three parallel audit-log systems exist** with no consolidation:
   `platform_audit_logs` (`app/core/audit.py`), the platform_notifications
   engine-audit table (`/v1/admin/audit-logs`), and the auth-specific
   `login_events`/`ComplianceAuditLog`-style system
   (`/v1/auth/audit-log`). This sprint added a 4th convenience path
   (`/v1/admin/audit-logs/login-events`) rather than reduce this — flagged
   honestly as adding to, not fixing, the fragmentation. A dedicated
   consolidation sprint should merge these into one canonical audit surface.

5. **No dedicated Navigation admin editor page** — the sidebar itself is the
   only UI surface for navigation; there's no `/admin/navigation` page to
   view/edit nav config directly (the ticket's assumed
   `PUT /v1/admin/navigation/{item_id}` and
   `POST /v1/admin/navigation/rebuild` endpoints were not found to exist).

6. **No dedicated `finance_usage_credit_engine` registry entry** — same
   finding as before, functionality is real, not exposed as its own engine.

7. **No forced 500-error reproduction** was performed to confirm the 500
   error envelope also includes `request_id` — only 401/403/404/422 were
   confirmed live. Given the consistent error-handling middleware pattern
   observed across all other status codes, this is a low-risk gap, but
   explicitly unverified.
