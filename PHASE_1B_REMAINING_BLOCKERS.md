# Phase 1B — Remaining Blockers

1. **No true interactive browser session was ever launched** — the single
   blocker preventing full `READY_ADMIN_SETUP_FRONTEND_BACKEND_CERTIFIED`.
   No browser automation tool is available in this environment. Steps 29-30
   of the manual smoke script (console errors, visual NaN/undefined check)
   remain unverified. **This is an environment limitation, not unaddressed
   work** — everything that could be verified without a browser was.

2. **Role taxonomy gap persists** — 6 of the ticket's 10 required roles
   (`platform_admin`, `finance_admin`, `operations_admin`, `support_admin`,
   `compliance_officer`, `tenant_manager`) still don't exist as real,
   assignable roles. The new Roles UI surfaces this honestly
   (`is_implemented: false`) rather than hiding it — implementing the full
   taxonomy remains out of scope (a feature addition, not a closure-sprint
   fix, per the "do not add unrelated features" rule).

3. **Navigation editor formally deferred** — see
   `PHASE_1B_NAVIGATION_GAP_DECISION.md`. A backlog ticket is recorded for a
   future sprint.

4. **Three parallel audit-log systems still not consolidated** —
   `platform_audit_logs`, the platform_notifications engine-audit table, and
   `login_events`/`/v1/auth/audit-log`. This sprint's login-events decision
   (`PHASE_1B_LOGIN_EVENTS_ENDPOINT_DECISION.md`) documents rather than
   fixes this fragmentation.

5. **Role/permission mutation endpoints are 501, not functional.**
   `POST/PUT /v1/admin/roles*` return `NOT_IMPLEMENTED` by design (roles are
   code-defined). If a future sprint wants true admin-editable custom roles,
   this requires a larger architecture change (a `roles`/`role_permissions`
   DB schema, migrating away from the current code-constant model) —
   explicitly not attempted here to avoid a half-finished RBAC rewrite.

6. **`allow_job_completion_when_usage_credit_insufficient` setting still
   doesn't exist** — carried forward from Phase 0, not in this sprint's
   scope (job completion is explicitly out of scope for Admin Setup).
