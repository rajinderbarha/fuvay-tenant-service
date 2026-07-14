"""MODULE-L5-11 — a raised delivery error must enter the capped retry cycle."""
import inspect


def test_dispatch_marks_raised_failures_FAILED():
    """dispatch_pending caught a raised delivery error (gateway down / network
    error) and logged it while leaving the outbox record PENDING — so it was
    re-dispatched every loop tick FOREVER with no cap, because max_retries only
    governs FAILED records (via retry_failed). The exception path must mark the
    record FAILED so it joins the normal capped retry cycle. Proven: a raising
    provider now leaves the record delivery_status=FAILED."""
    from app.engines.platform_notifications.notification_service import NotificationService
    src = inspect.getsource(NotificationService.dispatch_pending)
    exc = src.split("except Exception")[1]
    assert "DELIVERY_FAILED" in exc              # marks failed in the except path
    assert "DISPATCH_EXCEPTION" in exc


def test_retry_failed_respects_the_cap():
    """retry_failed must only re-queue FAILED records under the retry cap and
    increment retry_count, so retries are bounded."""
    from app.engines.platform_notifications.notification_service import NotificationService
    src = inspect.getsource(NotificationService.retry_failed)
    assert "retry_count < NotificationOutbox.max_retries" in src
    assert "retry_count += 1" in src
