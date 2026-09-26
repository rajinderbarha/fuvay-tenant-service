"""Regression coverage for provider legal-identity continuity."""
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

import pytest

from app.engines.public_registration.models import ProviderIdentityReviewCase
from app.engines.public_registration.service import (
    RegistrationService,
    _normalize_business_name,
    _normalize_legal_identifier,
    _registered_postcode,
)
from app.engines.security.admin_service import (
    POLICY_DEFAULTS,
    POLICY_RECOMMENDED,
    POLICY_RULES,
    SecurityAdminService,
)
from app.exceptions import ServiceOSException


ROOT = Path(__file__).resolve().parents[1]
POLICIES = {
    "provider_reregistration_guard_enabled",
    "provider_reregistration_composite_match_enabled",
}


def test_identity_values_are_canonical_before_comparison():
    assert _normalize_legal_identifier(" 03abcde1234f1z5 ") == "03ABCDE1234F1Z5"
    assert _normalize_legal_identifier("abc-de 1234-f") == "ABCDE1234F"
    assert _normalize_business_name(" Fuvay Home-Services Pvt. Ltd. ") == "FUVAYHOMESERVICESPVTLTD"
    assert _registered_postcode({"pincode": "140 412"}) == "140412"


def test_migration_admin_policy_and_review_ui_are_wired():
    migration = (ROOT / "alembic/versions/391_provider_reregistration_guard.py").read_text("utf-8")
    page = (ROOT / "frontend/super-admin/app/admin/security/page.tsx").read_text("utf-8")
    assert 'down_revision = "390"' in migration
    assert "provider_identity_review_cases" in migration
    assert POLICIES <= set(POLICY_RULES) == set(POLICY_DEFAULTS) == set(POLICY_RECOMMENDED)
    for key in POLICIES:
        assert key in migration
        assert key in page
    assert "restore_existing_account" in page
    assert "reject_evasion" in page
    assert "false_positive" in page


@pytest.mark.asyncio
async def test_matching_identity_is_committed_before_signup_is_blocked():
    registration_id = uuid.uuid4()
    tenant = SimpleNamespace(
        id=uuid.uuid4(), status="suspended", health_score=22,
        health_band="at_risk",
    )
    pending = SimpleNamespace(id=registration_id, status="in_progress")
    no_existing = MagicMock()
    no_existing.scalar_one_or_none.return_value = None
    stats = MagicMock()
    stats.one.return_value = (2, 300)
    db = MagicMock(
        execute=AsyncMock(side_effect=[no_existing, stats]),
        flush=AsyncMock(), commit=AsyncMock(), add=MagicMock(),
    )
    service = RegistrationService(db)
    service._identity_matches = AsyncMock(return_value=[(tenant, ["pan"], "high")])
    service._audit = AsyncMock()

    async def policy_value(_db, key, default):
        return True

    with patch("app.engines.security.policy_runtime.security_policy_value", new=policy_value):
        with pytest.raises(ServiceOSException) as error:
            await service._enforce_provider_identity_continuity(pending)

    assert error.value.error_code == "PROVIDER_IDENTITY_REVIEW_REQUIRED"
    assert pending.status == "identity_review"
    db.commit.assert_awaited_once()
    case = next(call.args[0] for call in db.add.call_args_list
                if isinstance(call.args[0], ProviderIdentityReviewCase))
    assert case.match_signals == ["pan"]
    assert case.risk_snapshot["sla_breached_jobs"] == 2
    assert case.risk_snapshot["sla_penalties"] == 300.0


@pytest.mark.asyncio
async def test_false_positive_reopens_only_when_no_other_case_is_open():
    case = ProviderIdentityReviewCase(
        registration_id=uuid.uuid4(), matched_tenant_id=uuid.uuid4(),
        status="open", match_strength="medium",
        match_signals=["business_name_and_registered_postcode"],
        risk_snapshot={},
    )
    case.id = uuid.uuid4()
    case.created_at = datetime.now(timezone.utc)
    registration = SimpleNamespace(
        id=case.registration_id, status="identity_review",
        business_name="Applicant", legal_name="Applicant Legal",
    )
    tenant = SimpleNamespace(
        id=case.matched_tenant_id, business_name="Existing Provider",
        tenant_name="Existing Provider", tenant_code="PRV-1", status="suspended",
    )
    no_other = MagicMock()
    no_other.scalar_one.return_value = 0
    db = MagicMock(
        get=AsyncMock(side_effect=[case, registration, tenant]),
        execute=AsyncMock(return_value=no_other),
    )
    service = SecurityAdminService(db, actor_id=uuid.uuid4())
    service._audit = AsyncMock()

    result = await service.resolve_provider_identity_case(
        case.id, "false_positive", "Verified separate legal ownership documents.",
    )

    assert result["decision"] == "false_positive"
    assert registration.status == "in_progress"
    service._audit.assert_awaited_once()
