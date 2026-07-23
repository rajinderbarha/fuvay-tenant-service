"""Inventory Document Extraction Engine — Router.

Prefix matches the inventory_document_extraction EngineDefinition's
api_prefix (app/engine_registry/registry.py): /v1/inventory/extraction
Plus draft item CRUD + publish under /v1/inventory/items/{id}/...
"""
import uuid

import structlog
from fastapi import APIRouter, Depends, File, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import P, require_tenant_mutation_permission
from app.dependencies.auth import get_current_user, UserContext
from app.dependencies.db import get_db
from app.engines.inventory.extraction_service import InventoryExtractionService
from app.schemas.base import ApiResponse, ok

logger = structlog.get_logger("inventory.extraction.router")
router = APIRouter(prefix="/v1/inventory", tags=["Inventory Document Extraction"])
ENGINE_ID = "inventory_document_extraction"


def _svc(r: Request, db: AsyncSession = Depends(get_db),
         u: UserContext = Depends(get_current_user)) -> InventoryExtractionService:
    return InventoryExtractionService(
        db=db, request_id=getattr(r.state, "request_id", "—"),
        actor_id=uuid.UUID(u.user_id) if u.user_id else None, actor_role=u.role,
        actor_tenant_id=uuid.UUID(u.tenant_id) if u.tenant_id else None)


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


@router.get("/extraction/meta", tags=["Engine Registry"])
async def engine_meta() -> dict:
    return {"engine_id": ENGINE_ID, "name": "Inventory Document Extraction Engine",
            "version": "1.0.0", "endpoint_count": 6, "status": "active",
            "capabilities": ["pdf_text_extraction", "llm_line_item_extraction",
                             "draft_review", "explicit_publish"]}


@router.post(
    "/tenants/{tenant_id}/extraction/upload",
    status_code=status.HTTP_201_CREATED,
    summary="Upload a PDF for AI inventory line-item extraction (draft rows only)",
    response_model=ApiResponse[dict],
)
async def upload_pdf_for_extraction(
    tenant_id: uuid.UUID, r: Request,
    file: UploadFile = File(...),
    u: UserContext = Depends(require_tenant_mutation_permission(P.TENANT_UPDATE)),
    s: InventoryExtractionService = Depends(_svc),
) -> ApiResponse[dict]:
    if file.content_type not in ("application/pdf",) and not (file.filename or "").lower().endswith(".pdf"):
        from app.exceptions import ServiceOSException
        raise ServiceOSException("VALIDATION_ERROR", "Only PDF files are accepted for extraction.")
    pdf_bytes = await file.read()
    result = await s.extract_from_pdf(tenant_id, file.filename or "upload.pdf", pdf_bytes)
    return ok(result, _rid(r), ENGINE_ID)


@router.get(
    "/tenants/{tenant_id}/extraction/drafts",
    summary="List draft inventory items awaiting provider review",
    response_model=ApiResponse[dict],
)
async def list_draft_items(
    tenant_id: uuid.UUID, r: Request,
    u: UserContext = Depends(get_current_user),
    s: InventoryExtractionService = Depends(_svc),
) -> ApiResponse[dict]:
    return ok(await s.list_drafts(tenant_id), _rid(r), ENGINE_ID)


@router.patch(
    "/items/{item_id}/draft",
    summary="Edit a draft inventory item before publishing",
    response_model=ApiResponse[dict],
)
async def update_draft_item(
    item_id: uuid.UUID, r: Request,
    u: UserContext = Depends(require_tenant_mutation_permission(P.TENANT_UPDATE)),
    s: InventoryExtractionService = Depends(_svc),
) -> ApiResponse[dict]:
    return ok(await s.update_draft(item_id, await r.json()), _rid(r), ENGINE_ID)


@router.delete(
    "/items/{item_id}/draft",
    summary="Discard a draft inventory item",
    response_model=ApiResponse[dict],
)
async def delete_draft_item(
    item_id: uuid.UUID, r: Request,
    u: UserContext = Depends(require_tenant_mutation_permission(P.TENANT_UPDATE)),
    s: InventoryExtractionService = Depends(_svc),
) -> ApiResponse[dict]:
    return ok(await s.delete_draft(item_id), _rid(r), ENGINE_ID)


@router.post(
    "/items/{item_id}/publish",
    summary="Publish a draft inventory item (draft -> published)",
    response_model=ApiResponse[dict],
)
async def publish_item(
    item_id: uuid.UUID, r: Request,
    u: UserContext = Depends(require_tenant_mutation_permission(P.TENANT_UPDATE)),
    s: InventoryExtractionService = Depends(_svc),
) -> ApiResponse[dict]:
    return ok(await s.publish_item(item_id), _rid(r), ENGINE_ID)


@router.post(
    "/items/publish-bulk",
    summary="Publish multiple draft inventory items at once",
    response_model=ApiResponse[dict],
)
async def publish_items_bulk(
    r: Request,
    u: UserContext = Depends(require_tenant_mutation_permission(P.TENANT_UPDATE)),
    s: InventoryExtractionService = Depends(_svc),
) -> ApiResponse[dict]:
    body = await r.json()
    item_ids = [uuid.UUID(i) for i in body.get("item_ids", [])]
    return ok(await s.publish_many(item_ids), _rid(r), ENGINE_ID)
