"""MODULE-L5-02 — post-completion financial + review flow bug guards.

All proven live end-to-end on :8001 (invoice -> issue -> payment -> review) for
JOB-20260714-000001; these lock the regressions in.
"""
import inspect


def test_financial_events_migration_adds_updated_at():
    """Bug #16: financial_events was created (migration 041) without updated_at
    though FinancialEvent(ServiceOSBase) declares it — every financial-event
    write 500'd. Migration 137 backfills the column."""
    import os
    d = os.path.join(os.path.dirname(__file__), "..", "alembic", "versions")
    src = open(os.path.join(d, "137_financial_events_updated_at.py"), encoding="utf-8").read()
    assert "financial_events" in src and "updated_at" in src and 'down_revision = "136"' in src


def test_invalid_payment_mode_raises_correct_code():
    """Bug #18: invalid payment_mode raised ERR_INVOICE_ALREADY_ISSUED (wrong
    constant). Must raise ERR_INVALID_PAYMENT_MODE."""
    from app.engines.invoice_payment import payment_service
    src = inspect.getsource(payment_service.ServicePaymentService.record_onsite_payment)
    assert "ERR_INVALID_PAYMENT_MODE" in src
    assert "raise ValueError(ERR_INVOICE_ALREADY_ISSUED)" not in src


def test_record_payment_handler_maps_valueerror_to_4xx():
    """Bug #18: bare ValueErrors leaked as 500. Handler must map to 4xx."""
    from app.engines.invoice_payment import provider_router
    src = inspect.getsource(provider_router.provider_record_payment)
    assert "except ValueError" in src and "ServiceOSException" in src
    # Bug #17: must not touch the non-existent user.staff_member_id attribute raw
    assert "user.staff_member_id" not in src
    assert 'getattr(user, "staff_member_id"' in src


def test_submit_review_handler_maps_valueerror_to_4xx():
    """Bug #19: submit_review leaked domain ValueErrors (REVIEW_NOT_ELIGIBLE
    etc.) as 500. Handler must map to 4xx."""
    from app.engines.customer_reviews import customer_router
    src = inspect.getsource(customer_router.submit_review)
    assert "except ValueError" in src and "ServiceOSException" in src


def test_completed_and_invoiced_job_is_review_eligible():
    """Bug #20: issuing an invoice moves a completed job to invoice_issued, which
    was excluded — closing the review window on the normal billed flow."""
    from app.engines.customer_reviews.constants import ELIGIBLE_STATUSES, RECORD_TYPE_SERVICE_JOB
    s = ELIGIBLE_STATUSES[RECORD_TYPE_SERVICE_JOB]
    assert {"completed", "invoice_issued", "paid"} <= s


def test_no_router_uses_bare_user_staff_member_id():
    """Bug #17: UserContext has no staff_member_id; every raw access 500'd."""
    import os
    roots = ["app/engines/invoice_payment", "app/engines/quote_checklist",
             "app/engines/execution"]
    base = os.path.join(os.path.dirname(__file__), "..")
    offenders = []
    for root in roots:
        for dp, _, files in os.walk(os.path.join(base, root)):
            for f in files:
                if f.endswith(".py"):
                    p = os.path.join(dp, f)
                    src = open(p, encoding="utf-8").read()
                    # raw `user.staff_member_id` not guarded by getattr
                    for line in src.splitlines():
                        if "user.staff_member_id" in line and "getattr" not in line:
                            offenders.append(f"{root}/{f}: {line.strip()}")
    assert not offenders, offenders
