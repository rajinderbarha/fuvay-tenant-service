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


def test_ai_escalation_is_not_auto_fired():
    """ai_escalation_at calls out to DeepSeek; firing it from an unattended loop
    would incur external API cost. It must stay an explicit admin action."""
    from app.jobs import complaint_sla
    src = inspect.getsource(complaint_sla)
    assert "start_session" not in src
    assert "AISettlementService" not in src
