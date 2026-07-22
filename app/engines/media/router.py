"""Media Vault — Router (8 endpoints)."""
import uuid
import structlog
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.permissions import P, require_permission
from app.dependencies.auth import get_current_user, UserContext
from app.dependencies.db import get_db
from app.engines.media.service import MediaService
from app.schemas.base import ApiResponse, ok

logger = structlog.get_logger("media.router")
router = APIRouter(prefix="/v1/media", tags=["Media Vault"])
ENGINE_ID = "media"

def _svc(r: Request, db: AsyncSession = Depends(get_db),
          u: UserContext = Depends(get_current_user)) -> MediaService:
    # Phase 2A Slice 2F-31A (N01 residual): actor_role and actor_tenant_id are
    # now passed so MediaService can independently enforce tenant authority on
    # every mutation, rather than trusting client-supplied tenant_id values.
    return MediaService(db=db, request_id=getattr(r.state,"request_id","—"),
                         actor_id=uuid.UUID(u.user_id) if u.user_id else None,
                         actor_role=u.role,
                         actor_tenant_id=uuid.UUID(u.tenant_id) if u.tenant_id else None)
def _rid(r): return getattr(r.state,"request_id","—")

@router.get("/meta", tags=["Engine Registry"])
async def engine_meta() -> dict:
    return {"engine_id": ENGINE_ID, "name": "Media Vault", "version": "5.0.0",
            "endpoint_count": 8, "status": "active",
            "capabilities": ["multipart_upload","signed_urls","quota_enforcement",
                             "soft_delete","virus_scanning","entity_attachment"]}

@router.post("/upload/initiate", status_code=status.HTTP_201_CREATED, response_model=ApiResponse[dict])
async def initiate_upload(r: Request,
                           u: UserContext = Depends(get_current_user),
                           s: MediaService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    data = await s.initiate_upload(
        uuid.UUID(body["tenant_id"]), body["file_name"], body["mime_type"],
        body["size_bytes"], body.get("entity_type"), body.get("entity_id"))
    return ok(data, _rid(r), ENGINE_ID)

@router.post("/upload/{session_id}/confirm", response_model=ApiResponse[dict])
async def confirm_upload(session_id: uuid.UUID, r: Request,
                          u: UserContext = Depends(get_current_user),
                          s: MediaService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.confirm_upload(session_id, body.get("is_public", False)), _rid(r), ENGINE_ID)

@router.get("/tenants/{tenant_id}/files", response_model=ApiResponse[dict])
async def list_files(tenant_id: uuid.UUID, r: Request,
                      entity_type: str|None = Query(None),
                      entity_id: str|None = Query(None),
                      limit: int = Query(50,ge=1,le=200),
                      cursor: str|None = Query(None),
                      u: UserContext = Depends(get_current_user),
                      s: MediaService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.list_files(tenant_id, entity_type, entity_id, limit, cursor), _rid(r), ENGINE_ID)

@router.get("/tenants/{tenant_id}/files/{file_id}", response_model=ApiResponse[dict])
async def get_file(tenant_id: uuid.UUID, file_id: uuid.UUID, r: Request,
                    u: UserContext = Depends(get_current_user),
                    s: MediaService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_file(file_id, tenant_id), _rid(r), ENGINE_ID)

@router.delete("/tenants/{tenant_id}/files/{file_id}", response_model=ApiResponse[dict])
async def delete_file(tenant_id: uuid.UUID, file_id: uuid.UUID, r: Request,
                       u: UserContext = Depends(require_permission(P.TENANT_UPDATE)),
                       s: MediaService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.delete_file(file_id, tenant_id), _rid(r), ENGINE_ID)

@router.get("/tenants/{tenant_id}/quota", response_model=ApiResponse[dict])
async def storage_quota(tenant_id: uuid.UUID, r: Request,
                         u: UserContext = Depends(get_current_user),
                         s: MediaService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_storage_quota(tenant_id), _rid(r), ENGINE_ID)
