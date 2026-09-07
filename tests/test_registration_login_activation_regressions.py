"""Behavioral coverage for registration, login and delayed activation."""
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.engines.auth.schemas import LoginRequest
from app.engines.public_registration.service import RegistrationService
from app.engines.vertical_catalog.service import VerticalCatalogService


@pytest.mark.parametrize("phone", ["9041624576", "09041624576", "91 90416 24576", "+91 90416-24576"])
def test_login_accepts_signup_mobile_formats(phone):
    assert LoginRequest(email=phone, password="secret").email == "+919041624576"


@pytest.mark.asyncio
async def test_editing_verified_signup_contacts_requires_new_verification():
    pending = SimpleNamespace(id=uuid.uuid4(), email="old@example.com", mobile="+919041624576",
                              email_verified=True, mobile_verified=True)
    db = MagicMock(flush=AsyncMock())
    svc = RegistrationService(db)
    svc._get_pending = AsyncMock(return_value=pending)
    svc._send_otps = AsyncMock(return_value={})
    svc._audit = AsyncMock()
    with patch("app.engines.public_registration.service.validate_password_strength", return_value=[]), \
         patch("app.engines.public_registration.service.hash_password", return_value="hashed"):
        result = await svc.start_or_resume("Owner", "new@example.com", "9041624577", "secret", "secret",
                                           False, False, False, registration_id=pending.id)
    assert not result["email_verified"]
    assert not result["mobile_verified"]
    assert pending.email == "new@example.com"
    assert pending.mobile == "+919041624577"


@pytest.mark.asyncio
async def test_enrollment_transition_does_not_commit_partial_approval():
    # submitted_at populated -- a real "submitted" row always has it; the
    # submission gate added in a93de26 checks this field, not status alone.
    row = SimpleNamespace(id=uuid.uuid4(), tenant_id=uuid.uuid4(), vertical_id=uuid.uuid4(),
                          status="submitted", submitted_at=datetime.now(timezone.utc))
    result = MagicMock()
    result.scalar_one_or_none.return_value = row
    db = MagicMock(execute=AsyncMock(return_value=result), flush=AsyncMock(), commit=AsyncMock(), refresh=AsyncMock())
    svc = VerticalCatalogService()
    svc._enrollment_dict = lambda r: {"status": r.status}
    transitioned = await svc.transition_enrollment(db, row.id, "approved_pending_activation")
    assert transitioned["status"] == "approved_pending_activation"
    db.commit.assert_not_awaited()
    db.flush.assert_awaited()


@pytest.mark.asyncio
async def test_delayed_activation_updates_tenant_account():
    from app.engines.vertical_catalog.activation import try_auto_activate
    tenant_id, enrollment_id = uuid.uuid4(), uuid.uuid4()
    db = MagicMock(execute=AsyncMock())
    svc = MagicMock()
    svc.get_or_create_enrollment = AsyncMock(return_value={"id": str(enrollment_id), "status": "activation_requirements_pending"})
    svc._by_key = AsyncMock(return_value=SimpleNamespace(id=uuid.uuid4()))
    svc.transition_enrollment = AsyncMock(side_effect=[{"status": "activating"}, {"status": "active"}])
    with patch("app.engines.vertical_catalog.activation.VerticalCatalogService", return_value=svc), \
         patch("app.engines.vertical_catalog.activation.evaluate_activation_gates", new=AsyncMock(return_value=[{"state": "ready"}])):
        result = await try_auto_activate(db, tenant_id)
    assert result["status"] == "active"
    assert [call.args[2] for call in svc.transition_enrollment.await_args_list] == ["activating", "active"]
    assert db.execute.await_args.args[1] == {"tid": str(tenant_id)}
    db.execute.assert_awaited_once()
