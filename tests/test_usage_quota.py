"""
Phase 11 — Finance/Wallet/Commission/Billing audit found one real gap:
TenantLimits.current_staff_count / current_active_jobs / current_api_calls_today
were defined, enforced by check_limit(), but NEVER incremented or decremented
anywhere — every tenant silently had unlimited usage regardless of plan.

This verifies: (1) the shared adjust_usage() helper actually mutates the
counter and no-ops gracefully for tenants with no TenantLimits row, (2)
inviting/deactivating staff keeps current_staff_count honest and the plan
limit is actually enforced before an invite is created, (3) job
creation/closure/voiding keeps current_active_jobs honest.
"""
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.exceptions import ServiceOSException


def make_limits(**kw):
    defaults = dict(tenant_id=uuid.uuid4(), max_staff=10, current_staff_count=0,
                     max_active_jobs=20, current_active_jobs=0,
                     max_api_calls_per_day=5000, current_api_calls_today=0)
    defaults.update(kw)
    return MagicMock(**defaults)


# ── adjust_usage helper ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_adjust_usage_increments_existing_counter():
    from app.core.usage_quota import adjust_usage
    limits = make_limits(current_staff_count=2)
    result = MagicMock(); result.scalar_one_or_none.return_value = limits
    db = MagicMock(); db.execute = AsyncMock(return_value=result)

    await adjust_usage(db, limits.tenant_id, "current_staff_count", 1)
    assert limits.current_staff_count == 3


@pytest.mark.asyncio
async def test_adjust_usage_never_goes_negative():
    from app.core.usage_quota import adjust_usage
    limits = make_limits(current_active_jobs=0)
    result = MagicMock(); result.scalar_one_or_none.return_value = limits
    db = MagicMock(); db.execute = AsyncMock(return_value=result)

    await adjust_usage(db, limits.tenant_id, "current_active_jobs", -1)
    assert limits.current_active_jobs == 0


@pytest.mark.asyncio
async def test_adjust_usage_noop_when_no_limits_row():
    """Tenants with no TenantLimits row are unrestricted — must not error."""
    from app.core.usage_quota import adjust_usage
    result = MagicMock(); result.scalar_one_or_none.return_value = None
    db = MagicMock(); db.execute = AsyncMock(return_value=result)

    await adjust_usage(db, uuid.uuid4(), "current_staff_count", 1)  # should not raise


@pytest.mark.asyncio
async def test_adjust_usage_rejects_unknown_field():
    from app.core.usage_quota import adjust_usage
    db = MagicMock()
    with pytest.raises(ValueError):
        await adjust_usage(db, uuid.uuid4(), "not_a_real_field", 1)


# ── Staff invite/deactivate keep current_staff_count honest ────────────────

@pytest.mark.asyncio
async def test_invite_staff_blocks_when_at_plan_limit():
    from app.engines.auth.service import AuthService
    tid = uuid.uuid4()

    no_existing_user = MagicMock(); no_existing_user.scalar_one_or_none.return_value = None
    db = MagicMock(); db.execute = AsyncMock(return_value=no_existing_user)
    svc = AuthService(db=db)

    import app.engines.tenant_engine.service as tenant_module
    real_check_limit = tenant_module.TenantService.check_limit
    async def fake_check_limit(self, tenant_id, limit_type):
        raise ServiceOSException("PLAN_LIMIT_EXCEEDED", "Reached staff_count limit (10).")
    tenant_module.TenantService.check_limit = fake_check_limit
    try:
        with pytest.raises(ServiceOSException) as exc:
            await svc.invite_staff(tid, uuid.uuid4(), "new@biz.io", "New Staff", None, [])
    finally:
        tenant_module.TenantService.check_limit = real_check_limit
    assert exc.value.error_code == "PLAN_LIMIT_EXCEEDED"


@pytest.mark.asyncio
async def test_invite_staff_increments_usage_counter_on_success():
    from app.engines.auth.service import AuthService
    tid = uuid.uuid4()
    limits = make_limits(current_staff_count=2)

    no_existing_user = MagicMock(); no_existing_user.scalar_one_or_none.return_value = None
    limits_result = MagicMock(); limits_result.scalar_one_or_none.return_value = limits
    db = MagicMock()
    db.execute = AsyncMock(side_effect=[no_existing_user, limits_result])
    db.flush = AsyncMock()
    svc = AuthService(db=db)

    import app.engines.tenant_engine.service as tenant_module
    real_check_limit = tenant_module.TenantService.check_limit
    tenant_module.TenantService.check_limit = AsyncMock(return_value={"allowed": True})
    try:
        await svc.invite_staff(tid, uuid.uuid4(), "new@biz.io", "New Staff", None, [])
    finally:
        tenant_module.TenantService.check_limit = real_check_limit

    assert limits.current_staff_count == 3


@pytest.mark.asyncio
async def test_deactivate_staff_decrements_usage_counter():
    from app.engines.auth.service import AuthService
    tid = uuid.uuid4()
    user = MagicMock(id=uuid.uuid4(), tenant_id=tid, is_active=True)
    limits = make_limits(current_staff_count=3)

    user_result = MagicMock(); user_result.scalar_one_or_none.return_value = user
    limits_result = MagicMock(); limits_result.scalar_one_or_none.return_value = limits
    db = MagicMock()
    db.execute = AsyncMock(side_effect=[user_result, limits_result, MagicMock()])
    svc = AuthService(db=db)

    await svc.deactivate_staff(user.id, tid, uuid.uuid4())
    assert limits.current_staff_count == 2


@pytest.mark.asyncio
async def test_deactivate_already_inactive_staff_does_not_double_decrement():
    from app.engines.auth.service import AuthService
    tid = uuid.uuid4()
    user = MagicMock(id=uuid.uuid4(), tenant_id=tid, is_active=False)  # already inactive
    user_result = MagicMock(); user_result.scalar_one_or_none.return_value = user
    db = MagicMock()
    db.execute = AsyncMock(side_effect=[user_result, MagicMock()])
    svc = AuthService(db=db)

    await svc.deactivate_staff(user.id, tid, uuid.uuid4())
    # 2 calls expected regardless (user lookup + session revoke) — the point is
    # there's no THIRD call to look up/adjust TenantLimits for an already-inactive user.
    assert db.execute.call_count == 2


# ── Job creation/close/void keep current_active_jobs honest ────────────────

@pytest.mark.asyncio
async def test_create_job_increments_active_jobs_counter():
    from app.engines.field_ops.service import FieldOpsService
    tid = uuid.uuid4()
    limits = make_limits(current_active_jobs=4)
    limits_result = MagicMock(); limits_result.scalar_one_or_none.return_value = limits
    db = MagicMock()
    db.execute = AsyncMock(return_value=limits_result)
    db.flush = AsyncMock()
    import datetime as _dt
    db.add = MagicMock(side_effect=lambda o: setattr(o, "created_at", _dt.datetime.now(_dt.timezone.utc))
                        if getattr(o, "created_at", None) is None else None)
    svc = FieldOpsService(db=db)

    await svc.create_job(tid, {"title": "AC Repair", "service_type_id": "ac_repair"})
    assert limits.current_active_jobs == 5


@pytest.mark.asyncio
async def test_void_job_decrements_active_jobs_counter():
    from app.engines.field_ops.service import FieldOpsService
    from app.engines.field_ops.constants import JS

    tid = uuid.uuid4()
    job = MagicMock(id=uuid.uuid4(), tenant_id=tid, status=JS.DISPATCHED)
    limits = make_limits(current_active_jobs=5)

    job_result = MagicMock(); job_result.scalar_one_or_none.return_value = job
    limits_result = MagicMock(); limits_result.scalar_one_or_none.return_value = limits
    db = MagicMock()
    db.execute = AsyncMock(side_effect=[job_result, limits_result])
    svc = FieldOpsService(db=db)
    svc._write_history = AsyncMock()

    await svc.void_job(job.id, "customer cancelled")
    assert limits.current_active_jobs == 4


@pytest.mark.asyncio
async def test_update_status_to_cancelled_decrements_active_jobs():
    from app.engines.field_ops.service import FieldOpsService
    from app.engines.field_ops.constants import JS, JobType

    tid = uuid.uuid4()
    job = MagicMock(id=uuid.uuid4(), tenant_id=tid, status=JS.DRAFT, job_type=JobType.REPAIR,
                     assigned_staff_id=None, checklist=[])
    limits = make_limits(current_active_jobs=3)

    job_result = MagicMock(); job_result.scalar_one_or_none.return_value = job
    limits_result = MagicMock(); limits_result.scalar_one_or_none.return_value = limits
    db = MagicMock()
    db.execute = AsyncMock(side_effect=[job_result, limits_result])
    svc = FieldOpsService(db=db)
    svc._write_history = AsyncMock()
    svc._publish = AsyncMock()

    await svc.update_status(job.id, JS.CANCELLED, "customer no-show", None, None)
    assert limits.current_active_jobs == 2
