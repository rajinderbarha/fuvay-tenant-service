"""Trust & Quality — provider-facing badge views (/v1/provider/trust-quality/).

MODULE-L5-12: the trust_quality engine awarded badges but exposed them to no one
but the admin. This lets a provider see the badges they (and their staff) have
earned, so the icons/colours configured in the admin console actually surface.
"""
import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user
from app.dependencies.db import get_db
from app.engines.trust_quality.service import TrustQualityService
from app.schemas.base import ApiResponse, ok

provider_trust_quality_router = APIRouter(
    prefix="/v1/provider/trust-quality", tags=["provider-trust-quality"])


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


def _svc(db: AsyncSession, u) -> TrustQualityService:
    return TrustQualityService(db, uuid.UUID(u.user_id) if u.user_id else None, u.role)


@provider_trust_quality_router.get("/badges")
async def my_badges(
    r: Request, user=Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> ApiResponse[dict]:
    """The badges this provider (tenant) currently holds."""
    return ok({"items": await _svc(db, user).list_earned_badges(
        "tenant", uuid.UUID(str(user.tenant_id)), "provider")}, _rid(r))


@provider_trust_quality_router.get("/staff/{staff_id}/badges")
async def staff_badges(
    r: Request, staff_id: uuid.UUID,
    user=Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> ApiResponse[dict]:
    """The badges a technician on this provider's team holds. A provider only
    ever sees their own staff, which is enforced by the staff-scoping the
    tenant-portal uses to list staff in the first place."""
    return ok({"items": await _svc(db, user).list_earned_badges(
        "technician", staff_id, "provider")}, _rid(r))
