import pytest
from unittest.mock import AsyncMock, patch
from starlette.requests import Request
from app.engines.vertical_catalog.service_setup_readiness import service_setup_readiness
from app.engines.vertical_catalog.setup_sequence import STEPS, prerequisite, mutation_step


def test_configured_draft_completes_without_later_coverage_and_hours():
    result = service_setup_readiness([("draft", {"errors": [
        {"code": "MISSING_SERVICE_AREA"}, {"code": "MISSING_BUSINESS_HOURS"}]} )])
    assert result["percentage"] == 100
    assert result["complete"] is True
    assert result["blocking_reasons"] == []


def test_every_enabled_service_must_be_configured_and_errors_are_actionable():
    result = service_setup_readiness([("one", {"errors": []}), ("two", {"errors": [
        {"code": "MISSING_TENANT_PRICE", "message": "Set a price."}]})])
    assert result["percentage"] == 50
    assert not result["complete"]
    assert result["blocking_reasons"][0]["tenant_service_id"] == "two"


def test_no_services_is_not_complete():
    assert service_setup_readiness([])["percentage"] == 0
    assert not service_setup_readiness([])["complete"]


@pytest.mark.parametrize("code", ["MISSING_CONSULTATION_FEE", "MISSING_REQUIRED_TYPE_SELECTION", "MISSING_PUBLISHED_WORKFLOW", "REQUIRED_SERVICE_OPTION_PRICE_MISSING"])
def test_service_requirements_are_not_bypassed(code):
    assert not service_setup_readiness([("one", {"errors": [{"code": code}]})])["complete"]


def test_all_step_prerequisites():
    for done in range(len(STEPS)):
        sections = [{"key": key, "status": "complete" if i < done else "not_started"} for i, (key, _) in enumerate(STEPS)]
        for target, (key, _) in enumerate(STEPS):
            blocker = prerequisite(sections, key)
            if target <= done:
                assert blocker is None
            else:
                assert blocker["key"] == STEPS[done][0]


@pytest.mark.parametrize("path,expected", [
    ("/v1/tenant/home-services/setup/documents/upload", "DOCUMENTS"),
    ("/v1/tenant/catalog/home-services/pricing-policy", "SERVICES_PRICING"),
    ("/v1/provider/offerings/enabled", "SERVICES_PRICING"),
    ("/v1/tenant/home-services/activation/funding/order", "TECHNICIAN_PLAN"),
    ("/v1/tenant/home-services/activation/credit-package/order", "TECHNICIAN_PLAN"),
    ("/v1/provider/team-members", "STAFF_TECHNICIANS"),
    ("/v1/tenant/service-areas", "COVERAGE_AVAILABILITY"),
    ("/v1/provider/booking-window", "COVERAGE_AVAILABILITY"),
    ("/v1/tenant/home-services/setup/finance/payment-methods", "FINANCE_READINESS"),
    ("/v1/tenant/home-services/setup/submit", "REVIEW_SUBMIT"),
])
def test_setup_mutation_families_are_guarded(path, expected):
    assert mutation_step(path, "POST") == expected
    assert mutation_step(path, "GET") is None


@pytest.mark.parametrize("path", ["/v1/tenant/home-services/activation/funding/confirm", "/v1/tenant/home-services/activation/webhook", "/v1/tenant/home-services/activation/funding/order_123/reconcile", "/v1/provider/team-members/activate"])
def test_settlement_and_invitation_are_not_setup_edits(path):
    assert mutation_step(path, "POST") is None


@pytest.mark.asyncio
async def test_non_setup_route_does_not_resolve_owner_auth():
    from app.dependencies.setup_sequence import enforce_setup_sequence
    request = Request({"type": "http", "path": "/v1/provider/team-members/activate", "method": "POST", "headers": []})
    with patch("app.dependencies.setup_sequence.get_current_user", new_callable=AsyncMock) as auth:
        await enforce_setup_sequence(request, db=AsyncMock())
    auth.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("status,blocked", [("draft_setup", True), ("changes_requested", True), ("active", False)])
async def test_backend_rejects_later_edit_but_allows_active_operations(status, blocked):
    from types import SimpleNamespace
    from unittest.mock import MagicMock
    import uuid
    from app.dependencies.setup_sequence import enforce_setup_sequence
    from app.exceptions import ServiceOSException
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = SimpleNamespace(status=status)
    db.execute.return_value = result
    user = SimpleNamespace(tenant_id=str(uuid.uuid4()), role="tenant_owner")
    request = Request({"type": "http", "path": "/v1/provider/availability", "method": "POST", "headers": []})
    with patch("app.dependencies.setup_sequence.get_current_user", AsyncMock(return_value=user)), \
         patch("app.engines.vertical_catalog.home_services_setup_service.get_setup_overview", AsyncMock(return_value={"sections": []})):
        if blocked:
            with pytest.raises(ServiceOSException) as exc:
                await enforce_setup_sequence(request, db=db)
            assert exc.value.error_code == "SETUP_PREVIOUS_STEP_INCOMPLETE"
        else:
            await enforce_setup_sequence(request, db=db)


@pytest.mark.asyncio
@pytest.mark.parametrize("publish_fails", [False, True])
async def test_submit_fully_publishes_services_before_admin_handoff(publish_fails):
    from types import SimpleNamespace
    from unittest.mock import MagicMock
    import uuid
    from app.engines.vertical_catalog.service import VerticalCatalogService
    from app.exceptions import ServiceOSException
    tid = uuid.uuid4()
    result = MagicMock()
    result.scalars.return_value.all.return_value = [SimpleNamespace(id=uuid.uuid4())]
    db = MagicMock(execute=AsyncMock(return_value=result), commit=AsyncMock())
    svc = VerticalCatalogService()
    svc.get_or_create_enrollment = AsyncMock(return_value={"id": str(uuid.uuid4()), "vertical_id": str(uuid.uuid4()), "status": "draft_setup"})
    svc.transition_enrollment = AsyncMock(return_value={"status": "submitted"})
    catalog = MagicMock(publish_service=AsyncMock())
    if publish_fails:
        catalog.publish_service.side_effect = ServiceOSException("SERVICE_SETUP_INCOMPLETE", "Missing coverage", status_code=422)
    with patch("app.engines.vertical_catalog.home_services_setup_service.get_setup_overview", AsyncMock(return_value={"sections": [{"key": "SERVICES_PRICING", "required": True, "status": "complete"}]})), \
         patch("app.engines.vertical_catalog.declarations.get_declaration_status", AsyncMock(return_value={"all_accepted": True})), \
         patch("app.engines.admin_catalog.tenant_service.TenantCatalogService", return_value=catalog):
        if publish_fails:
            with pytest.raises(ServiceOSException):
                await svc.submit_for_review(db, tid, "home_services")
            svc.transition_enrollment.assert_not_awaited()
            db.execute.assert_awaited_once()  # Read offerings only; no admin-queue write.
        else:
            assert (await svc.submit_for_review(db, tid, "home_services"))["status"] == "submitted"
            catalog.publish_service.assert_awaited_once()
            svc.transition_enrollment.assert_awaited_once()
            assert "verification_status='pending'" in str(db.execute.await_args.args[0])
        db.commit.assert_not_awaited()  # Request dependency commits or rolls back everything together.
