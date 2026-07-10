"""Profile Engine — Phase 0C Router.

Endpoints:
  GET  /v1/me/profile            — get own profile (all roles)
  PUT  /v1/me/profile            — update own profile (all roles)
  GET  /v1/provider/business-profile  — get business profile (tenant roles)
  PUT  /v1/provider/business-profile  — update business profile (tenant roles)
  GET  /v1/staff/profile         — get staff own profile
  PUT  /v1/staff/profile         — update staff own profile
  GET  /v1/customer/profile      — get customer own profile
  PUT  /v1/customer/profile      — update customer own profile

Auth: all endpoints require Bearer token.
Ownership: always from JWT — never from request body.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import UserContext, get_current_user, require_customer, require_technician
from app.dependencies.db import get_db
from app.engines.profile.schemas import UpdateUserProfileRequest, UpdateBusinessProfileRequest
from app.engines.profile.service import ProfileService
from app.schemas.base import ApiResponse, ok

router = APIRouter(prefix="/v1", tags=["My Profile"])


def _req_id(r: Request) -> str:
    return getattr(r.state, "request_id", "")


def _svc(
    db: AsyncSession = Depends(get_db),
    actor: UserContext = Depends(get_current_user),
) -> ProfileService:
    return ProfileService(db=db, actor=actor)


def _svc_customer(
    db: AsyncSession = Depends(get_db),
    actor: UserContext = Depends(require_customer),
) -> ProfileService:
    return ProfileService(db=db, actor=actor)


def _svc_technician(
    db: AsyncSession = Depends(get_db),
    actor: UserContext = Depends(require_technician),
) -> ProfileService:
    return ProfileService(db=db, actor=actor)


# ── Common: any authenticated user ───────────────────────────────────────────

@router.get(
    "/me/profile",
    response_model=ApiResponse[dict],
    summary="Get own profile",
    description=(
        "Returns the authenticated user's profile including display_name, language, timezone. "
        "Works for all roles: super_admin, tenant_owner, staff, technician, customer."
    ),
)
async def get_my_profile(
    r: Request,
    actor: UserContext = Depends(get_current_user),
    svc: ProfileService = Depends(_svc),
) -> ApiResponse[dict]:
    data = await svc.get_user_profile()
    return ok(data, _req_id(r))


@router.put(
    "/me/profile",
    response_model=ApiResponse[dict],
    summary="Update own profile",
    description=(
        "Update editable user profile fields. "
        "Forbidden fields (role, tenant_id, password_hash, etc.) are silently ignored — "
        "they are not accepted by the schema. "
        "Phone changes are uniqueness-checked. "
        "Email changes are not allowed here — contact support."
    ),
)
async def update_my_profile(
    body: UpdateUserProfileRequest,
    r: Request,
    actor: UserContext = Depends(get_current_user),
    svc: ProfileService = Depends(_svc),
) -> ApiResponse[dict]:
    data = await svc.update_user_profile(body)
    return ok(data, _req_id(r))


# ── Provider: business profile ────────────────────────────────────────────────

@router.get(
    "/provider/business-profile",
    response_model=ApiResponse[dict],
    tags=["Provider Business Profile"],
    summary="Get provider business profile",
)
async def get_business_profile(
    r: Request,
    actor: UserContext = Depends(require_technician),
    svc: ProfileService = Depends(_svc_technician),
) -> ApiResponse[dict]:
    data = await svc.get_business_profile()
    return ok(data, _req_id(r))


@router.put(
    "/provider/business-profile",
    response_model=ApiResponse[dict],
    tags=["Provider Business Profile"],
    summary="Update provider business profile",
    description=(
        "Update tenant business details. "
        "Critical fields (business_name, owner_name, address, GST, etc.) trigger re-verification "
        "if the tenant was already in 'verified' or 'approved' status. "
        "Read-only fields (tenant_id, verification_status, slug, status) are not accepted."
    ),
)
async def update_business_profile(
    body: UpdateBusinessProfileRequest,
    r: Request,
    actor: UserContext = Depends(require_technician),
    svc: ProfileService = Depends(_svc_technician),
) -> ApiResponse[dict]:
    data = await svc.update_business_profile(body)
    return ok(data, _req_id(r))


@router.post(
    "/provider/business-profile/submit-review",
    response_model=ApiResponse[dict],
    tags=["Provider Business Profile"],
    summary="Submit business profile for admin verification review",
    description=(
        "Validates that all required fields are complete, then moves "
        "verification_status to 'pending' (unless already pending or "
        "already verified/approved/active). Tenant cannot self-approve — "
        "this only requests review, it never sets an approved status."
    ),
)
async def submit_business_profile_for_review(
    r: Request,
    actor: UserContext = Depends(require_technician),
    svc: ProfileService = Depends(_svc_technician),
) -> ApiResponse[dict]:
    data = await svc.submit_business_profile_for_review()
    return ok(data, _req_id(r))


# ── Staff: own profile ────────────────────────────────────────────────────────

@router.get(
    "/staff/profile",
    response_model=ApiResponse[dict],
    tags=["Staff Profile"],
    summary="Get own staff profile",
)
async def get_staff_profile(
    r: Request,
    actor: UserContext = Depends(require_technician),
    svc: ProfileService = Depends(_svc_technician),
) -> ApiResponse[dict]:
    data = await svc.get_user_profile()
    return ok(data, _req_id(r))


@router.put(
    "/staff/profile",
    response_model=ApiResponse[dict],
    tags=["Staff Profile"],
    summary="Update own staff profile",
    description="Staff can update own display_name, language, timezone, phone. Role and tenant_id are read-only.",
)
async def update_staff_profile(
    body: UpdateUserProfileRequest,
    r: Request,
    actor: UserContext = Depends(require_technician),
    svc: ProfileService = Depends(_svc_technician),
) -> ApiResponse[dict]:
    data = await svc.update_user_profile(body)
    return ok(data, _req_id(r))


# ── Customer: own profile ─────────────────────────────────────────────────────

@router.get(
    "/customer/profile",
    response_model=ApiResponse[dict],
    tags=["Customer Profile"],
    summary="Get own customer profile",
)
async def get_customer_profile(
    r: Request,
    actor: UserContext = Depends(require_customer),
    svc: ProfileService = Depends(_svc_customer),
) -> ApiResponse[dict]:
    data = await svc.get_user_profile()
    return ok(data, _req_id(r))


@router.put(
    "/customer/profile",
    response_model=ApiResponse[dict],
    tags=["Customer Profile"],
    summary="Update own customer profile",
    description="Customer can update own display_name, language, timezone. Phone requires OTP (blocked here — contact support).",
)
async def update_customer_profile(
    body: UpdateUserProfileRequest,
    r: Request,
    actor: UserContext = Depends(require_customer),
    svc: ProfileService = Depends(_svc_customer),
) -> ApiResponse[dict]:
    data = await svc.update_user_profile(body)
    return ok(data, _req_id(r))
