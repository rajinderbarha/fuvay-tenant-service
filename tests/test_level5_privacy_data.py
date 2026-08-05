"""PRIVACY-DATA (2026-08-01) — customer Privacy & Data screen phase.

Real bug found and fixed during audit: `ComplianceService.process_deletion`
step 1 (anonymize auth/identity data) checked `hasattr(user, "phone_number")`
before clearing a customer's phone -- but the real `User` model column is
`phone` (confirmed in `app/engines/auth/models.py`), not `phone_number`.
The hasattr check always evaluated False, so a "completed" erasure never
actually cleared the phone number despite `tables_erased` claiming "users"
was fully anonymized.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.engines.compliance.service import ComplianceService


def _exec_result(*, scalar=None):
    res = MagicMock()
    res.scalar_one_or_none = MagicMock(return_value=scalar)
    return res


def _db():
    db = MagicMock()
    db.execute = AsyncMock()
    db.flush = AsyncMock()
    db.add = MagicMock()
    return db


class TestPhoneAnonymizationFix:
    @pytest.mark.asyncio
    async def test_erasure_actually_clears_the_real_phone_column(self):
        user_id = uuid.uuid4()
        user = SimpleNamespace(id=user_id, email="rajinder@example.com",
                                full_name="Rajinder Singh", phone="+919900024102")
        req = SimpleNamespace(
            id=uuid.uuid4(), user_id=user_id, tenant_id=None,
            status="pending", request_reason="test",
            sla_deadline=datetime.now(timezone.utc) + timedelta(hours=72),
            processed_at=None, tables_erased=None, tables_exempted=None,
            exemption_reasons=None, processed_by=None, created_at=datetime.now(timezone.utc),
        )
        svc = ComplianceService(db=_db(), actor_id=user_id)
        svc.db.execute = AsyncMock(side_effect=[
            _exec_result(scalar=req),   # load DataDeletionRequest
            _exec_result(scalar=user),  # load User
        ])
        svc._audit = AsyncMock()
        svc._publish = AsyncMock()

        # Remaining engine lookups (bookings/messages/reviews/sessions) are
        # allowed to fail gracefully -- the method catches and logs per
        # step, confirmed in source -- so a bare mock returning empty is
        # sufficient to isolate the phone-clearing assertion.
        async def _side_effect(*args, **kwargs):
            res = MagicMock()
            scalars = MagicMock()
            scalars.all = MagicMock(return_value=[])
            res.scalars = MagicMock(return_value=scalars)
            return res

        call_count = {"n": 0}
        original = svc.db.execute

        async def _execute(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] <= 2:
                return await original(*args, **kwargs)
            return await _side_effect(*args, **kwargs)

        svc.db.execute = _execute

        await svc.process_deletion(req.id)

        assert user.phone is None
        assert user.email == f"deleted_{user_id}@erasure.invalid"
        assert user.full_name == "Deleted User"
