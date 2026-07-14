"""MODULE-L5-02 — complaint flow + systemic ValueError->4xx bug guards."""
from app.exceptions import _domain_code_status


def test_complaint_eligibility_covers_invoiced_and_paid_jobs():
    """Bug #23: a completed job billed (invoice_issued) or settled (paid) must
    still be complaint-eligible."""
    from app.engines.complaints.constants import ELIGIBLE_STATUSES, RECORD_SERVICE_JOB
    assert {"completed", "invoice_issued", "paid"} <= ELIGIBLE_STATUSES[RECORD_SERVICE_JOB]


def test_domain_valueerror_maps_to_4xx():
    """Bug #24: bare ValueError(ERR_CODE) domain rejections must map to a 4xx,
    including the `CODE: detail` form; genuine python ValueErrors stay 500."""
    assert _domain_code_status("COMPLAINT_ACCESS_DENIED") == 403
    assert _domain_code_status("INVOICE_NOT_FOUND") == 404
    assert _domain_code_status("DUPLICATE_SERVICE_AREA") == 409
    assert _domain_code_status("COMPLAINT_INVALID_STATUS_TRANSITION: open -> resolution_proposed") == 422
    assert _domain_code_status("INVALID_PAYMENT_MODE") == 422
    # not domain codes -> None (fall through to 500)
    assert _domain_code_status("invalid literal for int() with base 10: 'x'") is None
    assert _domain_code_status("could not convert string to float") is None
    assert _domain_code_status("") is None


def test_value_error_handler_registered():
    import inspect
    from app import exceptions
    src = inspect.getsource(exceptions.register_exception_handlers)
    assert "@app.exception_handler(ValueError)" in src


def test_create_complaint_resolves_tenant_from_record():
    """Bug #25: the filing customer has no tenant, so the complaint was stored
    with tenant_id=NULL and the provider could never see it. create_complaint
    must resolve the owning tenant from the linked record."""
    import inspect
    from app.engines.complaints.complaint_service import ComplaintService
    src = inspect.getsource(ComplaintService.create_complaint)
    assert "_resolve_tenant_for_record" in src
    helper = inspect.getsource(ComplaintService._resolve_tenant_for_record)
    for t in ("service_jobs", "service_bookings", "service_invoices"):
        assert t in helper


def test_reschedule_request_validates_required_fields():
    """MODULE-L5-02 bug #26: request_reschedule read body["requested_date"] and
    body["requested_slot"] with raw dict access, so a missing field raised
    KeyError -> 500. It must validate to a clean 422. Proven live: missing
    fields -> 422 RESCHEDULE_FIELDS_REQUIRED (was 500)."""
    import inspect
    from app.engines.booking import router
    src = inspect.getsource(router.request_reschedule)
    assert "RESCHEDULE_FIELDS_REQUIRED" in src
    assert 'body.get(f)' in src or 'body.get(' in src


def test_proposed_resolution_can_be_accepted_or_rejected():
    """MODULE-L5-02 bug #27: after a resolution is proposed the customer responds
    via accept (-> resolved) or reject (-> under_admin_review), but neither was a
    permitted transition from resolution_proposed, so every proposed resolution
    stalled forever. Proven live: accept -> 200, complaint status 'resolved'."""
    from app.engines.complaints.constants import (
        ALLOWED_TRANSITIONS, STATUS_RESOLUTION_PROPOSED, STATUS_RESOLVED,
        STATUS_UNDER_ADMIN_REVIEW,
    )
    allowed = ALLOWED_TRANSITIONS[STATUS_RESOLUTION_PROPOSED]
    assert STATUS_RESOLVED in allowed
    assert STATUS_UNDER_ADMIN_REVIEW in allowed


def test_accepting_rework_resolution_creates_rework_request():
    """MODULE-L5-02 bug #28: create_rework_request_from_complaint had no caller
    anywhere, so a rework request could never exist and the entire rework
    sub-flow (admin approve/assign, provider schedule/start/complete) was
    unreachable. Accepting a rework-type resolution must now spawn the request
    and move the complaint to rework_approved. Proven live end-to-end: accept ->
    rework list 0->1 -> approve -> schedule -> start -> complete -> complaint
    resolved, rework completed."""
    import inspect
    from app.engines.complaints.complaint_service import ComplaintService
    src = inspect.getsource(ComplaintService.customer_accept_resolution)
    assert "create_rework_request_from_complaint" in src
    assert 'resolution_type' in src and "rework" in src
    from app.engines.complaints.constants import (
        ALLOWED_TRANSITIONS, STATUS_RESOLUTION_PROPOSED, STATUS_REWORK_APPROVED,
    )
    assert STATUS_REWORK_APPROVED in ALLOWED_TRANSITIONS[STATUS_RESOLUTION_PROPOSED]


def test_refund_path_advances_and_resolves_the_complaint():
    """MODULE-L5-02 bug #29: the customer refund endpoint is reachable from an
    open complaint, but refund_requested was not a permitted target from open (or
    awaiting_provider). refund_service SILENTLY SKIPS a complaint transition it
    is not allowed to make, so the complaint stayed 'open' while the refund ran
    all the way to approved/recorded — a refund could be fully paid out with the
    complaint still showing open, never resolving. And verify_refund never moved
    the complaint out of refund_recorded at all.

    Proven live: request -> refund_requested, approve -> refund_approved,
    record -> refund_recorded, verify -> resolved."""
    import inspect
    from app.engines.complaints.constants import (
        ALLOWED_TRANSITIONS, STATUS_OPEN, STATUS_AWAITING_PROVIDER,
        STATUS_REFUND_REQUESTED, STATUS_REFUND_RECORDED, STATUS_RESOLVED,
    )
    assert STATUS_REFUND_REQUESTED in ALLOWED_TRANSITIONS[STATUS_OPEN]
    assert STATUS_REFUND_REQUESTED in ALLOWED_TRANSITIONS[STATUS_AWAITING_PROVIDER]
    assert STATUS_RESOLVED in ALLOWED_TRANSITIONS[STATUS_REFUND_RECORDED]
    from app.engines.complaints.refund_service import RefundRequestService
    src = inspect.getsource(RefundRequestService.verify_refund)
    assert "STATUS_RESOLVED" in src and "get_complaint" in src
