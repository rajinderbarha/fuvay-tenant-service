"""Backend counterpart to setup navigation. Never gates payment confirmation."""
import uuid
from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies.auth import get_current_user, UserContext
from app.dependencies.db import get_db
from app.engines.vertical_catalog.models import Vertical, TenantVerticalEnrollment
from app.engines.vertical_catalog.setup_sequence import mutation_step, prerequisite
from app.exceptions import ServiceOSException


async def enforce_setup_sequence(request: Request,
                                 user: UserContext = Depends(get_current_user),
                                 db: AsyncSession = Depends(get_db)):
    target = mutation_step(request.url.path, request.method)
    if not target:
        return
    # Use the request's normal, cached auth dependency. Mixed public routers
    # attach this guard only to protected setup mutations, never invitations.
    if not user.tenant_id or user.role == "super_admin" or user.role.startswith("admin_"):
        return
    enrollment = (await db.execute(
        select(TenantVerticalEnrollment).join(Vertical, Vertical.id == TenantVerticalEnrollment.vertical_id)
        .where(TenantVerticalEnrollment.tenant_id == uuid.UUID(str(user.tenant_id)),
               Vertical.key == "home_services")
    )).scalar_one_or_none()
    if not enrollment or enrollment.status not in {"draft", "draft_setup", "changes_requested"}:
        return
    from app.engines.vertical_catalog.home_services_setup_service import get_setup_overview
    overview = await get_setup_overview(db, uuid.UUID(str(user.tenant_id)))
    blocked = prerequisite(overview["sections"], target)
    if blocked:
        raise ServiceOSException(
            "SETUP_PREVIOUS_STEP_INCOMPLETE",
            f"Complete {blocked['label']} to 100% before continuing.",
            status_code=409, context={"required_step": blocked["key"], "route": blocked["route"]},
        )
