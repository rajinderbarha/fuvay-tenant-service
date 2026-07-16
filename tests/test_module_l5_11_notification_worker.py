"""MODULE-L5-11 — the notification dispatch/retry worker must run in-process.

MODULE-L5-50 addendum: the original tests here only asserted the loop *exists*
and is *wired up* via source inspection -- they never actually executed
dispatch_pending()/retry_failed() against a real DB, so a broken import
(`from app.database import AsyncSessionLocal` -- that name has never existed;
the real API is `get_session_factory()`) went undetected. Confirmed live: the
background loop (started for real in app/main.py's lifespan) logged
`jobs.notifications.loop_error: cannot import name 'AsyncSessionLocal'` every
single minute since MODULE-L5-11 was written -- the retry/catch-up net this
whole module exists for has never worked. Fixed by switching to
get_session_factory(), the same pattern app/jobs/complaint_sla.py already
uses correctly. Added TestLive below to close this blind spot for good.
"""
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


def test_no_broken_asyncsessionlocal_import():
    from app.jobs import notifications
    src = inspect.getsource(notifications)
    assert "AsyncSessionLocal" not in src
    assert "get_session_factory" in src


class TestLive:
    async def test_dispatch_pending_and_retry_failed_run_without_error(self):
        """Regression guard for the AsyncSessionLocal bug: initializes the real
        app database (as the app lifespan does) and calls the job functions
        directly, so a broken import/session-factory call fails the test
        instead of silently logging an error once a minute forever."""
        from app import database

        await database.init_db()
        try:
            from app.jobs.notifications import dispatch_pending, retry_failed
            result_d = await dispatch_pending(limit=5)
            result_r = await retry_failed(limit=5)
        finally:
            await database.close_db()

        assert "processed" in result_d
        assert "retried" in result_r
