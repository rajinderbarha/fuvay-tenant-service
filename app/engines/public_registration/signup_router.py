"""Public 5-step no-payment tenant signup — the router `RegistrationService`
was always missing.

Real bug fixed here: `RegistrationService` (this file's sibling
service.py) fully implements the exact flow the approved signup design
specifies -- Owner Account -> Verify Contact -> Business Identity ->
Select Vertical -> Review & Consent -> auto-login into the vertical setup
wizard -- including real OTP delivery, password hashing, consent records,
and atomic tenant+user+enrollment creation. It was never instantiated
anywhere in the codebase; no router called it. A different, unrelated
signup path (`/v1/tenants/onboarding/signup`, an admin-mediated lead queue
with no login until admin approval) was used instead, which is why a real
signup got stuck with no way to log in and no way to reach the setup wizard.

Routes are namespaced under `/v1/public/signup/*` to avoid colliding with
the existing (paid, Razorpay) flow's `/v1/public/register/*` routes in
router.py -- the two are genuinely different products, not two versions of
one endpoint.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.db import get_db
from app.dependencies.auth import get_current_user, get_current_user_optional, UserContext
from app.engines.public_registration.service import RegistrationService
from app.schemas.base import ApiResponse, ok
from app.core.security import get_client_ip

ENGINE_ID = "public_registration"
router = APIRouter(prefix="/v1/public/signup", tags=["Public Signup (no payment)"])


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


def _svc(request: Request, db: AsyncSession = Depends(get_db)) -> RegistrationService:
    return RegistrationService(db=db, ip_address=get_client_ip(request), user_agent=request.headers.get("user-agent"))


# ── Step 1 — Owner Account ──────────────────────────────────────────────────
class OwnerAccountBody(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    mobile: str = Field(..., min_length=10, max_length=20)
    password: str = Field(..., min_length=8)
    password_confirm: str
    # Consent belongs to step 5. Keep these optional for backwards
    # compatibility with older clients, but never require or persist them
    # as granted during owner-account creation.
    authorized_declaration: bool = False
    tos_privacy_accepted: bool = False
    marketing_consent: bool = False
    # Present when resuming a save (idempotent re-submit of step 1).
    registration_id: uuid.UUID | None = None


@router.post("/owner-account", response_model=ApiResponse[dict], status_code=201,
             summary="Step 1: create/resume owner account, send OTPs")
async def owner_account(body: OwnerAccountBody, r: Request, svc: RegistrationService = Depends(_svc)):
    data = await svc.start_or_resume(
        full_name=body.full_name, email=body.email, mobile=body.mobile,
        password=body.password, password_confirm=body.password_confirm,
        authorized_declaration=body.authorized_declaration,
        tos_privacy_accepted=body.tos_privacy_accepted,
        marketing_consent=body.marketing_consent,
        registration_id=body.registration_id,
    )
    return ok(data, _rid(r), ENGINE_ID)


# ── Step 2 — Verify Contact ──────────────────────────────────────────────────
class VerifyContactBody(BaseModel):
    registration_id: uuid.UUID
    channel: str = Field(..., pattern="^(mobile|email)$")
    otp: str = Field(..., min_length=4, max_length=8)


@router.post("/verify-contact", response_model=ApiResponse[dict],
             summary="Step 2: verify a mobile or email OTP")
async def verify_contact(body: VerifyContactBody, r: Request, svc: RegistrationService = Depends(_svc)):
    data = await svc.verify_contact(body.registration_id, body.channel, body.otp)
    return ok(data, _rid(r), ENGINE_ID)


class ResendOtpBody(BaseModel):
    registration_id: uuid.UUID
    channel: str = Field(..., pattern="^(mobile|email)$")


@router.post("/resend-otp", response_model=ApiResponse[dict], summary="Resend an OTP for one channel")
async def resend_otp(body: ResendOtpBody, r: Request, svc: RegistrationService = Depends(_svc)):
    data = await svc.resend_otp(body.registration_id, body.channel)
    return ok(data, _rid(r), ENGINE_ID)


# ── Step 3 — Business Identity ───────────────────────────────────────────────
class BusinessIdentityBody(BaseModel):
    registration_id: uuid.UUID
    legal_name: str | None = None
    business_name: str | None = None
    gstin: str | None = None
    pan: str | None = None
    cin: str | None = None
    business_type: str | None = None
    year_established: int | None = None
    employee_count: int | None = None
    website_url: str | None = None
    description: str | None = None
    registered_address: dict | None = None


@router.post("/business-identity", response_model=ApiResponse[dict],
             summary="Step 3: save legal/business identity fields")
async def business_identity(body: BusinessIdentityBody, r: Request, svc: RegistrationService = Depends(_svc)):
    fields = body.model_dump(exclude={"registration_id"}, exclude_none=True)
    data = await svc.save_business_identity(body.registration_id, **fields)
    return ok(data, _rid(r), ENGINE_ID)


# ── Step 4 — Select Vertical ─────────────────────────────────────────────────
@router.get("/verticals", response_model=ApiResponse[dict], summary="List verticals open for signup")
async def list_verticals(r: Request, svc: RegistrationService = Depends(_svc)):
    data = await svc.list_registrable_verticals()
    return ok({"verticals": data}, _rid(r), ENGINE_ID)


class SelectVerticalBody(BaseModel):
    registration_id: uuid.UUID
    vertical_key: str


@router.post("/select-vertical", response_model=ApiResponse[dict], summary="Step 4: choose a business vertical")
async def select_vertical(body: SelectVerticalBody, r: Request, svc: RegistrationService = Depends(_svc)):
    data = await svc.select_vertical(body.registration_id, body.vertical_key)
    return ok(data, _rid(r), ENGINE_ID)


# ── Step 5 — Review & Consent -> Create Workspace ────────────────────────────
class CompleteBody(BaseModel):
    registration_id: uuid.UUID
    idempotency_key: str
    authorized_declaration: bool
    tos_privacy_accepted: bool
    marketing_consent: bool = False


@router.post("/complete", response_model=ApiResponse[dict], status_code=201,
             summary="Step 5: create the tenant, owner user and vertical enrollment; auto-login")
async def complete(body: CompleteBody, r: Request, svc: RegistrationService = Depends(_svc)):
    data = await svc.complete(
        body.registration_id, body.idempotency_key,
        body.authorized_declaration, body.tos_privacy_accepted, body.marketing_consent,
    )
    return ok(data, _rid(r), ENGINE_ID)


# ── Status (resume banner / application tracking) ───────────────────────────
@router.get("/status", response_model=ApiResponse[dict],
            summary="Resume-in-progress or post-signup stage, by registration_id or logged-in user")
async def get_status(
    r: Request,
    registration_id: uuid.UUID | None = None,
    user: UserContext | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    svc = RegistrationService(db=db)
    # get_status expects a real auth.models.User when checking a logged-in
    # applicant's post-signup stage; UserContext carries the same tenant_id.
    from app.engines.auth.models import User
    real_user = None
    if user and user.tenant_id:
        real_user = await db.get(User, uuid.UUID(user.user_id))
    data = await svc.get_status(registration_id, real_user)
    return ok(data, _rid(r), ENGINE_ID)
