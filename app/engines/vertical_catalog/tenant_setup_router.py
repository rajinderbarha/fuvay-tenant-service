"""Tenant-facing Home Services Setup Overview endpoints.

Backs the "Workspace Created / Setup Overview" onboarding page. tenant_id is
always resolved server-side from the caller's JWT (UserContext.tenant_id via
get_current_user) -- never accepted from the client -- matching the pattern
established in app.engines.provider_portal.router.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user, UserContext
from app.dependencies.db import get_db
from app.dependencies.vertical_guard import require_vertical_not_active
from app.core.permissions import require_tenant_owner_mutation
from app.schemas.base import ok
from app.engines.vertical_catalog.home_services_setup_service import (
    get_setup_overview, get_application_status, HOME_SERVICES_VERTICAL_KEY,
)
from app.engines.vertical_catalog.service import VerticalCatalogService
from app.engines.vertical_catalog.declarations import get_declaration_status, accept_declarations

router = APIRouter(prefix="/v1/tenant/home-services/setup", tags=["Tenant Home Services Setup"])

_svc = VerticalCatalogService()


def _tid(user: UserContext) -> uuid.UUID:
    if not user.tenant_id:
        raise HTTPException(403, "No tenant context")
    return uuid.UUID(user.tenant_id)


@router.get("/overview")
async def get_overview(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_vertical_not_active(HOME_SERVICES_VERTICAL_KEY)),
):
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    data = await get_setup_overview(db, tid)
    return ok(data, request_id=rid)


@router.get("/declarations")
async def get_declarations(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_vertical_not_active(HOME_SERVICES_VERTICAL_KEY)),
):
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    v = await _svc._by_key(db, HOME_SERVICES_VERTICAL_KEY)
    if not v:
        raise HTTPException(404, "Vertical not found")
    data = await get_declaration_status(db, tid, v.id)
    return ok(data, request_id=rid)


@router.post("/declarations")
async def accept_declarations_endpoint(
    request: Request,
    payload: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_owner_mutation),
    _guard: UserContext = Depends(require_vertical_not_active(HOME_SERVICES_VERTICAL_KEY)),
):
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    # Canonical request field is ``declaration_keys`` (the tenant client has
    # always used that descriptive name).  The endpoint previously looked
    # only for ``keys`` and silently treated a valid request as an empty
    # acceptance, so Submit immediately failed with DECLARATIONS_REQUIRED.
    # Keep ``keys`` as a compatibility alias for older clients, but never
    # acknowledge an empty/malformed consent write as successful.
    raw_keys = payload.get("declaration_keys")
    if raw_keys is None:
        raw_keys = payload.get("keys")
    if not isinstance(raw_keys, list) or not raw_keys:
        raise HTTPException(422, "Select all required declarations before saving.")
    if any(not isinstance(key, str) or not key.strip() for key in raw_keys):
        raise HTTPException(422, "Declaration keys must be non-empty strings.")
    # Deduplicate without changing order. Duplicate keys would otherwise add
    # two rows in one transaction and violate the append-only unique key.
    keys = list(dict.fromkeys(key.strip() for key in raw_keys))
    v = await _svc._by_key(db, HOME_SERVICES_VERTICAL_KEY)
    if not v:
        raise HTTPException(404, "Vertical not found")
    try:
        data = await accept_declarations(
            db, tid, v.id, keys, actor_id=uuid.UUID(user.user_id) if user.user_id else None,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    return ok(data, request_id=rid)


@router.post("/submit")
async def submit_for_review(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_owner_mutation),
    _guard: UserContext = Depends(require_vertical_not_active(HOME_SERVICES_VERTICAL_KEY)),
):
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    enrollment = await _svc.submit_for_review(
        db, tid, HOME_SERVICES_VERTICAL_KEY, actor_id=uuid.UUID(user.user_id) if user.user_id else None)
    return ok(enrollment, request_id=rid)


@router.get("/application-status")
async def get_application_status_endpoint(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    """Authoritative Application Status projection. Read-only, so it stays
    reachable even once the enrollment is 'active' (the frontend shows a
    brief activation-success view before it navigates the tenant onward)."""
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    data = await get_application_status(db, tid)
    return ok(data, request_id=rid)


@router.get("/routing")
async def get_routing(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    """Backend-authoritative post-login destination. Frontend maps the
    returned key to an internal route -- it never receives a raw URL."""
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))

    from sqlalchemy import text
    tenant_row = (await db.execute(
        text("SELECT status FROM tenants WHERE id=:tid"), {"tid": str(tid)},
    )).fetchone()
    if not tenant_row:
        return ok({"actor_type": "tenant_owner", "next_destination": "RESTRICTED_WORKSPACE",
                   "reason_code": "TENANT_NOT_FOUND"}, request_id=rid)

    enrollment = await _svc.get_or_create_enrollment(db, tid, HOME_SERVICES_VERTICAL_KEY)
    status = enrollment["status"]

    if tenant_row.status in ("suspended", "terminated"):
        destination, reason = "RESTRICTED_WORKSPACE", "TENANT_SUSPENDED"
    elif status == "active":
        destination, reason = "TENANT_DASHBOARD", "VERTICAL_ACTIVE"
    elif status in ("approved", "approved_pending_activation", "activation_requirements_pending", "activating"):
        destination, reason = "HOME_SERVICES_ACTIVATION", "APPROVED_PENDING_ACTIVATION"
    elif status in ("submitted", "under_review"):
        destination, reason = "HOME_SERVICES_UNDER_REVIEW", "SUBMITTED_FOR_REVIEW"
    elif status == "changes_requested":
        destination, reason = "HOME_SERVICES_CHANGES_REQUESTED", "CHANGES_REQUESTED"
    elif status == "rejected":
        destination, reason = "HOME_SERVICES_SETUP_OVERVIEW", "REJECTED"
    else:
        destination, reason = "HOME_SERVICES_SETUP_OVERVIEW", "SETUP_INCOMPLETE"

    return ok({
        "actor_type": "tenant_owner",
        "workspace_status": tenant_row.status,
        "vertical_status": status,
        "next_destination": destination,
        "reason_code": reason,
    }, request_id=rid)
