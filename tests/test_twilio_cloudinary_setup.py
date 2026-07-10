"""
Twilio Verify + Cloudinary credential wiring tests.

Verifies:
  1. Twilio Verify client functions exist and have correct API endpoints
  2. is_verify_configured() reads TWILIO_VERIFY_SERVICE_SID from settings
  3. verify_send() calls Twilio Verify /Verifications with correct params
  4. verify_check() calls Twilio Verify /VerificationChecks and parses status
  5. verify_check() returns False on 404 (expired/used)
  6. Registration flow uses Twilio Verify when SID is configured
  7. Registration flow falls back to SMS OTP when Verify not configured
  8. Auth send_phone_otp uses Twilio Verify when configured
  9. Auth verify_phone_otp_login uses Twilio Verify when configured
  10. Cloudinary client builds correct upload URL and signed params
  11. Cloudinary delivery URL uses correct cloud name
  12. Cloudinary is_configured() reads all 3 env vars
"""
import hashlib
import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import uuid
import json


# ── 1. Verify client functions exist ─────────────────────────────────────────

def test_twilio_client_has_verify_send():
    from app.twilio_client import verify_send
    assert callable(verify_send)


def test_twilio_client_has_verify_check():
    from app.twilio_client import verify_check
    assert callable(verify_check)


def test_twilio_client_has_is_verify_configured():
    from app.twilio_client import is_verify_configured
    assert callable(is_verify_configured)


# ── 2. is_verify_configured reads TWILIO_VERIFY_SERVICE_SID ──────────────────

def test_is_verify_configured_true_when_all_fields_set():
    from app.twilio_client import is_verify_configured
    mock_settings = MagicMock(
        TWILIO_ACCOUNT_SID="ACxxx", TWILIO_AUTH_TOKEN="token",
        TWILIO_VERIFY_SERVICE_SID="VAxxx"
    )
    with patch("app.twilio_client.get_settings", return_value=mock_settings):
        assert is_verify_configured() is True


def test_is_verify_configured_false_when_service_sid_missing():
    from app.twilio_client import is_verify_configured
    mock_settings = MagicMock(
        TWILIO_ACCOUNT_SID="ACxxx", TWILIO_AUTH_TOKEN="token",
        TWILIO_VERIFY_SERVICE_SID=""
    )
    with patch("app.twilio_client.get_settings", return_value=mock_settings):
        assert is_verify_configured() is False


# ── 3. verify_send calls Twilio Verify API ────────────────────────────────────

@pytest.mark.asyncio
async def test_verify_send_posts_to_correct_url():
    from app.twilio_client import verify_send
    mock_settings = MagicMock(
        TWILIO_ACCOUNT_SID="ACtest", TWILIO_AUTH_TOKEN="authtoken",
        TWILIO_VERIFY_SERVICE_SID="VAtest123"
    )
    mock_resp = MagicMock(status_code=201)
    mock_resp.json.return_value = {"status": "pending", "sid": "VExx"}

    captured = {}
    class FakeAsyncClient:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def post(self, url, **kwargs):
            captured["url"] = url
            captured["data"] = kwargs.get("data", {})
            return mock_resp

    with patch("app.twilio_client.get_settings", return_value=mock_settings), \
         patch("app.twilio_client.httpx.AsyncClient", FakeAsyncClient):
        result = await verify_send("+919876543210")

    assert result is True
    assert "VAtest123/Verifications" in captured["url"]
    assert captured["data"]["To"] == "+919876543210"
    assert captured["data"]["Channel"] == "sms"


# ── 4. verify_check parses "approved" status ──────────────────────────────────

@pytest.mark.asyncio
async def test_verify_check_returns_true_when_approved():
    from app.twilio_client import verify_check
    mock_settings = MagicMock(
        TWILIO_ACCOUNT_SID="ACtest", TWILIO_AUTH_TOKEN="authtoken",
        TWILIO_VERIFY_SERVICE_SID="VAtest123"
    )
    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = {"status": "approved", "to": "+919876543210"}

    class FakeAsyncClient:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def post(self, url, **kwargs):
            return mock_resp

    with patch("app.twilio_client.get_settings", return_value=mock_settings), \
         patch("app.twilio_client.httpx.AsyncClient", FakeAsyncClient):
        result = await verify_check("+919876543210", "123456")

    assert result is True


@pytest.mark.asyncio
async def test_verify_check_returns_false_when_pending():
    from app.twilio_client import verify_check
    mock_settings = MagicMock(
        TWILIO_ACCOUNT_SID="ACtest", TWILIO_AUTH_TOKEN="authtoken",
        TWILIO_VERIFY_SERVICE_SID="VAtest123"
    )
    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = {"status": "pending"}

    class FakeAsyncClient:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def post(self, url, **kwargs):
            return mock_resp

    with patch("app.twilio_client.get_settings", return_value=mock_settings), \
         patch("app.twilio_client.httpx.AsyncClient", FakeAsyncClient):
        result = await verify_check("+919876543210", "000000")

    assert result is False


# ── 5. verify_check returns False on 404 (expired/used) ──────────────────────

@pytest.mark.asyncio
async def test_verify_check_returns_false_on_404():
    from app.twilio_client import verify_check
    mock_settings = MagicMock(
        TWILIO_ACCOUNT_SID="ACtest", TWILIO_AUTH_TOKEN="authtoken",
        TWILIO_VERIFY_SERVICE_SID="VAtest123"
    )
    mock_resp = MagicMock(status_code=404)

    class FakeAsyncClient:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def post(self, url, **kwargs):
            return mock_resp

    with patch("app.twilio_client.get_settings", return_value=mock_settings), \
         patch("app.twilio_client.httpx.AsyncClient", FakeAsyncClient):
        result = await verify_check("+919876543210", "expired_code")

    assert result is False


# ── 6. Registration flow uses Twilio Verify when configured ──────────────────

@pytest.mark.asyncio
async def test_registration_initiate_uses_twilio_verify_when_configured():
    from app.engines.public_registration.router import InitiateRequest, initiate_registration

    req = InitiateRequest(
        business_name="Test Biz", owner_name="Test", owner_email="t@b.io",
        owner_phone="+919999999999", vertical="home_services",
        city="Mumbai", country="India", zipcode="400001", plan_type="growth",
    )

    saved_session: dict = {}
    redis = MagicMock()
    async def fake_setex(key, ttl, data):
        saved_session.update(json.loads(data))
    redis.setex = fake_setex

    r = MagicMock(); r.state = MagicMock(request_id="t")

    with patch("app.engines.public_registration.router.is_verify_configured", return_value=True), \
         patch("app.engines.public_registration.router.verify_send", new_callable=AsyncMock, return_value=True):
        await initiate_registration(req, r, redis=redis)

    assert saved_session["use_verify"] is True
    assert saved_session["otp"] is None  # no fallback OTP stored


# ── 7. Registration falls back to SMS OTP when Verify not configured ──────────

@pytest.mark.asyncio
async def test_registration_initiate_falls_back_to_sms_otp():
    from app.engines.public_registration.router import InitiateRequest, initiate_registration

    req = InitiateRequest(
        business_name="Test Biz", owner_name="Test", owner_email="t@b.io",
        owner_phone="+919999999999", vertical="home_services",
        city="Mumbai", country="India", zipcode="400001", plan_type="growth",
    )

    saved_session: dict = {}
    redis = MagicMock()
    async def fake_setex(key, ttl, data):
        saved_session.update(json.loads(data))
    redis.setex = fake_setex

    r = MagicMock(); r.state = MagicMock(request_id="t")

    with patch("app.engines.public_registration.router.is_verify_configured", return_value=False), \
         patch("app.engines.public_registration.router.send_sms", new_callable=AsyncMock, return_value=True):
        await initiate_registration(req, r, redis=redis)

    assert saved_session["use_verify"] is False
    assert saved_session["otp"] is not None  # fallback OTP stored
    assert len(saved_session["otp"]) == 6


# ── 8. Auth send_phone_otp uses Twilio Verify when configured ────────────────

@pytest.mark.asyncio
async def test_auth_send_phone_otp_uses_twilio_verify():
    from app.engines.auth.service import AuthService
    db = MagicMock(); db.add = MagicMock()
    svc = AuthService(db=db)

    with patch("app.twilio_client.is_verify_configured", return_value=True), \
         patch("app.twilio_client.verify_send", new_callable=AsyncMock, return_value=True):
        result = await svc.send_phone_otp("+919999999999", "phone_login")

    assert result["use_verify"] is True
    db.add.assert_not_called()  # no OTPRecord added when using Twilio Verify


# ── 9. Auth verify_phone_otp_login uses Twilio Verify when configured ─────────

@pytest.mark.asyncio
async def test_auth_verify_phone_otp_login_uses_twilio_verify():
    from app.engines.auth.service import AuthService
    from app.exceptions import ServiceOSException

    db = MagicMock()
    svc = AuthService(db=db)

    with patch("app.twilio_client.is_verify_configured", return_value=True), \
         patch("app.twilio_client.verify_check", new_callable=AsyncMock, return_value=False):
        with pytest.raises(ServiceOSException) as exc:
            await svc.verify_phone_otp_login(
                "+919999999999", "wrong_code", "dev1", None, None
            )
    assert exc.value.error_code == "UNAUTHORIZED"


# ── 10. Cloudinary builds correct upload URL ──────────────────────────────────

def test_cloudinary_build_upload_params_correct_url():
    from app.cloudinary_client import build_upload_params
    mock_settings = MagicMock(
        CLOUDINARY_CLOUD_NAME="dr1b4ezct",
        CLOUDINARY_API_KEY="468629114443996",
        CLOUDINARY_API_SECRET="gJDsgFpcKmIsamUmKbmVs5BTPJc",
    )
    with patch("app.cloudinary_client.get_settings", return_value=mock_settings):
        params = build_upload_params("media/test123", folder="tenants/abc")

    assert params["upload_url"] == "https://api.cloudinary.com/v1_1/dr1b4ezct/auto/upload"
    assert params["api_key"] == "468629114443996"
    assert "signature" in params
    assert "timestamp" in params


def test_cloudinary_signature_is_sha1_of_sorted_params():
    """Verify the signing algorithm matches Cloudinary's documented spec."""
    from app.cloudinary_client import build_upload_params
    api_secret = "gJDsgFpcKmIsamUmKbmVs5BTPJc"
    mock_settings = MagicMock(
        CLOUDINARY_CLOUD_NAME="dr1b4ezct",
        CLOUDINARY_API_KEY="468629114443996",
        CLOUDINARY_API_SECRET=api_secret,
    )
    with patch("app.cloudinary_client.get_settings", return_value=mock_settings), \
         patch("app.cloudinary_client.time.time", return_value=1700000000):
        params = build_upload_params("img/test")

    expected_str = f"public_id=img/test&timestamp=1700000000{api_secret}"
    expected_sig = hashlib.sha1(expected_str.encode()).hexdigest()
    assert params["signature"] == expected_sig


# ── 11. Cloudinary delivery URL ───────────────────────────────────────────────

def test_cloudinary_delivery_url_format():
    from app.cloudinary_client import build_delivery_url
    mock_settings = MagicMock(CLOUDINARY_CLOUD_NAME="dr1b4ezct")
    with patch("app.cloudinary_client.get_settings", return_value=mock_settings):
        url = build_delivery_url("tenants/abc/photo.jpg", resource_type="image")
    assert url == "https://res.cloudinary.com/dr1b4ezct/image/upload/tenants/abc/photo.jpg"


# ── 12. Cloudinary is_configured reads all 3 env vars ────────────────────────

def test_cloudinary_is_configured_false_when_secret_missing():
    from app.cloudinary_client import is_configured
    mock_settings = MagicMock(
        CLOUDINARY_CLOUD_NAME="dr1b4ezct", CLOUDINARY_API_KEY="468629114443996",
        CLOUDINARY_API_SECRET="",  # missing
    )
    with patch("app.cloudinary_client.get_settings", return_value=mock_settings):
        assert is_configured() is False


def test_cloudinary_is_configured_true_when_all_set():
    from app.cloudinary_client import is_configured
    mock_settings = MagicMock(
        CLOUDINARY_CLOUD_NAME="dr1b4ezct", CLOUDINARY_API_KEY="468629114443996",
        CLOUDINARY_API_SECRET="gJDsgFpcKmIsamUmKbmVs5BTPJc",
    )
    with patch("app.cloudinary_client.get_settings", return_value=mock_settings):
        assert is_configured() is True
