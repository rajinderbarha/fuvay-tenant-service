"""Technician Mobile App Phase T — Documents & Certifications routes."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import require_staff_or_technician_only, UserContext
from app.dependencies.db import get_db
from app.dependencies.vertical_guard import require_tenant_vertical_active
from app.core.permissions import require_tenant_owner_mutation
from app.schemas.base import ok
from app.exceptions import ServiceOSException
from app.engines.home_service_assignment.mobile_documents_service import MobileDocumentsService

router = APIRouter(prefix="/v1/staff/me/documents", tags=["Mobile Documents & Certifications"])
tenant_router = APIRouter(prefix="/v1/tenant/documents/technicians", tags=["Tenant Staff Document Review"])

_svc = MobileDocumentsService()


def _rid(request: Request) -> str:
    return request.headers.get("x-request-id", str(uuid.uuid4()))


def _require_tenant(user: UserContext) -> uuid.UUID:
    if not user.tenant_id:
        raise ServiceOSException("TENANT_REQUIRED", "No tenant context on this account.", status_code=403)
    return uuid.UUID(user.tenant_id)


@router.get("")
async def get_documents(
    request: Request,
    user: UserContext = Depends(require_staff_or_technician_only),
    _vertical: UserContext = Depends(require_tenant_vertical_active("home_services")),
    db: AsyncSession = Depends(get_db),
):
    tid = _require_tenant(user)
    data = await _svc.get_documents(db, uuid.UUID(user.user_id), tid)
    return ok(data, request_id=_rid(request), engine_id="home_service_assignment")


@router.post("")
async def submit_document(
    body: dict, request: Request,
    user: UserContext = Depends(require_staff_or_technician_only),
    _vertical: UserContext = Depends(require_tenant_vertical_active("home_services")),
    db: AsyncSession = Depends(get_db),
):
    tid = _require_tenant(user)
    doc_type = (body or {}).get("doc_type")
    media_asset_id = (body or {}).get("media_asset_id")
    if not doc_type or not media_asset_id:
        raise ServiceOSException("VALIDATION_ERROR", "doc_type and media_asset_id are required.", status_code=400)

    from datetime import datetime
    def _parse(v):
        return datetime.fromisoformat(v) if v else None

    data = await _svc.submit_document(
        db, uuid.UUID(user.user_id), tid,
        doc_type=doc_type, media_asset_id=uuid.UUID(media_asset_id),
        document_number=(body or {}).get("document_number"),
        issue_date=_parse((body or {}).get("issue_date")),
        expiry_date=_parse((body or {}).get("expiry_date")),
    )
    return ok(data, request_id=_rid(request), engine_id="home_service_assignment")


@router.get("/{doc_type}/history")
async def get_document_history(
    doc_type: str, request: Request,
    user: UserContext = Depends(require_staff_or_technician_only),
    db: AsyncSession = Depends(get_db),
):
    tid = _require_tenant(user)
    data = await _svc.list_versions(db, uuid.UUID(user.user_id), tid, doc_type)
    return ok({"versions": data}, request_id=_rid(request), engine_id="home_service_assignment")


async def review_document(
    document_id: uuid.UUID, body: dict, request: Request,
    user: UserContext = Depends(require_tenant_owner_mutation),
    db: AsyncSession = Depends(get_db),
):
    tid = _require_tenant(user)
    decision = (body or {}).get("decision")
    if not decision:
        raise ServiceOSException("VALIDATION_ERROR", "decision is required.", status_code=400)
    data = await _svc.review_document(
        db, tid, document_id, decision=decision,
        reviewer_user_id=uuid.UUID(user.user_id), reason=(body or {}).get("reason"),
    )
    return ok(data, request_id=_rid(request), engine_id="home_service_assignment")


# Mount the review route on the shared tenant_router prefix so it lands at
# /v1/tenant/documents/technicians/{document_id}/review, alongside the
# existing GET .../technicians/{staff_id} in tenant_documents_workspace_router.py.
tenant_router.add_api_route("/{document_id}/review", review_document, methods=["POST"])
