"""Authenticated re-consent API for materially changed legal documents."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import UserContext, get_current_user
from app.dependencies.db import get_db
from app.engines.compliance.models import ConsentRecord
from app.engines.legal_documents import constants as C
from app.engines.legal_documents import service as legal_service
from app.exceptions import ServiceOSException
from app.models.base import utcnow
from app.schemas.base import ApiResponse, ok

router = APIRouter(prefix="/v1/legal", tags=["Legal Consent"])


class AcceptLegalDocumentsRequest(BaseModel):
    accepted: bool
    document_ids: list[uuid.UUID]


def _audience(user: UserContext) -> str:
    return C.AUDIENCE_CUSTOMER if user.role == "customer" else C.AUDIENCE_TENANT


async def _status(db: AsyncSession, user: UserContext) -> dict:
    live = []
    for doc_type in C.SIGNUP_CONSENT_DOC_TYPES:
        document = await legal_service.get_live(
            db, doc_type=doc_type, audience=_audience(user),
        )
        if document is not None:
            live.append(document)

    latest = (await db.execute(
        select(ConsentRecord).where(
            ConsentRecord.user_id == uuid.UUID(user.user_id),
            ConsentRecord.consent_type == "tos_privacy",
        ).order_by(ConsentRecord.created_at.desc()).limit(1)
    )).scalars().first()
    accepted_ids = set()
    if latest is not None and latest.action == "granted":
        accepted_ids = {
            str(item.get("id"))
            for item in (latest.meta or {}).get("legal_documents", [])
            if item.get("id")
        }

    pending = [
        document for document in live
        if document.requires_reacceptance and str(document.id) not in accepted_ids
    ]
    return {
        "requires_acceptance": bool(pending),
        "documents": [document.to_public_dict() for document in pending],
        "document_ids": [str(document.id) for document in pending],
        "message": (
            "Please review and accept the updated service, warranty, refund, and provider-responsibility terms."
            if pending else "Your legal acceptance is current."
        ),
    }


@router.get("/consent-status", response_model=ApiResponse[dict])
async def consent_status(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
) -> ApiResponse[dict]:
    return ok(await _status(db, user), getattr(request.state, "request_id", "-"), C.ENGINE_ID)


@router.post("/accept", response_model=ApiResponse[dict])
async def accept_documents(
    body: AcceptLegalDocumentsRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
) -> ApiResponse[dict]:
    if not body.accepted:
        raise ServiceOSException(
            "LEGAL_ACCEPTANCE_REQUIRED", "You must actively accept the updated terms.", status_code=422,
        )
    status = await _status(db, user)
    expected = set(status["document_ids"])
    supplied = {str(item) for item in body.document_ids}
    if expected and supplied != expected:
        raise ServiceOSException(
            "LEGAL_DOCUMENT_CHANGED",
            "The legal document changed while you were reviewing it. Please review the latest version.",
            status_code=409,
        )
    if not expected:
        return ok(status, getattr(request.state, "request_id", "-"), C.ENGINE_ID)

    references = await legal_service.consent_references(
        db, audience=_audience(user),
    )
    terms_version = next(
        (item["version"] for item in references if item["doc_type"] == C.DOC_TERMS_OF_SERVICE),
        "unversioned",
    )
    now = utcnow()
    record = ConsentRecord(
        user_id=uuid.UUID(user.user_id),
        tenant_id=uuid.UUID(user.tenant_id) if user.tenant_id else None,
        consent_type="tos_privacy",
        action="granted",
        policy_version=terms_version,
        granted_at=now,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        source="legal_reacceptance",
        meta={"legal_documents": references, "accepted_document_ids": sorted(expected)},
    )
    db.add(record)
    await db.commit()
    current = await _status(db, user)
    return ok(current, getattr(request.state, "request_id", "-"), C.ENGINE_ID)
