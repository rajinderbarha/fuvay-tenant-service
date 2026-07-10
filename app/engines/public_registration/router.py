"""
Public Registration Engine — Router
Allows any home service business to self-register without admin involvement.
No auth required on these endpoints.

Flow:
  POST /v1/public/register/initiate      → validate + send OTP → returns session_id
  POST /v1/public/register/confirm-plan  → update plan in session
  POST /v1/public/register/verify        → verify OTP → marks session verified (no tenant created yet)
  POST /v1/public/register/payment-order → create Razorpay order for the selected plan
  POST /v1/public/register/complete      → verify Razorpay payment → create tenant + subscription + limits
  POST /v1/public/register/webhook/razorpay → Razorpay server-to-server payment events
"""
from __future__ import annotations
import secrets
import uuid
import json
from datetime import datetime, timezone, timedelta

import structlog
from fastapi import APIRouter, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import Depends

from app.config import get_settings
settings = get_settings()
from app.dependencies.db import get_db
from app.exceptions import ServiceOSException
from app.schemas.base import ApiResponse, ok
from app.redis_client import get_redis
from app.engines.auth.utils import hash_password
from app.engines.tenant_engine.models import Tenant, TenantLimits
from app.engines.tenant_engine.constants import PLAN_LIMITS, TRIAL_DAYS
from app.engines.auth.models import User
from app.twilio_client import send_sms, verify_send, verify_check, is_verify_configured
from app.email_client import send_email
from app.integrations.razorpay_client import (
    create_order as razorpay_create_order,
    verify_payment_signature,
    verify_webhook_signature,
)

logger = structlog.get_logger("public_registration")
router = APIRouter(prefix="/v1/public", tags=["Public Registration"])

OTP_TTL_SECONDS     = 600    # 10 minutes
SESSION_TTL_SECONDS = 1800   # 30 minutes
MAX_OTP_ATTEMPTS    = 5

VALID_VERTICALS = ["home_services"]
VALID_PLANS     = ["starter", "growth", "enterprise"]

# Plan prices in INR — single source of truth for registration flow
PLAN_PRICES_INR = {"starter": 999, "growth": 2499, "enterprise": 7999}


# ── Schemas ───────────────────────────────────────────────────────────────────

class InitiateRequest(BaseModel):
    business_name: str      = Field(..., min_length=2, max_length=200)
    owner_name:    str      = Field(..., min_length=2, max_length=200)
    owner_email:   EmailStr
    owner_phone:   str      = Field(..., min_length=10, max_length=20)
    vertical:      str      = Field(..., pattern="^[a-z_]+$")
    city:          str      = Field(..., min_length=2, max_length=100)
    country:       str      = Field(..., min_length=2, max_length=50)
    zipcode:       str      = Field(..., min_length=3, max_length=20)
    state:         str | None = Field(default=None, max_length=100)
    plan_type:     str      = Field(default="growth")


class ConfirmPlanRequest(BaseModel):
    session_id:          str
    plan_type:           str = Field(..., pattern="^(starter|growth|enterprise)$")
    selected_package_id: str | None = None  # P1: new-style package ID from /v1/public/packages


class VerifyRequest(BaseModel):
    session_id: str
    otp:        str = Field(..., min_length=4, max_length=8)


class PaymentOrderRequest(BaseModel):
    session_id:     str
    billing_cycle:  str = Field(default="monthly", pattern="^(monthly|annual)$")


class CompleteRequest(BaseModel):
    session_id:          str
    razorpay_order_id:   str
    razorpay_payment_id: str
    razorpay_signature:  str
    selected_package_id: str | None = None  # P1: package selected during signup


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_session(redis, session_id: str) -> dict:
    raw = await redis.get(f"reg:session:{session_id}")
    if not raw:
        raise ServiceOSException(
            "SESSION_EXPIRED",
            "Registration session expired. Please start over.",
            status_code=400,
        )
    return json.loads(raw)


async def _save_session(redis, session_id: str, data: dict) -> None:
    await redis.setex(f"reg:session:{session_id}", SESSION_TTL_SECONDS, json.dumps(data))


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post(
    "/register/initiate",
    response_model=ApiResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Initiate tenant registration — validates details, sends OTP (public)",
)
async def initiate_registration(
    body: InitiateRequest,
    r: Request,
    redis=Depends(get_redis),
):
    if body.vertical not in VALID_VERTICALS:
        raise ServiceOSException(
            "INVALID_VERTICAL",
            f"Vertical must be one of: {', '.join(VALID_VERTICALS)}",
            status_code=422,
        )
    if body.plan_type not in VALID_PLANS:
        body.plan_type = "growth"

    session_id = f"reg_{secrets.token_urlsafe(24)}"

    # Prefer Twilio Verify (OTP managed by Twilio); fall back to self-generated OTP via plain SMS
    use_verify = is_verify_configured()
    fallback_otp: str | None = None

    if use_verify:
        sent = await verify_send(body.owner_phone)
        if not sent:
            # Twilio Verify call failed — drop to SMS fallback
            use_verify = False

    if not use_verify:
        fallback_otp = str(secrets.randbelow(900000) + 100000)
        sent = await send_sms(body.owner_phone,
            f"Your ServiceOS verification code is {fallback_otp}. Valid for 10 minutes.")

    session_data = {
        "business_name": body.business_name,
        "owner_name":    body.owner_name,
        "owner_email":   body.owner_email,
        "owner_phone":   body.owner_phone,
        "vertical":      body.vertical,
        "city":          body.city,
        "country":       body.country,
        "zipcode":       body.zipcode,
        "state":         body.state,
        "plan_type":     body.plan_type,
        # use_verify=True means Twilio manages the OTP; fallback_otp is None
        "use_verify":       use_verify,
        "otp":              fallback_otp,   # None when Twilio Verify is active
        "otp_attempts":     0,
        "verified":         False,
        "payment_order_id": None,
        "payment_completed": False,
    }
    await _save_session(redis, session_id, session_data)

    logger.info("registration.otp_sent", phone=body.owner_phone[:4] + "****",
                session_id=session_id, method="twilio_verify" if use_verify else "sms_fallback",
                dev_otp=fallback_otp if (settings.DEBUG and fallback_otp) else "hidden")

    response_data = {"session_id": session_id, "message": f"OTP sent to {body.owner_phone[:4]}XXXXXX"}
    if settings.DEBUG and fallback_otp:
        response_data["dev_otp"] = fallback_otp

    return ok(response_data, getattr(r.state, "request_id", "—"), engine_id="public_registration")


@router.post(
    "/register/confirm-plan",
    response_model=ApiResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Update plan selection before OTP verification (public)",
)
async def confirm_plan(
    body: ConfirmPlanRequest,
    r: Request,
    redis=Depends(get_redis),
):
    session = await _get_session(redis, body.session_id)
    session["plan_type"] = body.plan_type
    if body.selected_package_id:
        session["selected_package_id"] = body.selected_package_id
    await _save_session(redis, body.session_id, session)
    return ok(
        {"plan_type": body.plan_type, "price_inr": PLAN_PRICES_INR.get(body.plan_type)},
        getattr(r.state, "request_id", "—"), engine_id="public_registration",
    )


@router.post(
    "/register/verify",
    response_model=ApiResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Verify OTP — marks session as verified, no tenant created yet (public)",
)
async def verify_otp(
    body: VerifyRequest,
    r: Request,
    redis=Depends(get_redis),
):
    session = await _get_session(redis, body.session_id)

    use_verify = session.get("use_verify", False)

    if use_verify:
        # Twilio Verify — delegate OTP check to Twilio
        approved = await verify_check(session["owner_phone"], body.otp)
        if not approved:
            session["otp_attempts"] = session.get("otp_attempts", 0) + 1
            await _save_session(redis, body.session_id, session)
            remaining = max(0, MAX_OTP_ATTEMPTS - session["otp_attempts"])
            raise ServiceOSException(
                "INVALID_OTP",
                f"Incorrect or expired OTP. {remaining} attempts remaining.",
                status_code=400,
            )
    else:
        # Fallback: self-managed OTP stored in Redis session
        session["otp_attempts"] = session.get("otp_attempts", 0) + 1
        if session["otp_attempts"] > MAX_OTP_ATTEMPTS:
            await redis.delete(f"reg:session:{body.session_id}")
            raise ServiceOSException(
                "OTP_MAX_ATTEMPTS",
                "Too many incorrect attempts. Please register again.",
                status_code=429,
            )
        if body.otp != session.get("otp"):
            await _save_session(redis, body.session_id, session)
            raise ServiceOSException(
                "INVALID_OTP",
                f"Incorrect OTP. {MAX_OTP_ATTEMPTS - session['otp_attempts']} attempts remaining.",
                status_code=400,
            )

    session["verified"] = True
    await _save_session(redis, body.session_id, session)

    logger.info("registration.otp_verified", session_id=body.session_id,
                business=session["business_name"])

    return ok(
        {
            "session_id":    body.session_id,
            "verified":      True,
            "business_name": session["business_name"],
            "plan_type":     session["plan_type"],
            "price_inr":     PLAN_PRICES_INR.get(session["plan_type"]),
        },
        getattr(r.state, "request_id", "—"), engine_id="public_registration",
    )


@router.post(
    "/register/payment-order",
    response_model=ApiResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Create Razorpay payment order for the selected plan (public)",
)
async def create_payment_order(
    body: PaymentOrderRequest,
    r: Request,
    redis=Depends(get_redis),
):
    session = await _get_session(redis, body.session_id)

    if not session.get("verified"):
        raise ServiceOSException(
            "OTP_NOT_VERIFIED",
            "Phone number must be verified before payment.",
            status_code=400,
        )

    plan_type     = session["plan_type"]
    amount_rupees = PLAN_PRICES_INR.get(plan_type, 999)
    receipt       = f"reg_{body.session_id[:16]}"

    order = await razorpay_create_order(
        amount_rupees=amount_rupees,
        receipt=receipt,
        notes={
            "business_name": session["business_name"],
            "owner_email":   session["owner_email"],
            "plan_type":     plan_type,
            "session_id":    body.session_id,
        },
    )

    session["payment_order_id"]    = order["id"]
    session["billing_cycle"]       = body.billing_cycle
    await _save_session(redis, body.session_id, session)

    logger.info("registration.payment_order_created", order_id=order["id"],
                plan=plan_type, amount_rupees=amount_rupees)

    return ok(
        {
            "order_id":    order["id"],
            "amount":      order["amount"],   # in paise
            "amount_inr":  amount_rupees,
            "currency":    "INR",
            "key_id":      settings.RAZORPAY_KEY_ID,
            "prefill": {
                "name":  session["owner_name"],
                "email": session["owner_email"],
                "contact": session["owner_phone"],
            },
        },
        getattr(r.state, "request_id", "—"), engine_id="public_registration",
    )


@router.post(
    "/register/complete",
    response_model=ApiResponse[dict],
    status_code=status.HTTP_201_CREATED,
    summary="Complete registration — verify payment, create tenant + subscription (public)",
)
async def complete_registration(
    body: CompleteRequest,
    r: Request,
    db:    AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    session = await _get_session(redis, body.session_id)

    if not session.get("verified"):
        raise ServiceOSException("OTP_NOT_VERIFIED",
            "Phone number must be verified before completing registration.", status_code=400)

    if session.get("payment_completed"):
        raise ServiceOSException("REGISTRATION_DUPLICATE",
            "This registration has already been completed.", status_code=409)

    # Verify Razorpay payment signature
    if not verify_payment_signature(body.razorpay_order_id,
                                     body.razorpay_payment_id,
                                     body.razorpay_signature):
        raise ServiceOSException("PAYMENT_SIGNATURE_INVALID",
            "Payment could not be verified. Please contact support.", status_code=400)

    # Check for duplicate email
    existing = await db.execute(
        select(User).where(User.email == session["owner_email"])
    )
    if existing.scalar_one_or_none():
        await redis.delete(f"reg:session:{body.session_id}")
        raise ServiceOSException("REGISTRATION_DUPLICATE",
            "An account with this email already exists. Please log in.", status_code=409)

    plan_type     = session["plan_type"]
    billing_cycle = session.get("billing_cycle", "monthly")
    trial_days    = TRIAL_DAYS.get(plan_type, 14)
    temp_password = secrets.token_urlsafe(9)
    utcnow        = lambda: datetime.now(timezone.utc)

    try:
        # 1. Create tenant
        tenant = Tenant(
            tenant_name  = session["business_name"],
            vertical     = session["vertical"],
            city         = session["city"],
            state        = session.get("state"),
            country      = session["country"],
            zipcode      = session["zipcode"],
            status       = "trial",
            plan_type    = plan_type,
            trial_expires_at = utcnow() + timedelta(days=trial_days),
        )
        db.add(tenant)
        await db.flush()

        # 2. Create owner user
        owner = User(
            tenant_id            = tenant.id,
            email                = session["owner_email"],
            phone                = session["owner_phone"],
            full_name            = session["owner_name"],
            role                 = "tenant_owner",
            hashed_password      = hash_password(temp_password),
            is_active            = True,
            force_password_change = True,
        )
        db.add(owner)
        await db.flush()
        tenant.owner_user_id = owner.id

        # 3. Seed TenantLimits from plan
        limits_cfg = PLAN_LIMITS.get(plan_type, PLAN_LIMITS["starter"])
        db.add(TenantLimits(
            tenant_id           = tenant.id,
            max_staff           = limits_cfg["max_staff"],
            max_active_jobs     = limits_cfg["max_active_jobs"],
            max_storage_gb      = limits_cfg["max_storage_gb"],
            max_api_calls_per_day = limits_cfg["max_api_calls_per_day"],
            max_engines         = limits_cfg["max_engines"],
            max_customers       = limits_cfg["max_customers"],
        ))

        # 4. Create subscription (trial period)
        from app.engines.subscription.service import SubscriptionService
        sub_svc = SubscriptionService(db=db)
        await sub_svc.create_subscription(
            tenant_id     = tenant.id,
            plan_type     = plan_type,
            billing_cycle = billing_cycle,
            trial_days    = trial_days,
        )

        # 5. P1 — Create package assignment (starts only after admin approval)
        #    Payment has been collected so status = paid_pending_approval.
        #    starts_at / expires_at remain NULL until admin approves.
        #    Wallet credits are NOT added here.
        #    Uses a SAVEPOINT so a failed flush leaves the outer transaction intact.
        if body.selected_package_id:
            try:
                from app.engines.package_commerce.service import PackageCommerceService
                pkg_svc = PackageCommerceService(db=db)
                async with db.begin_nested():  # SAVEPOINT — rolled back on failure, outer tx continues
                    await pkg_svc.create_package_assignment(
                        tenant_id=tenant.id,
                        package_id=uuid.UUID(body.selected_package_id),
                        payment_reference=body.razorpay_payment_id,
                        is_paid=True,
                    )
            except Exception as exc:
                logger.warning("registration.package_assignment_failed",
                               error=str(exc), package_id=body.selected_package_id)
                # Assignment failure must NOT block account creation

        await db.commit()

    except ServiceOSException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.error("registration.db_error", error=str(e))
        raise ServiceOSException("REGISTRATION_FAILED",
            "Failed to create your account. Please contact support.", status_code=500)

    # Send credentials
    welcome_body = (
        f"Welcome to ServiceOS, {session['owner_name']}!\n\n"
        f"Your account for \"{session['business_name']}\" has been created on the {plan_type.title()} plan.\n"
        f"Login email: {session['owner_email']}\n"
        f"Temporary password: {temp_password}\n\n"
        f"You have a {trial_days}-day free trial. Log in to add your services and go live.\n"
        f"You'll be asked to set a new password on first login."
    )
    await send_email(session["owner_email"], "Welcome to ServiceOS — Your login credentials", welcome_body)
    await send_sms(session["owner_phone"],
        f"ServiceOS account created for {session['business_name']}. Temp pwd: {temp_password}")

    # Mark session complete and clean up
    session["payment_completed"] = True
    await redis.delete(f"reg:session:{body.session_id}")

    logger.info("registration.completed",
        tenant_id=str(tenant.id), plan=plan_type, city=session["city"],
        country=session["country"], razorpay_order=body.razorpay_order_id)

    return ok(
        {
            "tenant_id":     str(tenant.id),
            "business_name": session["business_name"],
            "plan_type":     plan_type,
            "trial_days":    trial_days,
            "owner_email":   session["owner_email"],
            "temp_password": temp_password,
            "message":       (
                f"Account created! Your {trial_days}-day trial has started. "
                "Save your temporary password — you'll be asked to change it on first login."
            ),
        },
        getattr(r.state, "request_id", "—"), engine_id="public_registration",
    )


@router.post(
    "/register/webhook/razorpay",
    status_code=status.HTTP_200_OK,
    summary="Razorpay server-to-server webhook (public, no auth)",
    include_in_schema=False,
)
async def razorpay_webhook(r: Request):
    raw_body  = await r.body()
    signature = r.headers.get("X-Razorpay-Signature", "")

    if not verify_webhook_signature(raw_body, signature):
        logger.warning("razorpay.webhook_invalid_signature")
        return {"status": "ignored"}

    try:
        payload = json.loads(raw_body)
    except Exception:
        return {"status": "ignored"}

    event = payload.get("event", "")
    logger.info("razorpay.webhook_received", event=event)

    # payment.captured means money is in our account — log it.
    # Full activation (subscription status update) is handled by /complete.
    # This webhook is the fallback for cases where the client-side callback is missed.
    if event == "payment.captured":
        payment = payload.get("payload", {}).get("payment", {}).get("entity", {})
        order_id   = payment.get("order_id", "")
        payment_id = payment.get("id", "")
        logger.info("razorpay.payment_captured", order_id=order_id, payment_id=payment_id)

    return {"status": "ok"}
