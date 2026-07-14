"""MODULE-L5-11 — the notification dispatch/retry worker must run in-process."""
import inspect
import os


def test_notifications_has_a_background_loop():
    """Notification delivery is inline on create; the dispatcher is the
    retry/catch-up net for records left PENDING by a transient failure. It was
    CLI-only — unlike the compliance-SLA, complaint-SLA and export-worker loops
    (all started in the lifespan) — so without external per-minute cron a
    transiently-failed notification was never retried. It must have an in-process
    loop like the others."""
    from app.jobs import notifications
    assert hasattr(notifications, "background_loop")
    src = inspect.getsource(notifications.background_loop)
    assert "dispatch_pending" in src and "retry_failed" in src
    assert "asyncio.CancelledError" in src   # cancels cleanly on shutdown


def test_notification_loop_registered_in_lifespan():
    src = open(os.path.join(os.path.dirname(__file__), "..", "app", "main.py"),
               encoding="utf-8").read()
    assert "from app.jobs.notifications import background_loop" in src
    assert "_notif_task = asyncio.create_task" in src
    assert "_notif_task.cancel()" in src     # cancelled on shutdown
