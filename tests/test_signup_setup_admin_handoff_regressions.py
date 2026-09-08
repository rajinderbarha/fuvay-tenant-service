"""Regression coverage for the tenant -> Admin Home Services handoff."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

import pytest

from app.engines.vertical_catalog.service import VerticalCatalogService
from app.exceptions import ServiceOSException


def test_signup_normalizes_indian_mobile_numbers_to_e164():
    from app.engines.public_registration.service import _normalize_mobile

    assert _normalize_mobile("9041624576") == "+919041624576"
    assert _normalize_mobile("09041624576") == "+919041624576"
    assert _normalize_mobile("91 90416 24576") == "+919041624576"
    assert _normalize_mobile("+91 90416-24576") == "+919041624576"


def test_signup_rejects_ambiguous_invalid_mobile_numbers():
    from app.engines.public_registration.service import _normalize_mobile

    with pytest.raises(ServiceOSException) as exc:
        _normalize_mobile("12345")
    assert exc.value.error_code == "INVALID_MOBILE"


@pytest.mark.parametrize("status", [
    "approved", "approved_pending_activation", "activation_requirements_pending", "activating",
])
def test_signup_status_projects_every_activation_stage(status):
    from app.engines.public_registration.service import RegistrationService

    tenant = SimpleNamespace(status="pending_activation")
    enrollment = SimpleNamespace(status=status)
    assert RegistrationService(db=MagicMock())._compute_stage(tenant, enrollment) == "approved_pending_activation"


def test_signup_wizard_restores_refresh_safe_draft_without_passwords():
    from pathlib import Path

    source = Path("frontend/tenant-portal/app/register/page.tsx").read_text(encoding="utf-8")
    assert "SIGNUP_DRAFT_KEY" in source
    assert 'password: "", confirmPassword: ""' in source
    assert "localStorage.removeItem(SIGNUP_DRAFT_KEY)" in source


def test_signup_resend_reports_cooldown_and_success_feedback():
    from pathlib import Path

    service = Path("app/engines/public_registration/service.py").read_text(encoding="utf-8")
    page = Path("frontend/tenant-portal/app/register/page.tsx").read_text(encoding="utf-8")
    assert '"OTP_RESEND_COOLDOWN"' in service
    assert "status_code=429" in service
    assert "A new ${channel} code was sent." in page


@pytest.mark.asyncio
async def test_signup_resend_does_not_claim_success_during_cooldown():
    from app.engines.public_registration.service import RegistrationService, utcnow

    db = AsyncMock()
    query_result = MagicMock()
    query_result.scalar_one_or_none.return_value = SimpleNamespace(created_at=utcnow())
    db.execute.return_value = query_result
    service = RegistrationService(db=db)
    pending = SimpleNamespace(id=uuid.uuid4(), mobile="+919876543210", email="owner@example.com")

    with patch.object(service, "_get_pending", new=AsyncMock(return_value=pending)), \
         patch.object(service, "_send_otps", new=AsyncMock()) as send:
        with pytest.raises(ServiceOSException) as exc:
            await service.resend_otp(pending.id, "mobile")

    assert exc.value.error_code == "OTP_RESEND_COOLDOWN"
    assert exc.value.status_code == 429
    send.assert_not_awaited()


def test_admin_approval_notifies_provider_with_correct_destination():
    from pathlib import Path

    source = Path("app/engines/provider_portal/admin_router.py").read_text(encoding="utf-8")
    assert 'notification_type="tenant.verification_approved"' in source
    assert '"/dashboard" if is_active else "/onboarding/activation-center"' in source


def test_post_approval_ui_has_no_retired_deposit_copy():
    from pathlib import Path

    for relative in (
        "frontend/tenant-portal/app/(onboarding)/tenant/home-services/setup/review/page.tsx",
        "frontend/tenant-portal/app/onboarding/application-status/page.tsx",
        "frontend/tenant-portal/app/onboarding/activation-center/page.tsx",
    ):
        source = Path(relative).read_text(encoding="utf-8")
        assert "Security deposit" not in source
        assert "security_deposit" not in source


def test_terminal_rejection_ui_does_not_offer_resubmission():
    from pathlib import Path

    review = Path("frontend/tenant-portal/app/(onboarding)/tenant/home-services/setup/review/page.tsx").read_text(encoding="utf-8")
    overview = Path("frontend/tenant-portal/app/(onboarding)/tenant/home-services/setup/overview/page.tsx").read_text(encoding="utf-8")
    assert 'status === "rejected"' in review
    assert "Contact support if you believe this decision should be reviewed." in review
    assert "make corrections, and resubmit" not in overview


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["draft", "changes_requested"])
async def test_submit_for_review_syncs_admin_queue_and_enrollment(status):
    tenant_id = uuid.uuid4()
    enrollment_id = uuid.uuid4()
    vertical_id = uuid.uuid4()
    svc = VerticalCatalogService()
    svc.get_or_create_enrollment = AsyncMock(return_value={
        "id": str(enrollment_id), "vertical_id": str(vertical_id), "status": status,
    })
    svc.transition_enrollment = AsyncMock(return_value={"id": str(enrollment_id), "status": "submitted"})
    db = MagicMock()
    query_result = MagicMock()
    query_result.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=query_result)

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
