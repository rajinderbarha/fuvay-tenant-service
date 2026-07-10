"""
Follow-up to Phase 11: current_api_calls_today was the one usage counter
left unfixed (needs request-level counting + a daily reset, unlike
staff_count/active_jobs which are tied to specific business actions).

This verifies: (1) the Redis-backed counter increments and sets a
midnight-UTC TTL on first use that day (the "daily reset" — no cron needed),
(2) the UsageQuotaMiddleware actually calls the counter for tenant-scoped
requests and is a no-op for requests with no X-Tenant-ID, (3) check_limit()
reads the live Redis count for api_calls instead of the always-stale
Postgres column.
"""
import uuid
from datetime import datetime, timezone
import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.mark.asyncio
async def test_increment_api_calls_sets_midnight_ttl_on_first_call_of_day():
    from app.core.usage_quota import increment_api_calls
    redis = MagicMock()
    redis.incr = AsyncMock(return_value=1)
    redis.expire = AsyncMock()

    count = await increment_api_calls(redis, "tenant-123")

    assert count == 1
    redis.expire.assert_called_once()
    key, ttl = redis.expire.call_args.args
    assert 0 < ttl <= 86400


@pytest.mark.asyncio
async def test_increment_api_calls_does_not_reset_ttl_on_subsequent_calls():
    from app.core.usage_quota import increment_api_calls
    redis = MagicMock()
    redis.incr = AsyncMock(return_value=5)  # not the first call today
    redis.expire = AsyncMock()

    count = await increment_api_calls(redis, "tenant-123")

    assert count == 5
    redis.expire.assert_not_called()


@pytest.mark.asyncio
async def test_get_api_calls_today_returns_zero_when_no_key():
    from app.core.usage_quota import get_api_calls_today
    redis = MagicMock()
    redis.get = AsyncMock(return_value=None)

    assert await get_api_calls_today(redis, "tenant-123") == 0


@pytest.mark.asyncio
async def test_get_api_calls_today_decodes_bytes():
    from app.core.usage_quota import get_api_calls_today
    redis = MagicMock()
    redis.get = AsyncMock(return_value=b"42")

    assert await get_api_calls_today(redis, "tenant-123") == 42


@pytest.mark.asyncio
async def test_api_calls_key_is_scoped_per_tenant_and_changes_per_day():
    from app.core.usage_quota import _api_calls_key
    key_a = _api_calls_key("tenant-A")
    key_b = _api_calls_key("tenant-B")
    assert key_a != key_b
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    assert today in key_a


# ── Middleware ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_usage_quota_middleware_increments_for_tenant_request():
    from app.middleware import UsageQuotaMiddleware
    mw = UsageQuotaMiddleware(app=MagicMock())

    request = MagicMock()
    request.headers = {"X-Tenant-ID": "tenant-123"}
    call_next = AsyncMock(return_value=MagicMock())

    captured = {}
    async def fake_increment(redis, tenant_id):
        captured["tenant_id"] = tenant_id
        return 1

    import app.core.usage_quota as quota_module
    real = quota_module.increment_api_calls
    quota_module.increment_api_calls = fake_increment
    try:
        await mw.dispatch(request, call_next)
    finally:
        quota_module.increment_api_calls = real

    assert captured["tenant_id"] == "tenant-123"
    call_next.assert_awaited_once_with(request)


@pytest.mark.asyncio
async def test_usage_quota_middleware_noop_without_tenant_header():
    from app.middleware import UsageQuotaMiddleware
    mw = UsageQuotaMiddleware(app=MagicMock())

    request = MagicMock()
    request.headers = {}
    call_next = AsyncMock(return_value=MagicMock())

    import app.core.usage_quota as quota_module
    real = quota_module.increment_api_calls
    quota_module.increment_api_calls = AsyncMock()
    try:
        await mw.dispatch(request, call_next)
        quota_module.increment_api_calls.assert_not_called()
    finally:
        quota_module.increment_api_calls = real


@pytest.mark.asyncio
async def test_usage_quota_middleware_does_not_break_request_on_redis_failure():
    from app.middleware import UsageQuotaMiddleware
    mw = UsageQuotaMiddleware(app=MagicMock())

    request = MagicMock()
    request.headers = {"X-Tenant-ID": "tenant-123"}
    expected_response = MagicMock()
    call_next = AsyncMock(return_value=expected_response)

    import app.core.usage_quota as quota_module
    real = quota_module.increment_api_calls
    quota_module.increment_api_calls = AsyncMock(side_effect=Exception("redis down"))
    try:
        response = await mw.dispatch(request, call_next)
    finally:
        quota_module.increment_api_calls = real

    assert response is expected_response


# ── check_limit reads live Redis count ──────────────────────────────────────

@pytest.mark.asyncio
async def test_check_limit_api_calls_uses_live_redis_count_not_stale_column():
    from app.engines.tenant_engine.service import TenantService
    tid = uuid.uuid4()
    limits = MagicMock(current_staff_count=0, max_staff=10, current_active_jobs=0,
                        max_active_jobs=20, current_api_calls_today=0,  # stale Postgres value
                        max_api_calls_per_day=100)
    result = MagicMock(); result.scalar_one_or_none.return_value = limits
    db = MagicMock(); db.execute = AsyncMock(return_value=result)
    svc = TenantService(db=db)

    import app.core.usage_quota as quota_module
    real = quota_module.get_api_calls_today
    quota_module.get_api_calls_today = AsyncMock(return_value=99)  # live Redis count, near the cap
    try:
        result = await svc.check_limit(tid, "api_calls")
    finally:
        quota_module.get_api_calls_today = real

    assert result["allowed"] is True  # 99 < 100, still allowed


@pytest.mark.asyncio
async def test_check_limit_api_calls_blocks_when_redis_count_at_cap():
    from app.engines.tenant_engine.service import TenantService
    from app.exceptions import ServiceOSException
    tid = uuid.uuid4()
    limits = MagicMock(current_staff_count=0, max_staff=10, current_active_jobs=0,
                        max_active_jobs=20, current_api_calls_today=0, max_api_calls_per_day=100)
    result = MagicMock(); result.scalar_one_or_none.return_value = limits
    db = MagicMock(); db.execute = AsyncMock(return_value=result)
    svc = TenantService(db=db)

    import app.core.usage_quota as quota_module
    real = quota_module.get_api_calls_today
    quota_module.get_api_calls_today = AsyncMock(return_value=100)  # at the cap
    try:
        with pytest.raises(ServiceOSException) as exc:
            await svc.check_limit(tid, "api_calls")
    finally:
        quota_module.get_api_calls_today = real

    assert exc.value.error_code == "PLAN_LIMIT_EXCEEDED"
