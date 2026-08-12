"""Regression coverage for the tenant -> Admin Home Services handoff."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

import pytest

from app.engines.vertical_catalog.service import VerticalCatalogService
from app.exceptions import ServiceOSException


@pytest.mark.asyncio
async def test_submit_for_review_syncs_admin_queue_and_enrollment():
    tenant_id = uuid.uuid4()
    enrollment_id = uuid.uuid4()
    vertical_id = uuid.uuid4()
    svc = VerticalCatalogService()
    svc.get_or_create_enrollment = AsyncMock(return_value={
        "id": str(enrollment_id), "vertical_id": str(vertical_id), "status": "draft",
    })
    svc.transition_enrollment = AsyncMock(return_value={"id": str(enrollment_id), "status": "submitted"})
    db = MagicMock()
    db.execute = AsyncMock()

    with (
        patch(
            "app.engines.vertical_catalog.home_services_setup_service.get_setup_overview",
            new=AsyncMock(return_value={
                "sections": [{"key": "BUSINESS_PROFILE", "required": True, "status": "complete"}],
            }),
        ),
        patch(
            "app.engines.vertical_catalog.declarations.get_declaration_status",
            new=AsyncMock(return_value={"all_accepted": True}),
        ),
    ):
        result = await svc.submit_for_review(db, tenant_id, "home_services", actor_id=uuid.uuid4())

    assert result["status"] == "submitted"
    sql = str(db.execute.await_args.args[0])
    assert "verification_status='pending'" in sql
    assert "status='under_review'" in sql
    svc.transition_enrollment.assert_awaited_once()


@pytest.mark.asyncio
async def test_submit_for_review_rejects_incomplete_required_sections():
    tenant_id = uuid.uuid4()
    svc = VerticalCatalogService()
    svc.get_or_create_enrollment = AsyncMock(return_value={
        "id": str(uuid.uuid4()), "vertical_id": str(uuid.uuid4()), "status": "draft",
    })
    svc.transition_enrollment = AsyncMock()
    db = MagicMock()

    with patch(
        "app.engines.vertical_catalog.home_services_setup_service.get_setup_overview",
        new=AsyncMock(return_value={
            "sections": [{"key": "COVERAGE_AVAILABILITY", "required": True, "status": "in_progress"}],
        }),
    ):
        with pytest.raises(ServiceOSException) as exc:
            await svc.submit_for_review(db, tenant_id, "home_services")

    assert exc.value.error_code == "VERTICAL_SETUP_INCOMPLETE"
    assert exc.value.context == {"incomplete_sections": ["COVERAGE_AVAILABILITY"]}
    svc.transition_enrollment.assert_not_awaited()


@pytest.mark.asyncio
async def test_admin_approval_uses_canonical_activation_orchestrator():
    from app.engines.provider_portal.admin_router import _sync_home_services_enrollment_decision

    tenant_id = uuid.uuid4()
    enrollment_id = uuid.uuid4()
    db = MagicMock()
    query_result = MagicMock()
    query_result.fetchone.return_value = SimpleNamespace(id=enrollment_id, status="submitted")
    db.execute = AsyncMock(return_value=query_result)

    with patch(
        "app.engines.vertical_catalog.activation.approve_and_evaluate",
        new=AsyncMock(return_value={"id": str(enrollment_id), "status": "activation_requirements_pending"}),
    ) as approve:
        result = await _sync_home_services_enrollment_decision(
            db, tenant_id, "approve", actor_id=str(uuid.uuid4())
        )

    assert result["status"] == "activation_requirements_pending"
    approve.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("decision, expected", [
    ("request_changes", "changes_requested"),
    ("reject", "rejected"),
])
async def test_admin_nonapproval_decisions_sync_enrollment(decision, expected):
    from app.engines.provider_portal.admin_router import _sync_home_services_enrollment_decision

    tenant_id = uuid.uuid4()
    enrollment_id = uuid.uuid4()
    db = MagicMock()
    query_result = MagicMock()
    query_result.fetchone.return_value = SimpleNamespace(id=enrollment_id, status="submitted")
    db.execute = AsyncMock(return_value=query_result)

    with patch.object(
        VerticalCatalogService,
        "transition_enrollment",
        new=AsyncMock(return_value={"id": str(enrollment_id), "status": expected}),
    ) as transition:
        result = await _sync_home_services_enrollment_decision(
            db, tenant_id, decision, actor_id=str(uuid.uuid4()), reason="Please update the document"
        )

    assert result["status"] == expected
    assert transition.await_args.args[2] == expected

@pytest.mark.asyncio
async def test_business_profile_options_are_real_and_selectable():
    from types import SimpleNamespace
    from app.engines.profile.router import get_business_profile_options

    request = SimpleNamespace(state=SimpleNamespace(request_id="profile-options-test"))
    response = await get_business_profile_options(request, actor=SimpleNamespace(role="tenant_owner"))
    values = {item["value"] for item in response.data["entity_types"]}
    assert "sole_proprietorship" in values
    assert "Karnataka" in response.data["states"]


def test_setup_profile_requires_the_full_registered_address():
    from types import SimpleNamespace
    from app.engines.vertical_catalog.document_requirements import is_business_profile_complete

    complete = dict(
        business_name="Audit Services", business_type="sole_proprietorship",
        phone="+919876543210", email="audit@example.com", address_line1="42 Audit Avenue",
        district="Indiranagar", city="Bengaluru", state="Karnataka", zipcode="560038",
    )
    assert is_business_profile_complete(SimpleNamespace(**complete)) is True
    assert is_business_profile_complete(SimpleNamespace(**{**complete, "district": None})) is False
    assert is_business_profile_complete(SimpleNamespace(**{**complete, "zipcode": None})) is False
