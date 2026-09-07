"""Tenant-facing Verification Documents onboarding step.

Requirement manifest is resolved server-side (vertical + business_type +
country) from document_requirements.py -- the frontend never hardcodes
which documents are required. File bytes are never handled here: uploads go
through the canonical Media Engine (`POST /v1/media/upload`,
`media_context="provider_document"`) first; this router only claims an
already-validated, tenant-scoped MediaAsset against a requirement slot and
manages the TenantDocument version/review lifecycle on top of it.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user, UserContext
from app.dependencies.db import get_db
from app.dependencies.vertical_guard import require_vertical_not_active
from app.core.permissions import require_tenant_owner_mutation
from app.schemas.base import ok
from app.exceptions import ServiceOSException, NotFoundException
from app.engines.tenant_engine.models import TenantDocument
from app.engines.media.models import MediaAsset
from app.engines.media.validation import CONTEXT_RULES
from app.engines.vertical_catalog.home_services_setup_service import HOME_SERVICES_VERTICAL_KEY
from app.engines.vertical_catalog.document_requirements import (
    resolve_requirements, required_keys, is_business_profile_complete, POLICY_VERSION,
)

from app.dependencies.setup_sequence import enforce_setup_sequence

router = APIRouter(dependencies=[Depends(enforce_setup_sequence)], prefix="/v1/tenant/home-services/setup/documents", tags=["Tenant Verification Documents"])

DOCUMENT_MEDIA_CONTEXT = "provider_document"
utcnow = lambda: datetime.now(timezone.utc)


def _tid(user: UserContext) -> uuid.UUID:
    if not user.tenant_id:
        raise HTTPException(403, "No tenant context")
    return uuid.UUID(user.tenant_id)


async def _tenant_row(db: AsyncSession, tid: uuid.UUID):
    row = (await db.execute(
        text("SELECT id, vertical, business_type, country, status FROM tenants WHERE id=:tid"),
        {"tid": str(tid)},
    )).fetchone()
    if not row:
        raise NotFoundException("Tenant", str(tid))
    return row


async def _current_documents(db: AsyncSession, tid: uuid.UUID) -> list[TenantDocument]:
    r = await db.execute(
        select(TenantDocument).where(TenantDocument.tenant_id == tid, TenantDocument.is_current == True)  # noqa: E712
    )
    return list(r.scalars().all())


def _doc_dict(d: TenantDocument) -> dict:
    return {
        "id": str(d.id),
        "doc_type": d.doc_type,
        "label": d.label,
        "media_asset_id": str(d.media_asset_id) if d.media_asset_id else None,
        "view_url": f"/v1/media/{d.media_asset_id}/view" if d.media_asset_id else None,
        "document_number": d.document_number,
        "issue_date": d.issue_date.isoformat() if d.issue_date else None,
        "expiry_date": d.expiry_date.isoformat() if d.expiry_date else None,
        "version": d.version,
        "status": d.status,
        "rejection_reason": d.rejection_reason,
        "verified_at": d.verified_at.isoformat() if d.verified_at else None,
        "uploaded_at": d.created_at.isoformat() if d.created_at else None,
    }


async def _build_manifest(db: AsyncSession, tid: uuid.UUID, tenant_row) -> dict:
    reqs = resolve_requirements(vertical=tenant_row.vertical, business_type=tenant_row.business_type,
                                 country=tenant_row.country)
    current = await _current_documents(db, tid)
    by_type = {d.doc_type: d for d in current}

    items = []
    for req in reqs:
        doc = by_type.get(req["key"])
        items.append({
            **req,
            "document": _doc_dict(doc) if doc else None,
            "status": doc.status if doc else "not_uploaded",
        })

    additional = [_doc_dict(d) for d in current if d.doc_type == "additional"]

    required = [i for i in items if i["required"]]
    uploaded = sum(1 for i in required if i["status"] != "not_uploaded")
    verified = sum(1 for i in required if i["status"] == "verified")
    pending = sum(1 for i in required if i["status"] == "pending_review")
    rejected = sum(1 for i in required if i["status"] in ("rejected", "changes_requested"))
    missing = len(required) - uploaded

    rules = CONTEXT_RULES[DOCUMENT_MEDIA_CONTEXT]
    return {
        "policy_version": POLICY_VERSION,
        "requirements_context": {"business_type": tenant_row.business_type, "vertical": tenant_row.vertical},
        "requirements": items,
        "additional_documents": additional,
        "readiness": {
            "required_total": len(required),
            "uploaded": uploaded,
            "verified": verified,
            "pending_review": pending,
            "rejected": rejected,
            "missing": missing,
            "all_required_uploaded": missing == 0,
            "all_required_verified": verified == len(required) and len(required) > 0,
        },
        "upload_policy": {
            "allowed_mime_types": sorted(rules["allowed_types"]),
            "max_file_size_mb": rules["max_mb"],
        },
    }


@router.get("/requirements")
async def get_requirements(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_vertical_not_active(HOME_SERVICES_VERTICAL_KEY)),
):
    tid = _tid(user)
    rid = getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—")
    tenant_row = await _tenant_row(db, tid)

    profile_row = (await db.execute(
        text("SELECT business_name, business_type, phone, email, address_line1, district, city, state, zipcode "
             "FROM tenants WHERE id=:tid"),
        {"tid": str(tid)},
    )).fetchone()
    if not is_business_profile_complete(profile_row):
        return ok({"business_profile_complete": False, "requirements": [], "additional_documents": [],
                    "readiness": None, "upload_policy": None, "policy_version": POLICY_VERSION,
                    "requirements_context": None}, request_id=rid)

    manifest = await _build_manifest(db, tid, tenant_row)
    manifest["business_profile_complete"] = True
    return ok(manifest, request_id=rid)


class SubmitDocumentRequest(BaseModel):
    doc_type: str = Field(..., min_length=1, max_length=50)
    media_asset_id: uuid.UUID
    label: str | None = Field(default=None, max_length=200)
    document_number: str | None = Field(default=None, max_length=100)
    issue_date: datetime | None = None
    expiry_date: datetime | None = None


@router.post("")
async def submit_document(
    body: SubmitDocumentRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_owner_mutation),
    _guard: UserContext = Depends(require_vertical_not_active(HOME_SERVICES_VERTICAL_KEY)),
):
    tid = _tid(user)
    rid = getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—")
    tenant_row = await _tenant_row(db, tid)

    if body.doc_type != "additional":
        known_keys = {r["key"] for r in resolve_requirements(
            vertical=tenant_row.vertical, business_type=tenant_row.business_type, country=tenant_row.country)}
        if body.doc_type not in known_keys:
            raise ServiceOSException("DOC_TYPE_NOT_APPLICABLE",
                "This document type is not part of your verification requirements.", status_code=422)

    # Media asset must exist, belong to THIS tenant, and be the right context —
    # never trust a media_asset_id blindly; tenant isolation is enforced by
    # matching tenant_id server-side, not by the caller's say-so.
    asset = (await db.execute(select(MediaAsset).where(MediaAsset.id == body.media_asset_id))).scalar_one_or_none()
    if not asset or asset.tenant_id != tid or asset.status != "active":
        raise ServiceOSException("MEDIA_ASSET_NOT_FOUND",
            "The uploaded file could not be found for this workspace.", status_code=404)
    if asset.media_context != DOCUMENT_MEDIA_CONTEXT:
        raise ServiceOSException("MEDIA_CONTEXT_MISMATCH",
            "This file was not uploaded as a verification document.", status_code=422)

    existing = (await db.execute(
        select(TenantDocument).where(
            TenantDocument.tenant_id == tid, TenantDocument.doc_type == body.doc_type,
            TenantDocument.is_current == True,  # noqa: E712
        )
    )).scalar_one_or_none()

    new_doc = TenantDocument(
        tenant_id=tid, doc_type=body.doc_type, label=body.label,
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

    await db.commit()
    await db.refresh(new_doc)
    return ok(_doc_dict(new_doc), request_id=rid)


@router.delete("/{document_id}")
async def remove_document(
    document_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_owner_mutation),
    _guard: UserContext = Depends(require_vertical_not_active(HOME_SERVICES_VERTICAL_KEY)),
):
    """Only 'additional' documents (not part of the required manifest) can
    be removed outright — a required slot must go through replace instead,
    so a required document can never silently drop back to not_uploaded."""
    tid = _tid(user)
    rid = getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—")
    doc = (await db.execute(
        select(TenantDocument).where(TenantDocument.id == document_id, TenantDocument.tenant_id == tid)
    )).scalar_one_or_none()
    if not doc:
        raise NotFoundException("Document", str(document_id))
    if doc.doc_type != "additional":
        raise ServiceOSException("CANNOT_REMOVE_REQUIRED_DOCUMENT",
            "Required documents can only be replaced, not removed.", status_code=422)
    if not doc.is_current:
        raise ServiceOSException("DOCUMENT_NOT_CURRENT",
            "This document version is no longer current.", status_code=409)

    doc.is_current = False
    doc.status = "removed"
    await db.commit()
    return ok({"removed": True}, request_id=rid)
