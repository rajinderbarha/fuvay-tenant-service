"""Trust & Quality — public/customer-facing badge views.

MODULE-L5-12: customers only ever saw hardcoded text badges ("Verified",
"Highly Rated") computed in the matching engine. This exposes the real,
admin-configured customer_visible badges — with their icon and colour — so a
customer sees a provider's actual earned badges.
"""
import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.db import get_db
from app.engines.trust_quality.service import TrustQualityService
from app.schemas.base import ApiResponse, ok

public_trust_quality_router = APIRouter(
    prefix="/v1/public/trust-quality", tags=["public-trust-quality"])


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


@public_trust_quality_router.get("/providers/{tenant_id}/badges")
async def provider_public_badges(
    r: Request, tenant_id: uuid.UUID, db: AsyncSession = Depends(get_db),
) -> ApiResponse[dict]:
    """A provider's customer-visible badges — safe to show to anyone."""
    svc = TrustQualityService(db, None, "public")
    return ok({"items": await svc.list_earned_badges("tenant", tenant_id, "customer")}, _rid(r))
