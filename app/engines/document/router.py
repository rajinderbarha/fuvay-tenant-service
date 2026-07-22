"""Document Engine — Router (10 endpoints). Zero inline imports."""
import uuid
import structlog
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.permissions import P, require_permission, require_tenant_mutation_permission
from app.dependencies.auth import get_current_user, UserContext, require_super_admin
from app.dependencies.db import get_db
from app.engines.document.service import DocumentService
from app.schemas.base import ApiResponse, Links, Link, ok
from app.core.security import get_client_ip
logger = structlog.get_logger("document.router")
router = APIRouter(prefix="/v1/documents", tags=["Document Engine"])
ENGINE_ID = "document"
def _svc(r: Request, db: AsyncSession=Depends(get_db), u: UserContext=Depends(get_current_user)):
    # Phase 2A Slice 2F-35: actor_tenant_id is now passed so DocumentService
    # can independently enforce tenant authority on generate_document/
    # send_for_signature/void_document.
    return DocumentService(db=db, request_id=getattr(r.state,"request_id","—"),
                            actor_id=uuid.UUID(u.user_id) if u.user_id else None,
                            actor_role=u.role, actor_ip=get_client_ip(r),
                            actor_tenant_id=uuid.UUID(u.tenant_id) if u.tenant_id else None)
def _rid(r): return getattr(r.state,"request_id","—")
@router.get("/meta", tags=["Engine Registry"])
async def engine_meta() -> dict:
    return {"engine_id": ENGINE_ID,"name":"Document Engine","version":"10.0.0",
            "endpoint_count": 10,"status":"active",
            "capabilities":["sequential_doc_numbers","variable_validation_before_render",
                            "frozen_after_signing","append_only_legal_audit_trail",
                            "signed_url_with_expiry","void_preserves_content"]}
@router.post("", status_code=status.HTTP_201_CREATED,
             summary="Validates variables before rendering — 422 with missing list if incomplete",
             response_model=ApiResponse[dict])
async def generate_doc(r: Request, u: UserContext=Depends(require_tenant_mutation_permission(P.TENANT_UPDATE)),
                        s: DocumentService=Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    data = await s.generate_document(uuid.UUID(body["tenant_id"]), body["doc_type"],
        body.get("entity_type"), body.get("entity_id"),
        uuid.UUID(body["customer_id"]) if body.get("customer_id") else None,
        body.get("variables",{}))
    return ok(data, _rid(r), ENGINE_ID,
              links=Links(actions=[Link(href=f"/v1/documents/{data['document_id']}/send",
                                        method="POST", rel="send_for_signature")]))
@router.get("/{document_id}", response_model=ApiResponse[dict])
async def get_doc(document_id: uuid.UUID, r: Request, u: UserContext=Depends(get_current_user),
                   s: DocumentService=Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_document(document_id), _rid(r), ENGINE_ID)
@router.get("", summary="List documents by entity (job, booking, customer)",
            response_model=ApiResponse[dict])
async def list_by_entity(r: Request, tenant_id: uuid.UUID=Query(...),
                          entity_type: str=Query(...), entity_id: str=Query(...),
                          limit: int=Query(20,ge=1,le=100), cursor: str|None=Query(None),
                          u: UserContext=Depends(get_current_user),
                          s: DocumentService=Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.list_by_entity(tenant_id, entity_type, entity_id, limit, cursor), _rid(r), ENGINE_ID)
@router.post("/{document_id}/send",
             summary="Send for signature — generates cryptographic signed URL with 24h expiry",
             response_model=ApiResponse[dict])
async def send_for_signature(document_id: uuid.UUID, r: Request,
                              u: UserContext=Depends(require_tenant_mutation_permission(P.TENANT_UPDATE)),
                              s: DocumentService=Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.send_for_signature(document_id), _rid(r), ENGINE_ID)
@router.get("/{document_id}/signing-url", response_model=ApiResponse[dict])
async def get_signing_url(document_id: uuid.UUID, r: Request,
                           u: UserContext=Depends(get_current_user),
                           s: DocumentService=Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_signing_url(document_id), _rid(r), ENGINE_ID)
@router.post("/sign/{token}",
             summary="Record signature — freezes document. is_frozen=True after this call.",
             response_model=ApiResponse[dict])
async def record_signature(token: str, r: Request,
                            db: AsyncSession=Depends(get_db)) -> ApiResponse[dict]:
    body = await r.json()
    svc = DocumentService(db=db, actor_ip=get_client_ip(r))
    return ok(await svc.record_signature(token, body.get("signature_data",""), get_client_ip(r)), _rid(r), ENGINE_ID)
@router.post("/{document_id}/void",
             summary="Void document — content preserved as evidence. is_frozen stays True if was signed.",
             response_model=ApiResponse[dict])
async def void_document(document_id: uuid.UUID, r: Request,
                         u: UserContext=Depends(require_tenant_mutation_permission(P.TENANT_UPDATE)),
                         s: DocumentService=Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.void_document(document_id, body.get("reason","Voided")), _rid(r), ENGINE_ID)
@router.get("/{document_id}/events",
            summary="Append-only legal audit trail — events are never deleted",
            response_model=ApiResponse[dict])
async def list_events(document_id: uuid.UUID, r: Request,
                       u: UserContext=Depends(get_current_user),
                       s: DocumentService=Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.list_document_events(document_id), _rid(r), ENGINE_ID)
@router.get("/tenants/{tenant_id}/templates/{doc_type}", response_model=ApiResponse[dict])
async def get_template(tenant_id: uuid.UUID, doc_type: str, r: Request,
                        u: UserContext=Depends(get_current_user),
                        s: DocumentService=Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_template(tenant_id, doc_type), _rid(r), ENGINE_ID)
