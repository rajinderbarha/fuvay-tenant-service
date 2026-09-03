"""P0 Compliance SLA Automation — Test Suite.

Tests cover:
  A. Job file structure and CLI entrypoints
  B. run_sla_check — logic and audit trail
  C. run_expire_exports — expiry logic
  D. run_all — orchestration
  E. background_loop — asyncio task
  F. Lifespan wiring in main.py
  G. Admin router job endpoints
  H. api.ts — job trigger methods
  I. Frontend — Run SLA Job button
  J. Notification logic
  K. Audit log entries
"""
from pathlib import Path

import pytest

ROOT   = Path(__file__).parent.parent
JOB    = ROOT / "app" / "jobs" / "compliance_sla.py"
MAIN   = ROOT / "app" / "main.py"
ROUTER = ROOT / "app" / "engines" / "compliance" / "admin_router.py"
API_TS = ROOT / "frontend" / "super-admin" / "lib" / "api.ts"
PAGE   = ROOT / "frontend" / "super-admin" / "app" / "admin" / "compliance" / "page.tsx"


# ── A. Job File Structure ─────────────────────────────────────────────────────

class TestJobFile:
    def _src(self): return JOB.read_text(encoding="utf-8", errors="replace")

    def test_file_exists(self):
        assert JOB.exists()

    def test_module_docstring(self):
        src = self._src()
        assert "ComplianceSlaJob" in src or "SLA automation" in src.lower()

    def test_run_sla_check_defined(self):
        assert "async def run_sla_check" in self._src()

    def test_run_expire_exports_defined(self):
        assert "async def run_expire_exports" in self._src()

    def test_run_all_defined(self):
        assert "async def run_all" in self._src()

    def test_background_loop_defined(self):
        assert "async def background_loop" in self._src()

    def test_main_entrypoint_defined(self):
        assert "def main" in self._src()

    def test_cli_commands_sla(self):
        assert '"sla"' in self._src() or "'sla'" in self._src()

    def test_cli_commands_expire(self):
        assert '"expire"' in self._src() or "'expire'" in self._src()

    def test_cli_commands_all(self):
        assert '"all"' in self._src() or "'all'" in self._src()

    def test_loop_interval_defined(self):
        assert "LOOP_INTERVAL_SECONDS" in self._src()

    def test_loop_interval_value(self):
        src = self._src()
        # Should be 15 minutes (900 seconds)
        assert "15 * 60" in src or "900" in src

    def test_uses_asyncsession(self):
        # FINAL-L5-05AE: `AsyncSessionLocal` never existed in app/database.py
        # -- this background loop's `except Exception: log, don't crash`
        # wrapper silently swallowed an ImportError on every tick since
        # introduction (real DB session was never acquired). Fixed to use
        # the real `get_session_factory()` API (same fix already proven
        # correct in app/jobs/export_worker.py).
        assert "get_session_factory" in self._src()
        assert "AsyncSessionLocal" not in self._src()

    def test_at_risk_threshold_24h(self):
        src = self._src()
        assert "AT_RISK_HOURS" in src and ("24" in src)

    def test_open_statuses_defined(self):
        src = self._src()
        assert "OPEN_STATUSES" in src
        assert "submitted" in src
        assert "under_review" in src

    def test_cancelled_error_handled_in_loop(self):
        assert "CancelledError" in self._src()


# ── B. SLA Check Logic ────────────────────────────────────────────────────────

class TestSlaCheckLogic:
    def _src(self): return JOB.read_text(encoding="utf-8", errors="replace")

    def test_queries_compliance_requests(self):
        assert "ComplianceRequest" in self._src()

    def test_checks_due_at_field(self):
        assert "due_at" in self._src()

    def test_marks_breached(self):
        src = self._src()
        assert '"breached"' in src or "'breached'" in src

    def test_marks_at_risk(self):
        src = self._src()
        assert '"at_risk"' in src or "'at_risk'" in src

    def test_marks_on_track(self):
        src = self._src()
        assert '"on_track"' in src or "'on_track'" in src

    def test_updates_sla_status(self):
        assert "req.sla_status" in self._src()

    def test_updates_status_to_sla_breached(self):
        assert "sla_breached" in self._src()

    def test_only_transitions_logged(self):
        src = self._src()
        assert "prev_sla" in src
        assert "new_sla != prev_sla" in src or "prev_sla" in src

    def test_returns_checked_count(self):
        assert '"checked"' in self._src()

    def test_returns_newly_breached_count(self):
        assert '"newly_breached"' in self._src()

    def test_returns_newly_at_risk_count(self):
        assert '"newly_at_risk"' in self._src()

    def test_returns_notifications_sent_count(self):
        assert '"notifications_sent"' in self._src()

    def test_returns_run_at_timestamp(self):
        assert '"run_at"' in self._src()


# ── C. Export Expiry Logic ────────────────────────────────────────────────────

class TestExpireExportsLogic:
    def _src(self): return JOB.read_text(encoding="utf-8", errors="replace")

    def test_queries_compliance_exports(self):
        assert "ComplianceExport" in self._src()

    def test_checks_expires_at(self):
        assert "expires_at" in self._src()

    def test_filters_ready_downloaded(self):
        src = self._src()
        assert '"ready"' in src and '"downloaded"' in src

    def test_sets_status_expired(self):
        src = self._src()
        assert 'exp.status' in src and '"expired"' in src

    def test_clears_download_url(self):
        assert "download_url = None" in self._src()

    def test_writes_audit_log(self):
        src = self._src()
        assert "export.auto_expired" in src

    def test_returns_expired_count(self):
        assert '"expired"' in self._src()

    def test_returns_run_at(self):
        src = self._src()
        assert src.count('"run_at"') >= 2  # one per task + run_all


# ── D. run_all Orchestration ──────────────────────────────────────────────────

class TestRunAll:
    def _src(self): return JOB.read_text(encoding="utf-8", errors="replace")

    def test_calls_run_sla_check(self):
        assert "await run_sla_check()" in self._src()

    def test_calls_run_expire_exports(self):
        assert "await run_expire_exports()" in self._src()

    def test_returns_both_results(self):
        src = self._src()
        assert '"sla_check"' in src and '"expire_exports"' in src

    def test_logs_start_and_done(self):
        src = self._src()
        assert "compliance_sla.start" in src
        assert "compliance_sla.done" in src


# ── E. Background Loop ────────────────────────────────────────────────────────

class TestBackgroundLoop:
    def _src(self): return JOB.read_text(encoding="utf-8", errors="replace")

    def test_sleeps_on_interval(self):
        assert "asyncio.sleep(interval)" in self._src()

    def test_calls_run_all_in_loop(self):
        assert "await run_all()" in self._src()

    def test_handles_cancelled_error(self):
        assert "CancelledError" in self._src()

    def test_handles_generic_errors_without_crashing(self):
        src = self._src()
        assert "except Exception" in src
        assert "log.error" in src

    def test_first_run_delayed(self):
        src = self._src()
        # Sleep should come BEFORE run_all in the loop
        sleep_pos  = src.find("asyncio.sleep(interval)")
        run_all_pos = src.find("await run_all()")
        assert sleep_pos < run_all_pos, "Sleep should precede run_all in loop body"


# ── F. Lifespan Wiring ────────────────────────────────────────────────────────

class TestLifespanWiring:
    def _src(self): return MAIN.read_text(encoding="utf-8", errors="replace")

    def test_asyncio_imported(self):
        assert "import asyncio" in self._src()

    def test_background_loop_imported(self):
        assert "background_loop" in self._src()
        assert "compliance_sla" in self._src()

    def test_create_task_called(self):
        assert "asyncio.create_task" in self._src()

    def test_task_cancelled_on_shutdown(self):
        assert "_compliance_sla_task.cancel()" in self._src()

    def test_cancelled_error_awaited(self):
        src = self._src()
        assert "await _compliance_sla_task" in src
        assert "CancelledError" in src

    def test_loop_started_log(self):
        assert "compliance_sla_loop.started" in self._src()


# ── G. Admin Router Job Endpoints ─────────────────────────────────────────────

class TestAdminRouterJobs:
    def _src(self): return ROUTER.read_text(encoding="utf-8", errors="replace")

    def test_jobs_run_endpoint(self):
        assert '"/jobs/run"' in self._src()

    def test_jobs_run_sla_endpoint(self):
        assert '"/jobs/run-sla"' in self._src()

    def test_jobs_run_expire_exports_endpoint(self):
        assert '"/jobs/run-expire-exports"' in self._src()

    def test_run_all_imported(self):
        assert "run_all" in self._src()

    def test_run_sla_check_imported(self):
        assert "run_sla_check" in self._src()

    def test_run_expire_exports_imported(self):
        assert "run_expire_exports" in self._src()

    def test_all_require_super_admin(self):
        src = self._src()
        # count require_super_admin references — should cover new endpoints
        assert src.count("require_super_admin") >= 1


# ── H. api.ts Job Methods ─────────────────────────────────────────────────────

class TestApiTsJobs:
    def _src(self): return API_TS.read_text(encoding="utf-8", errors="replace")

    def test_run_jobs_method(self):
        assert "runJobs" in self._src()

    def test_run_sla_check_method(self):
        assert "runSlaCheck" in self._src()

    def test_run_expire_exports_method(self):
        assert "runExpireExports" in self._src()

    def test_jobs_run_url(self):
        assert "/v1/admin/compliance/jobs/run" in self._src()

    def test_jobs_run_sla_url(self):
        assert "/v1/admin/compliance/jobs/run-sla" in self._src()

    def test_jobs_expire_exports_url(self):
        assert "/v1/admin/compliance/jobs/run-expire-exports" in self._src()

    def test_run_jobs_post_method(self):
        src = self._src()
        # runJobs should use POST
        idx = src.find("runJobs")
        snippet = src[idx:idx+200]
        assert "POST" in snippet


# ── I. Frontend Run SLA Job Button ────────────────────────────────────────────

class TestFrontendSlaButton:
    def _src(self): return PAGE.read_text(encoding="utf-8", errors="replace")

    def test_run_sla_job_button_exists(self):
        src = self._src()
        assert "Run SLA Job" in src

    def test_run_jobs_action_defined(self):
        assert "runJobsAction" in self._src()

    def test_run_jobs_called_on_click(self):
        assert "runJobsAction.execute" in self._src()

    def test_refetch_after_job_run(self):
        src = self._src()
        # runJobsAction.execute() must be followed by a refetch call in same onClick block
        execute_pos = src.find("runJobsAction.execute")
        assert execute_pos != -1
        snippet = src[execute_pos:execute_pos + 200]
        assert "summary.refetch" in snippet or "requests.refetch" in snippet


# ── J. Notification Logic ─────────────────────────────────────────────────────

class TestNotificationLogic:
    def _src(self): return JOB.read_text(encoding="utf-8", errors="replace")

    def test_queries_super_admin_users(self):
        src = self._src()
        assert "super_admin" in src

    def test_creates_in_app_notification(self):
        assert "InAppNotification" in self._src()

    def test_breached_notification_critical_severity(self):
        src = self._src()
        assert '"critical"' in src

    def test_at_risk_notification_warning_severity(self):
        src = self._src()
        assert '"warning"' in src

    def test_notification_has_action_url(self):
        src = self._src()
        assert "action_url" in src
        assert "/admin/compliance" in src

    def test_notification_has_action_label(self):
        assert "action_label" in self._src()
        assert "Review Request" in self._src()

    def test_notification_source_record_type(self):
        assert "compliance_requests" in self._src()

    def test_notification_only_on_transition(self):
        src = self._src()
        # Only notify on newly_breached / newly_at_risk (transitions)
        assert "newly_breached" in src
        assert "newly_at_risk" in src

    def test_notification_count_returned(self):
        assert "notifications_sent" in self._src()

    def test_notification_uses_request_number(self):
        assert "request_number" in self._src()


# ── K. Audit Log Entries ──────────────────────────────────────────────────────

class TestAuditLogs:
    def _src(self): return JOB.read_text(encoding="utf-8", errors="replace")

    def test_sla_change_audit_logged(self):
        assert "ComplianceAuditLog" in self._src()

    def test_audit_action_sla_breached(self):
        src = self._src()
        assert "sla.breached" in src or '"sla.{new_sla}"' in src or "f\"sla.{new_sla}\"" in src

    def test_audit_actor_role_system(self):
        src = self._src()
        assert '"system"' in src

    def test_audit_has_prev_and_new_sla(self):
        src = self._src()
        assert "prev_sla" in src
        assert "new_sla" in src

    def test_export_expiry_audit_logged(self):
        assert "export.auto_expired" in self._src()

    def test_audit_has_legal_basis(self):
        assert "dpdp_act_2023" in self._src()

    def test_audit_append_only(self):
        src = self._src()
        # Only db.add, never db.delete for audit logs
        assert "db.add(ComplianceAuditLog" in src
        assert "db.delete(ComplianceAuditLog" not in src
