"""
Phase 14 — Tenant Self-Registration.

Tests the full self-serve onboarding flow:
  initiate → verify OTP → create Razorpay payment order → complete registration

Key contracts verified:
  1. country, city, zipcode are now required fields (schema validation)
  2. /verify marks the session as verified but does NOT create a tenant
  3. /payment-order rejects un-verified sessions (OTP must come first)
  4. /complete verifies Razorpay signature, creates Tenant + User +
     TenantLimits + Subscription, and returns credentials
  5. Duplicate email on /complete returns REGISTRATION_DUPLICATE
  6. Razorpay signature failure returns PAYMENT_SIGNATURE_INVALID
  7. OTP max-attempts invalidates the session
  8. Tenant model now has zipcode field
  9. /complete sets tenant.status = "trial" and trial_expires_at
  10. TenantLimits seeded from PLAN_LIMITS for chosen plan
"""
import uuid
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ── 1. Schema — country and zipcode are required ──────────────────────────────

def test_initiate_request_requires_country():
    from app.engines.public_registration.router import InitiateRequest
    from pydantic import ValidationError
    with pytest.raises(ValidationError) as exc:
        InitiateRequest(
            business_name="Rahul AC", owner_name="Rahul", owner_email="r@b.io",
            owner_phone="+919999999999", vertical="home_services",
            city="Mumbai", zipcode="400001",
            # country missing
        )
    assert "country" in str(exc.value).lower()


def test_initiate_request_requires_zipcode():
    from app.engines.public_registration.router import InitiateRequest
    from pydantic import ValidationError
    with pytest.raises(ValidationError) as exc:
        InitiateRequest(
            business_name="Rahul AC", owner_name="Rahul", owner_email="r@b.io",
            owner_phone="+919999999999", vertical="home_services",
            city="Mumbai", country="India",
            # zipcode missing
        )
    assert "zipcode" in str(exc.value).lower()


def test_initiate_request_requires_city():
    from app.engines.public_registration.router import InitiateRequest
    from pydantic import ValidationError
    with pytest.raises(ValidationError) as exc:
        InitiateRequest(
            business_name="Rahul AC", owner_name="Rahul", owner_email="r@b.io",
            owner_phone="+919999999999", vertical="home_services",
            country="India", zipcode="400001",
            # city missing
        )
    assert "city" in str(exc.value).lower()


def test_initiate_request_state_is_optional():
    from app.engines.public_registration.router import InitiateRequest
    req = InitiateRequest(
        business_name="Rahul AC", owner_name="Rahul", owner_email="r@b.io",
        owner_phone="+919999999999", vertical="home_services",
        city="Mumbai", country="India", zipcode="400001",
    )
    assert req.state is None


# ── 2. Session stores country, zipcode, state ─────────────────────────────────

@pytest.mark.asyncio
async def test_initiate_stores_country_and_zipcode_in_session():
    from app.engines.public_registration.router import InitiateRequest

    req = InitiateRequest(
        business_name="Rahul AC", owner_name="Rahul", owner_email="r@b.io",
        owner_phone="+919999999999", vertical="home_services",
        city="Mumbai", country="India", zipcode="400001", state="Maharashtra",
        plan_type="growth",
    )

    captured_data: dict = {}

    redis = MagicMock()
    async def fake_setex(key, ttl, data):
        captured_data.update(json.loads(data))
    redis.setex = fake_setex

    with patch("app.engines.public_registration.router.send_sms", return_value=True):
        from app.engines.public_registration.router import initiate_registration
        r = MagicMock(); r.state = MagicMock(request_id="test")
        await initiate_registration(req, r, redis=redis)

    assert captured_data["country"] == "India"
    assert captured_data["zipcode"] == "400001"
    assert captured_data["state"]   == "Maharashtra"
    assert captured_data["verified"] is False


# ── 3. /verify does NOT create a tenant ───────────────────────────────────────

@pytest.mark.asyncio
async def test_verify_marks_session_verified_but_does_not_create_tenant():
    from app.engines.public_registration.router import VerifyRequest, verify_otp

    session = {
        "business_name": "Rahul AC", "owner_name": "Rahul", "owner_email": "r@b.io",
        "owner_phone": "+919999999999", "vertical": "home_services",
        "city": "Mumbai", "country": "India", "zipcode": "400001", "state": None,
        "plan_type": "growth", "otp": "123456", "otp_attempts": 0,
        "verified": False, "payment_order_id": None, "payment_completed": False,
    }

    saved: dict = {}
    redis = MagicMock()
    redis.get = AsyncMock(return_value=json.dumps(session).encode())
    async def fake_setex(key, ttl, data):
        saved.update(json.loads(data))
    redis.setex = fake_setex

    req = VerifyRequest(session_id="reg_test", otp="123456")
    r = MagicMock(); r.state = MagicMock(request_id="test")

    result = await verify_otp(req, r, redis=redis)

    assert saved.get("verified") is True
    # No DB argument passed → no tenant was created
    assert result.data["verified"] is True
    assert result.data["session_id"] == "reg_test"


# ── 4. /payment-order rejects un-verified session ────────────────────────────

@pytest.mark.asyncio
async def test_payment_order_rejects_if_otp_not_verified():
    from app.engines.public_registration.router import PaymentOrderRequest, create_payment_order
    from app.exceptions import ServiceOSException

    session = {"verified": False, "plan_type": "growth", "business_name": "X",
               "owner_name": "X", "owner_email": "x@x.com", "owner_phone": "1234567890"}
    redis = MagicMock()
    redis.get = AsyncMock(return_value=json.dumps(session).encode())

    req = PaymentOrderRequest(session_id="reg_test")
    r = MagicMock(); r.state = MagicMock(request_id="test")

    with pytest.raises(ServiceOSException) as exc:
        await create_payment_order(req, r, redis=redis)
    assert exc.value.error_code == "OTP_NOT_VERIFIED"


@pytest.mark.asyncio
async def test_payment_order_creates_razorpay_order_for_verified_session():
    from app.engines.public_registration.router import PaymentOrderRequest, create_payment_order

    session = {
        "verified": True, "plan_type": "starter",
        "business_name": "Rahul AC", "owner_name": "Rahul",
        "owner_email": "r@b.io", "owner_phone": "+91999",
    }
    saved: dict = {}
    redis = MagicMock()
    redis.get = AsyncMock(return_value=json.dumps(session).encode())
    async def fake_setex(key, ttl, data):
        saved.update(json.loads(data))
    redis.setex = fake_setex

    fake_order = {"id": "order_abc123", "amount": 99900, "currency": "INR", "status": "created", "receipt": "x"}

    with patch("app.engines.public_registration.router.razorpay_create_order",
               return_value=fake_order):
        req = PaymentOrderRequest(session_id="reg_test")
        r = MagicMock(); r.state = MagicMock(request_id="test")
        result = await create_payment_order(req, r, redis=redis)

    assert result.data["order_id"] == "order_abc123"
    assert result.data["amount_inr"] == 999  # starter plan price
    assert saved["payment_order_id"] == "order_abc123"


# ── 5. /complete — Razorpay signature failure ─────────────────────────────────

@pytest.mark.asyncio
async def test_complete_rejects_invalid_razorpay_signature():
    from app.engines.public_registration.router import CompleteRequest, complete_registration
    from app.exceptions import ServiceOSException

    session = {
        "verified": True, "payment_completed": False, "plan_type": "growth",
        "business_name": "X", "owner_name": "X", "owner_email": "x@x.com",
        "owner_phone": "9999", "vertical": "home_services",
        "city": "Mumbai", "country": "India", "zipcode": "400001", "state": None,
    }
    redis = MagicMock()
    redis.get = AsyncMock(return_value=json.dumps(session).encode())
    db = MagicMock()

    with patch("app.engines.public_registration.router.verify_payment_signature", return_value=False):
        req = CompleteRequest(session_id="reg_test",
            razorpay_order_id="order_x", razorpay_payment_id="pay_x",
            razorpay_signature="bad_sig")
        r = MagicMock(); r.state = MagicMock(request_id="test")

        with pytest.raises(ServiceOSException) as exc:
            await complete_registration(req, r, db=db, redis=redis)
        assert exc.value.error_code == "PAYMENT_SIGNATURE_INVALID"


# ── 6. /complete creates tenant with zipcode + TenantLimits + Subscription ───

@pytest.mark.asyncio
async def test_complete_creates_tenant_with_country_and_zipcode():
    from app.engines.public_registration.router import CompleteRequest, complete_registration

    session = {
        "verified": True, "payment_completed": False, "plan_type": "starter",
        "business_name": "Rahul AC", "owner_name": "Rahul", "owner_email": "r@b.io",
        "owner_phone": "+91999", "vertical": "home_services",
        "city": "Mumbai", "country": "India", "zipcode": "400001", "state": "Maharashtra",
        "billing_cycle": "monthly",
    }
    redis = MagicMock()
    redis.get = AsyncMock(return_value=json.dumps(session).encode())
    redis.delete = AsyncMock()

    added_objects = []
    db = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()

    no_user_result = MagicMock(); no_user_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=no_user_result)

    def fake_add(obj):
        added_objects.append(obj)
        if hasattr(obj, "id") and obj.id is None:
            obj.id = uuid.uuid4()
    db.add = MagicMock(side_effect=fake_add)

    sub_mock = AsyncMock()
    sub_mock.return_value = {"plan_type": "starter", "status": "trialing"}

    with patch("app.engines.public_registration.router.verify_payment_signature", return_value=True), \
         patch("app.engines.public_registration.router.send_email", return_value=True), \
         patch("app.engines.public_registration.router.send_sms", return_value=True), \
         patch("app.engines.subscription.service.SubscriptionService.create_subscription", sub_mock):

        req = CompleteRequest(session_id="reg_test",
            razorpay_order_id="order_x", razorpay_payment_id="pay_x",
            razorpay_signature="valid_sig")
        r = MagicMock(); r.state = MagicMock(request_id="test")

        result = await complete_registration(req, r, db=db, redis=redis)

    # Verify Tenant was added
    from app.engines.tenant_engine.models import Tenant, TenantLimits
    tenant_obj = next((o for o in added_objects if isinstance(o, Tenant)), None)
    assert tenant_obj is not None
    assert tenant_obj.country == "India"
    assert tenant_obj.zipcode == "400001"
    assert tenant_obj.city    == "Mumbai"
    assert tenant_obj.status  == "trial"
    assert tenant_obj.trial_expires_at is not None

    # Verify TenantLimits was added
    limits_obj = next((o for o in added_objects if isinstance(o, TenantLimits)), None)
    assert limits_obj is not None
    assert limits_obj.max_staff == 10  # starter plan

    # Verify response
    assert result.data["business_name"] == "Rahul AC"
    assert result.data["plan_type"]     == "starter"
    assert result.data["trial_days"]    == 14  # starter = 14 days
    assert "temp_password" in result.data


# ── 7. /complete blocks duplicate email ───────────────────────────────────────

@pytest.mark.asyncio
async def test_complete_blocks_duplicate_email():
    from app.engines.public_registration.router import CompleteRequest, complete_registration
    from app.exceptions import ServiceOSException
    from app.engines.auth.models import User

    session = {
        "verified": True, "payment_completed": False, "plan_type": "growth",
        "business_name": "X", "owner_name": "X", "owner_email": "dup@b.io",
        "owner_phone": "9999", "vertical": "home_services",
        "city": "Mumbai", "country": "India", "zipcode": "400001", "state": None,
    }
    redis = MagicMock()
    redis.get = AsyncMock(return_value=json.dumps(session).encode())
    redis.delete = AsyncMock()

    existing_user = MagicMock(spec=User)
    result = MagicMock(); result.scalar_one_or_none.return_value = existing_user
    db = MagicMock(); db.execute = AsyncMock(return_value=result)

    with patch("app.engines.public_registration.router.verify_payment_signature", return_value=True):
        req = CompleteRequest(session_id="reg_test",
            razorpay_order_id="order_x", razorpay_payment_id="pay_x",
            razorpay_signature="valid_sig")
        r = MagicMock(); r.state = MagicMock(request_id="test")

        with pytest.raises(ServiceOSException) as exc:
            await complete_registration(req, r, db=db, redis=redis)
        assert exc.value.error_code == "REGISTRATION_DUPLICATE"


# ── 8. /complete blocks already-completed sessions ───────────────────────────

@pytest.mark.asyncio
async def test_complete_blocks_session_used_twice():
    from app.engines.public_registration.router import CompleteRequest, complete_registration
    from app.exceptions import ServiceOSException

    session = {
        "verified": True, "payment_completed": True,  # already done
        "plan_type": "growth", "business_name": "X", "owner_name": "X",
        "owner_email": "x@x.com", "owner_phone": "9999",
    }
    redis = MagicMock()
    redis.get = AsyncMock(return_value=json.dumps(session).encode())
    db = MagicMock()

    with patch("app.engines.public_registration.router.verify_payment_signature", return_value=True):
        req = CompleteRequest(session_id="reg_test",
            razorpay_order_id="order_x", razorpay_payment_id="pay_x",
            razorpay_signature="valid")
        r = MagicMock(); r.state = MagicMock(request_id="test")

        with pytest.raises(ServiceOSException) as exc:
            await complete_registration(req, r, db=db, redis=redis)
        assert exc.value.error_code == "REGISTRATION_DUPLICATE"


# ── 9. OTP max-attempts deletes the session ──────────────────────────────────

@pytest.mark.asyncio
async def test_otp_max_attempts_deletes_session():
    from app.engines.public_registration.router import VerifyRequest, verify_otp
    from app.exceptions import ServiceOSException

    session = {
        "otp": "111111", "otp_attempts": 5, "verified": False,
        "plan_type": "growth", "business_name": "X",
    }
    redis = MagicMock()
    redis.get = AsyncMock(return_value=json.dumps(session).encode())
    redis.delete = AsyncMock()

    req = VerifyRequest(session_id="reg_test", otp="999999")
    r = MagicMock(); r.state = MagicMock(request_id="test")

    with pytest.raises(ServiceOSException) as exc:
        await verify_otp(req, r, redis=redis)

    assert exc.value.error_code == "OTP_MAX_ATTEMPTS"
    redis.delete.assert_called_once()


# ── 10. Tenant model has zipcode field ───────────────────────────────────────

def test_tenant_model_has_zipcode_field():
    from app.engines.tenant_engine.models import Tenant
    t = Tenant(
        tenant_name="Test", vertical="home_services", country="India",
        city="Mumbai", zipcode="400001",
    )
    assert t.zipcode == "400001"


# ── 11. Plan trial days match constants ───────────────────────────────────────

def test_trial_days_per_plan():
    from app.engines.tenant_engine.constants import TRIAL_DAYS
    assert TRIAL_DAYS["starter"]    == 14
    assert TRIAL_DAYS["growth"]     == 30
    assert TRIAL_DAYS["enterprise"] == 60


# ── 12. TenantLimits seeded from correct plan ────────────────────────────────

def test_plan_limits_growth_has_50_staff():
    from app.engines.tenant_engine.constants import PLAN_LIMITS
    assert PLAN_LIMITS["growth"]["max_staff"] == 50
    assert PLAN_LIMITS["enterprise"]["max_staff"] == 500
