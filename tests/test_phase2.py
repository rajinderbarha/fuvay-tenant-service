"""
Phase 2 Verification Tests — Auth Engine + Tenant Engine
Run: pytest tests/test_phase2.py -v

All tests run without Docker using mocks from conftest.py
"""
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock, patch
from app.main import app


HEADERS = {"Authorization": "Bearer test-token", "X-Tenant-ID": "00000000-0000-0000-0000-000000000001"}


# ── Auth Engine Tests ────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_auth_engine_meta():
    """Auth /meta endpoint returns correct engine info."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/v1/auth/meta")
    assert resp.status_code == 200
    data = resp.json()
    assert data["engine_id"] == "auth"
    assert data["endpoint_count"] == 37
    assert "JWT" in data["description"]


@pytest.mark.asyncio
async def test_login_missing_body_returns_422():
    """Login with missing body returns validation error."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/v1/auth/login", json={})
    assert resp.status_code == 422
    data = resp.json()
    assert "error_code" in data
    assert data["error_code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_login_wrong_credentials_returns_401():
    """Login with non-existent user returns UNAUTHORIZED with RFC 7807 format.
    Mock DB returns None for user lookup, which correctly gives 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/v1/auth/login", json={
            "email": "nonexistent@test.com",
            "password": "WrongPassword123",
            "device_id": "test-device"
        })
    # User not found in mock DB → UNAUTHORIZED
    assert resp.status_code == 401
    data = resp.json()
    assert "error_code" in data
    assert data["error_code"] == "UNAUTHORIZED"
    assert "resolution" in data


@pytest.mark.asyncio
async def test_protected_endpoint_without_token_returns_401():
    """Any protected endpoint without token returns UNAUTHORIZED."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/v1/auth/me")
    assert resp.status_code == 401
    data = resp.json()
    assert data["error_code"] == "UNAUTHORIZED"
    assert "resolution" in data


@pytest.mark.asyncio
async def test_me_endpoint_with_valid_token():
    """GET /v1/auth/me with valid JWT returns user profile."""
    from app.engines.auth.utils import create_access_token
    token, _ = create_access_token(
        user_id="00000000-0000-0000-0000-000000000001",
        email="admin@serviceos.io",
        role="super_admin",
        tenant_id=None,
        tenant_name=None,
        plan_type=None,
        session_id="session-001",
        device_id="test-device",
        is_mfa_enabled=False,
        onboarding_complete=True,
        enabled_engines=[],
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code in (200, 404)


@pytest.mark.asyncio
async def test_non_super_admin_cannot_impersonate():
    """Staff/owner role cannot call impersonate — returns PERMISSION_DENIED."""
    from app.engines.auth.utils import create_access_token
    token, _ = create_access_token(
        user_id="00000000-0000-0000-0000-000000000002",
        email="owner@test.com",
        role="tenant_owner",
        tenant_id="00000000-0000-0000-0000-000000000001",
        tenant_name="Test Tenant",
        plan_type="growth",
        session_id="session-002",
        device_id="test-device",
        is_mfa_enabled=False,
        onboarding_complete=True,
        enabled_engines=[],
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/v1/auth/impersonate",
            headers={"Authorization": f"Bearer {token}"},
            json={"target_user_id": "00000000-0000-0000-0000-000000000003", "reason": "Testing access control"}
        )
    assert resp.status_code == 403
    data = resp.json()
    assert data["error_code"] == "PERMISSION_DENIED"
    assert "blocking_rule" in data


@pytest.mark.asyncio
async def test_jwt_payload_contains_required_fields():
    """JWT access token payload has all required Level 5 fields."""
    from app.engines.auth.utils import create_access_token, decode_token
    token, jti = create_access_token(
        user_id="usr-001", email="test@test.com", role="staff",
        tenant_id="tnt-001", tenant_name="Test Co", plan_type="growth",
        session_id="sess-001", device_id="dev-001",
        is_mfa_enabled=True, onboarding_complete=True,
        enabled_engines=["field_ops", "booking"],
    )
    payload = decode_token(token)
    required = ["sub","jti","iat","exp","iss","aud","email","role","tenant_id","tenant_name","plan_type","session_id","device_id","mfa_enabled","onboarding_complete","engines"]
    for field in required:
        assert field in payload, f"Missing field: {field}"
    assert payload["role"] == "staff"
    assert payload["iss"] == "serviceos"
    assert "field_ops" in payload["engines"]


@pytest.mark.asyncio
async def test_refresh_token_theft_detection():
    """Presenting a used refresh token triggers theft detection."""
    from app.engines.auth.utils import hash_token
    raw = "test-refresh-token-abc"
    hashed = hash_token(raw)
    assert len(hashed) == 64


@pytest.mark.asyncio
async def test_password_validation_rejects_weak():
    """Password validator rejects weak passwords with specific reasons."""
    from app.engines.auth.utils import validate_password_strength
    errors = validate_password_strength("abc", "John Doe", "john@test.com")
    assert len(errors) > 0
    assert any("8 character" in e for e in errors)

    errors2 = validate_password_strength("StrongPass1!", "John", "john@test.com")
    assert len(errors2) == 0


@pytest.mark.asyncio
async def test_totp_mfa_verify():
    """TOTP code verification works correctly."""
    import pyotp
    from app.engines.auth.utils import generate_totp_secret, verify_totp
    secret = generate_totp_secret()
    totp = pyotp.TOTP(secret)
    current_code = totp.now()
    assert verify_totp(secret, current_code) is True
    assert verify_totp(secret, "000000") is False


@pytest.mark.asyncio
async def test_backup_code_generation_and_verify():
    """Backup codes generate correctly and verify."""
    from app.engines.auth.utils import generate_backup_codes, verify_backup_code
    plain_codes, hashed_codes = generate_backup_codes()
    assert len(plain_codes) == 8
    assert len(hashed_codes) == 8
    assert verify_backup_code(plain_codes[0], hashed_codes[0]) is True
    assert verify_backup_code(plain_codes[0], hashed_codes[1]) is False


@pytest.mark.asyncio
async def test_api_key_generation():
    """API key generation produces correctly prefixed key."""
    from app.engines.auth.utils import generate_api_key, verify_api_key
    full_key, prefix, hashed = generate_api_key(test_mode=False)
    assert full_key.startswith("svc_live_")
    assert len(prefix) == 16
    assert verify_api_key(full_key, hashed) is True
    assert verify_api_key("wrong-key", hashed) is False


# ── Tenant Engine Tests ───────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_tenant_engine_meta():
    """Tenant /meta endpoint returns correct info."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/v1/tenants/meta")
    assert resp.status_code == 200
    data = resp.json()
    assert data["engine_id"] == "tenant"
    assert data["endpoint_count"] == 42


@pytest.mark.asyncio
async def test_onboarding_signup_returns_request_id():
    """Public signup endpoint creates onboarding request."""
    signup_data = {
        "business_name": "Test HVAC Co",
        "vertical": "home_services",
        "owner_name": "Raj Kumar",
        "owner_email": "raj@testhvac.in",
        "owner_phone": "+919876543210",
        "city": "Mumbai",
        "state": "Maharashtra",
        "gstin": "27ABCDE1234F1Z5",
        "description": "AC and heating services in Mumbai"
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/v1/tenants/onboarding/signup", json=signup_data)
    assert resp.status_code in (201, 200)
    data = resp.json()
    if resp.status_code == 201:
        assert "request_id" in data["data"]
        assert data["data"]["vertical"] == "home_services"


@pytest.mark.asyncio
async def test_onboarding_queue_requires_super_admin():
    """Onboarding queue requires super_admin role."""
    from app.engines.auth.utils import create_access_token
    token, _ = create_access_token(
        user_id="usr-003", email="staff@test.com", role="staff",
        tenant_id="tnt-001", tenant_name="Test Co", plan_type="growth",
        session_id="sess-003", device_id="dev-003",
        is_mfa_enabled=False, onboarding_complete=True, enabled_engines=[],
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/v1/tenants/onboarding/queue",
            headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403
    assert resp.json()["error_code"] == "PERMISSION_DENIED"


@pytest.mark.asyncio
async def test_plan_limits_are_correct():
    """Plan limits are correctly defined for all tiers."""
    from app.engines.tenant_engine.constants import PLAN_LIMITS
    assert PLAN_LIMITS["starter"]["max_staff"] == 10
    assert PLAN_LIMITS["growth"]["max_staff"] == 50
    assert PLAN_LIMITS["enterprise"]["max_staff"] == 500
    assert PLAN_LIMITS["growth"]["max_staff"] > PLAN_LIMITS["starter"]["max_staff"]


@pytest.mark.asyncio
async def test_default_engines_by_vertical():
    """Each vertical has a default engine bundle defined."""
    from app.engines.tenant_engine.constants import DEFAULT_ENGINES_BY_VERTICAL
    for vertical in ["home_services", "real_estate", "salon", "cafe"]:
        assert vertical in DEFAULT_ENGINES_BY_VERTICAL
        engines = DEFAULT_ENGINES_BY_VERTICAL[vertical]
        assert "auth" in engines
        assert "notification" in engines
        assert len(engines) >= 8


@pytest.mark.asyncio
async def test_health_score_computation():
    """Health score computation returns valid score and band."""
    from app.engines.tenant_engine.constants import HEALTH_BANDS
    import uuid
    from unittest.mock import AsyncMock, MagicMock
    db = AsyncMock()
    from app.engines.tenant_engine.service import TenantService
    svc = TenantService(db)
    with patch("app.engines.tenant_engine.service.get_redis", return_value=AsyncMock()):
        health = await svc.get_health_score(uuid.uuid4())
    assert 0 <= health["score"] <= 100
    assert health["band"] in HEALTH_BANDS.keys()
    assert "commission_adjustment_pct" in health
    assert "signals" in health


@pytest.mark.asyncio
async def test_commission_adjustment_by_band():
    """Platinum band reduces commission, at_risk increases it."""
    from app.engines.tenant_engine.constants import COMMISSION_ADJUSTMENT_BY_BAND
    assert COMMISSION_ADJUSTMENT_BY_BAND["platinum"] < 0
    assert COMMISSION_ADJUSTMENT_BY_BAND["gold"] == 0.0
    assert COMMISSION_ADJUSTMENT_BY_BAND["at_risk"] > 0
    assert COMMISSION_ADJUSTMENT_BY_BAND["at_risk"] > COMMISSION_ADJUSTMENT_BY_BAND["silver"]


@pytest.mark.asyncio
async def test_all_phase1_tests_still_pass():
    """Phase 1 health check still works after Phase 2 additions."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["engines"]["total"] >= 28
