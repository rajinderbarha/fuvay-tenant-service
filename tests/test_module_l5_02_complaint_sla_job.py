"""MODULE-L5-02 bug #32 — the complaint SLA/escalation job that never existed."""
import inspect


def test_complaint_sla_job_exists_with_expected_tasks():
    """CustomerComplaint stamps tenant_first_response_due_at / ai_escalation_at /
    admin_escalation_at and sla_status=on_time at creation, and ComplaintService
    already implemented check_and_update_sla() and get_sla_overdue_complaints() —
    but NOTHING called either. There was no scheduler, so sla_status stayed
    'on_time' forever however long a complaint went unanswered and no escalation
    ever fired: the whole SLA engine was dead code.

    Proven live: 3 complaints backdated 80h read sla_status='on_time'; after the
    job they read sla_status='escalated' and status='under_admin_review'."""
    from app.jobs import complaint_sla
    for fn in ("run_sla_check", "run_escalations", "run_all", "background_loop", "main"):
        assert hasattr(complaint_sla, fn), fn
    # the job must actually drive the previously-orphaned service methods
    assert "check_and_update_sla" in inspect.getsource(complaint_sla.run_sla_check)
    assert "STATUS_UNDER_ADMIN_REVIEW" in inspect.getsource(complaint_sla.run_escalations)


def test_complaint_sla_loop_registered_in_lifespan():
    """The loop must be started (and cancelled) by the app lifespan, like the
    compliance SLA and export-worker loops."""
    import os
    src = open(os.path.join(os.path.dirname(__file__), "..", "app", "main.py"),
               encoding="utf-8").read()
    assert "from app.jobs.complaint_sla import background_loop" in src
    assert "_complaint_sla_task = asyncio.create_task" in src
    assert "_complaint_sla_task.cancel()" in src


def test_ai_settlement_auto_starts_when_the_provider_fails():
    """Business rule (supersedes the earlier "never auto-fire the AI" guard):
    AI settlement is NOT started by hand. It takes over automatically once the
    PROVIDER has failed to solve the complaint — they blew their response SLA, or
    the customer rejected the resolution they offered. The admin only sets the
    rule (enable/disable, the cap, the permitted remedies) on complaint_policies.

    Starting a session charges the provider the AI settlement fee, so the job
    honours the policy's enable/auto-start switches before doing so."""
    from app.jobs import complaint_sla
    assert hasattr(complaint_sla, "run_ai_auto_start")
    src = inspect.getsource(complaint_sla.run_ai_auto_start)
    assert "AISettlementService" in src and "start_session" in src
    # the provider-failure condition
    assert "STATUS_AWAITING_PROVIDER" in src and "provider_responded_at" in src
    assert "STATUS_UNDER_ADMIN_REVIEW" in src
    # the admin's rule is honoured, and a complaint only gets one AI session
    assert "resolve_rule" in src
    assert "auto_start_on_provider_failure" in src
    assert "AISettlementSession" in src  # skip if it already had its turn
    # and it is part of the scheduled run
    assert "ai_auto_start" in inspect.getsource(complaint_sla.run_all)
