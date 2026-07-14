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
