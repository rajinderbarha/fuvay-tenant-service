"""Direct-payment dispute and Security workspace regression coverage."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

import pytest

from app.engines.invoice_payment.direct_payments_service import DirectPaymentsService
from app.exceptions import ServiceOSException


def _payment():
    return SimpleNamespace(
        id=uuid.uuid4(), tenant_id=uuid.uuid4(), customer_id=uuid.uuid4(),
        job_id=uuid.uuid4(), dispute_complaint_id=None,
        payment_status="verified", reconciliation_status="confirmed",
        customer_confirmed=True, customer_confirmation_action="confirm",
        customer_reported_amount=None, collected_amount=Decimal("1575.00"),
        provider_confirmed_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_direct_payment_dispute_requires_actual_reason_and_never_fabricates_one():
    db = MagicMock()
    svc = DirectPaymentsService(db, uuid.uuid4())
    pay = _payment()
    svc._get_record = AsyncMock(return_value=pay)
    svc._job = AsyncMock()
    with pytest.raises(ServiceOSException) as exc:
        await svc.open_dispute(payment_id=pay.id, actor_user_id=str(uuid.uuid4()),
                               description="  ")
    assert exc.value.error_code == "DIRECT_PAYMENT_DISPUTE_REASON_REQUIRED"
    svc._job.assert_not_awaited()
    db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_provider_dispute_creates_one_atomic_provider_attributed_complaint():
    from app.engines.complaints.complaint_service import ComplaintService

    db = MagicMock()
    db.commit = AsyncMock()
    pay = _payment()
    actor_id, complaint_id = uuid.uuid4(), uuid.uuid4()
    svc = DirectPaymentsService(db, pay.tenant_id)
    svc._get_record = AsyncMock(return_value=pay)
    svc._job = AsyncMock(return_value=SimpleNamespace(
        category_id=uuid.uuid4(), offering_id=uuid.uuid4(), job_number="JOB-1"))
    svc._log = AsyncMock()
    svc.get_detail = AsyncMock(return_value={"record": {"status": "disputed"}})
    reason = "The customer showed a different UPI transfer reference."
    with patch.object(ComplaintService, "create_complaint", new_callable=AsyncMock) as create:
        create.return_value = SimpleNamespace(id=complaint_id, complaint_number="CMP-1")
        with patch("app.engines.complaints.notifications.notify_customer_complaint_channel",
                   new_callable=AsyncMock) as notify:
            notify.return_value = False
            result = await svc.open_dispute(payment_id=pay.id, actor_user_id=str(actor_id),
                                            description=reason)
    assert result["record"]["status"] == "disputed"
    assert create.await_args.kwargs["complaint_type"] == "payment_issue"
    assert create.await_args.kwargs["description"] == reason
    assert create.await_args.kwargs["internal_payment_dispute"] is True
    assert create.await_args.kwargs["created_by_actor_type"] == "provider"
    assert create.await_args.kwargs["created_by_actor_user_id"] == actor_id
    assert create.await_args.kwargs["commit"] is False
    assert pay.dispute_complaint_id == complaint_id
    notify.assert_awaited_once()
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_customer_dispute_is_attributed_to_customer():
    from app.engines.complaints.complaint_service import ComplaintService

    db = MagicMock()
    db.commit = AsyncMock()
    pay = _payment()
    svc = DirectPaymentsService(db, pay.tenant_id)
    svc._get_record = AsyncMock(return_value=pay)
    svc._job = AsyncMock(return_value=SimpleNamespace(
        category_id=uuid.uuid4(), offering_id=uuid.uuid4(), job_number="JOB-2"))
    svc._log = AsyncMock()
    svc.get_detail = AsyncMock(return_value={})
    with patch.object(ComplaintService, "create_complaint", new_callable=AsyncMock) as create:
        create.return_value = SimpleNamespace(id=uuid.uuid4())
        await svc.open_dispute(payment_id=pay.id, actor_user_id=str(pay.customer_id),
                               actor_type="customer", description="I paid a different amount.")
    assert create.await_args.kwargs["created_by_actor_type"] == "customer"
    assert create.await_args.kwargs["created_by_actor_user_id"] == pay.customer_id


def test_security_workspace_uses_canonical_session_and_threat_controls():
    root = Path(__file__).resolve().parents[1]
    admin = (root / "app/engines/security/admin_service.py").read_text(encoding="utf-8")
    auth = (root / "app/engines/auth/service.py").read_text(encoding="utf-8")
    router = (root / "app/engines/security/admin_router.py").read_text(encoding="utf-8")
    constants = (root / "app/engines/security/constants.py").read_text(encoding="utf-8")
    assert "UserSession.last_active_at > idle_cutoff" not in admin
    assert 'stale.revocation_reason = "Concurrent session limit enforced"' in auth
    assert 'notes: str = Field(min_length=5, max_length=1000)' in router
    assert 't.resolved_at = None' in admin
    for operation in ("policy.update", "session.revoke", "api_key.rotate", "ip.unblock"):
        assert f'"{operation}"' in constants


def test_scoped_network_block_cannot_disable_another_scope():
    from app.middleware import IPBlocklistMiddleware
    assert IPBlocklistMiddleware._scope_matches("staff", "technician", None, None)
    assert not IPBlocklistMiddleware._scope_matches("staff", "customer", None, None)
    root = Path(__file__).resolve().parents[1]
    middleware = (root / "app/middleware.py").read_text(encoding="utf-8")
    admin = (root / "app/engines/security/admin_service.py").read_text(encoding="utf-8")
    assert 'scope == "staff" and role == "technician"' in middleware
    assert "expired_candidates" in middleware
    assert "if remaining is None:" in admin


def test_expired_session_is_not_mislabelled_as_revoked():
    from app.engines.security.admin_service import SecurityAdminService

    session = SimpleNamespace(
        id=uuid.uuid4(), user_id=uuid.uuid4(), tenant_id=None, device_id="dev",
        device_name="Browser", device_type="web", ip_address=None,
        is_trusted=False, is_approved=True, revoked_at=None,
        expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
        last_active_at=datetime.now(timezone.utc), revocation_reason=None,
    )
    user = SimpleNamespace(email="admin@example.test", full_name="Admin", role="super_admin")
    assert SecurityAdminService._session_to_dict(None, session, user)["status"] == "expired"


@pytest.mark.parametrize("case_status, expected", [
    ("open", True), ("awaiting_provider_response", True),
    ("resolved", False), ("closed", False), ("settled", False),
    (None, True),
])
def test_disputed_payment_only_needs_action_while_case_is_open(case_status, expected):
    assert DirectPaymentsService._needs_action({
        "status": "disputed", "dispute_case_status": case_status,
    }) is expected
