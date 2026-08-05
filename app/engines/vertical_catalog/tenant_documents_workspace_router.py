"""Tenant Documents & Verification workspace — permanent, post-activation
management surface. Distinct from tenant_documents_router.py (the onboarding
step, gated by require_vertical_not_active). See
tenant_documents_workspace_service.py module docstring for the full
reuse/no-new-table rationale.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import UserContext
from app.dependencies.db import get_db
from app.core.permissions import P, require_permission, require_tenant_mutation_permission
from app.schemas.base import ok
from app.exceptions import ServiceOSException, NotFoundException
from app.engines.tenant_engine.models import TenantDocument
from app.engines.media.models import MediaAsset
from app.engines.vertical_catalog.document_requirements import (
    resolve_requirements, resolve_technician_requirements,
)
from app.engines.vertical_catalog import tenant_documents_workspace_service as svc

router = APIRouter(prefix="/v1/tenant/documents", tags=["Tenant Documents & Verification"])
DOCUMENT_MEDIA_CONTEXT = "provider_document"
utcnow = lambda: datetime.now(timezone.utc)


def _tid(user: UserContext) -> uuid.UUID:
    if not user.tenant_id:
        raise HTTPException(403, "No tenant context")
    return uuid.UUID(user.tenant_id)


def _rid(request: Request) -> str:
    return getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—")


def _has(user: UserContext, permission: str) -> bool:
    from app.core.permissions import permission_checker
    return permission_checker.has(role=user.role, permission=permission,
                                   overrides=getattr(user, "permission_overrides", None))


@router.get("/workspace")
async def get_workspace(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission(P.TENANT_DOCUMENTS_READ)),
):
    """Composed projection: summary + business documents + technician
    summary in one round trip, matching the page's initial load."""
    tid = _tid(user)
    business = await svc.get_business_documents(db, tid)
    technicians = await svc.get_technician_documents_summary(db, tid)
    summary = await svc.get_summary(db, tid)
    return ok({
        "summary": summary,
        "business_documents": business,
        "technicians": technicians,
        "permissions": {
            "can_upload": _has(user, P.TENANT_DOCUMENTS_UPLOAD),
            "can_view": True,
        },
    }, request_id=_rid(request))


@router.get("/business")
async def list_business_documents(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission(P.TENANT_DOCUMENTS_READ)),
):
    tid = _tid(user)
    return ok(await svc.get_business_documents(db, tid), request_id=_rid(request))


@router.get("/technicians")
async def list_technician_documents(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission(P.TENANT_DOCUMENTS_READ)),
):
    tid = _tid(user)
    return ok(await svc.get_technician_documents_summary(db, tid), request_id=_rid(request))


@router.get("/technicians/{staff_id}")
async def get_technician_documents(
    staff_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission(P.TENANT_DOCUMENTS_READ)),
):
    tid = _tid(user)
    data = await svc.get_technician_documents_detail(db, tid, staff_id)
    if not data:
        raise NotFoundException("Technician", str(staff_id))
    return ok(data, request_id=_rid(request))


@router.get("/expiry-calendar")
async def get_expiry_calendar(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission(P.TENANT_DOCUMENTS_READ)),
):
    tid = _tid(user)
    return ok({"items": await svc.get_expiry_calendar(db, tid)}, request_id=_rid(request))


@router.get("/activity")
async def get_activity(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission(P.TENANT_DOCUMENTS_READ)),
):
    tid = _tid(user)
    return ok({"items": await svc.get_activity(db, tid)}, request_id=_rid(request))


@router.get("/verification-report")
async def get_verification_report(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission(P.TENANT_DOCUMENTS_READ)),
):
    """Safe summary report -- counts, statuses and expiry dates only, never
    raw document content or unmasked identifiers."""
    tid = _tid(user)
    business = await svc.get_business_documents(db, tid)
    technicians = await svc.get_technician_documents_summary(db, tid)
    summary = await svc.get_summary(db, tid)
    return ok({
        "generated_at": utcnow().isoformat(),
        "summary": summary,
        "business_documents": [{
            "label": i["label"], "effective_status": i["effective_status"],
            "validity_status": i["validity_status"], "expiry_date": (i["document"] or {}).get("expiry_date"),
            "required": i["required"],
        } for i in business["items"]],
        "technicians": technicians["items"],
    }, request_id=_rid(request))


@router.get("/versions/{doc_type}")
async def get_document_versions(
    doc_type: str,
    request: Request,
    staff_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission(P.TENANT_DOCUMENTS_READ)),
):
    tid = _tid(user)
    q = select(TenantDocument).where(TenantDocument.tenant_id == tid, TenantDocument.doc_type == doc_type)
    q = q.where(TenantDocument.staff_member_id == staff_id) if staff_id else q.where(TenantDocument.staff_member_id.is_(None))
    rows = (await db.execute(q.order_by(TenantDocument.version.desc()))).scalars().all()
    return ok({"items": [svc._doc_row_dict(d) for d in rows]}, request_id=_rid(request))


class SubmitDocumentRequest(BaseModel):
    doc_type: str = Field(..., min_length=1, max_length=50)
    media_asset_id: uuid.UUID
    staff_member_id: uuid.UUID | None = None
    label: str | None = Field(default=None, max_length=200)
    document_number: str | None = Field(default=None, max_length=100)
    issue_date: datetime | None = None
    expiry_date: datetime | None = None


@router.post("")
async def submit_document(
    body: SubmitDocumentRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_mutation_permission(P.TENANT_DOCUMENTS_UPLOAD)),
):
    tid = _tid(user)
    tenant_row = await svc._tenant_row(db, tid)

    if body.staff_member_id:
        from sqlalchemy import text as _text
        exists = (await db.execute(_text(
            "SELECT 1 FROM provider_team_members WHERE id=:sid AND tenant_id=:tid"
        ), {"sid": str(body.staff_member_id), "tid": str(tid)})).fetchone()
        if not exists:
            raise NotFoundException("Technician", str(body.staff_member_id))
        known_keys = {r["key"] for r in resolve_technician_requirements(vertical=tenant_row.vertical)}
    else:
        known_keys = {r["key"] for r in resolve_requirements(
            vertical=tenant_row.vertical, business_type=tenant_row.business_type, country=tenant_row.country)}

    if body.doc_type != "additional" and body.doc_type not in known_keys:
        raise ServiceOSException("DOC_TYPE_NOT_APPLICABLE",
            "This document type is not part of the verification requirements.", status_code=422)

    if body.expiry_date and body.issue_date and body.expiry_date < body.issue_date:
        raise ServiceOSException("INVALID_DATES", "Expiry date cannot precede issue date.", status_code=422)

    asset = (await db.execute(select(MediaAsset).where(MediaAsset.id == body.media_asset_id))).scalar_one_or_none()
    if not asset or asset.tenant_id != tid or asset.status != "active":
        raise ServiceOSException("MEDIA_ASSET_NOT_FOUND",
            "The uploaded file could not be found for this workspace.", status_code=404)
    if asset.media_context != DOCUMENT_MEDIA_CONTEXT:
        raise ServiceOSException("MEDIA_CONTEXT_MISMATCH",
            "This file was not uploaded as a verification document.", status_code=422)

    existing_q = select(TenantDocument).where(
        TenantDocument.tenant_id == tid, TenantDocument.doc_type == body.doc_type,
        TenantDocument.is_current == True,  # noqa: E712
    )
    existing_q = existing_q.where(TenantDocument.staff_member_id == body.staff_member_id) if body.staff_member_id \
        else existing_q.where(TenantDocument.staff_member_id.is_(None))
    existing = (await db.execute(existing_q)).scalar_one_or_none()

    new_doc = TenantDocument(
        tenant_id=tid, doc_type=body.doc_type, label=body.label, staff_member_id=body.staff_member_id,
        media_asset_id=body.media_asset_id, file_url=f"/v1/media/{body.media_asset_id}/view",
        document_number=body.document_number, issue_date=body.issue_date, expiry_date=body.expiry_date,
        version=(existing.version + 1) if existing else 1,
        is_current=True, status="pending_review",
        uploaded_by_user_id=uuid.UUID(user.user_id),
    )
    db.add(new_doc)
    await db.flush()

    if existing:
        existing.is_current = False
        existing.status = "superseded"
        existing.superseded_by_id = new_doc.id

    from app.engines.tenant_engine.models import TenantAuditLog
    db.add(TenantAuditLog(
        tenant_id=tid, actor_id=uuid.UUID(user.user_id), actor_role=user.role,
        action_type="document.submitted", entity_type="tenant_document", entity_id=str(new_doc.id),
        before_state=None, after_state={"status": "pending_review", "doc_type": body.doc_type},
    ))
    await db.commit()
    await db.refresh(new_doc)

    try:
        from app.engines.platform_notifications.notification_service import NotificationService
        from app.dependencies.auth import UserContext as _UC
        from sqlalchemy import text as _text
        admin_row = (await db.execute(_text(
            "SELECT id FROM users WHERE role IN ('super_admin','admin_operations') LIMIT 1"
        ))).fetchone()
        if admin_row:
            await NotificationService().fire_event(
                db, "document.submitted",
                payload={"tenant_name": tenant_row.vertical, "document_label": body.label or body.doc_type,
                         "tenant_id": str(tid)},
                tenant_id=tid, source_record_type="tenant_document", source_record_id=new_doc.id,
                recipients=[{"user_id": admin_row.id, "recipient_type": "admin"}],
            )
    except Exception:
        pass

    return ok(svc._doc_row_dict(new_doc), request_id=_rid(request))
