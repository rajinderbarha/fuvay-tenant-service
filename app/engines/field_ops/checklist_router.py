"""Field Ops Engine — Step 8: Tenant Checklist Template CRUD Router."""
import uuid
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.permissions import P, require_permission
from app.dependencies.auth import UserContext
from app.dependencies.db import get_db
from app.engines.field_ops.checklist_template_service import ChecklistTemplateService
from app.schemas.base import ApiResponse, ok

router = APIRouter(prefix="/v1/tenant/checklist-templates", tags=["Checklist Templates"])
ENGINE_ID = "field_ops"


def _svc(r: Request, db: AsyncSession = Depends(get_db),
         u: UserContext = Depends(require_permission(P.FIELD_OPS_CHECKLIST_MANAGE))) -> ChecklistTemplateService:
    return ChecklistTemplateService(
        db=db, actor_id=uuid.UUID(u.user_id) if u.user_id else None, actor_role=u.role,
        actor_tenant_id=uuid.UUID(u.tenant_id) if u.tenant_id else None)


def _rid(r): return getattr(r.state, "request_id", "—")


def _tenant_id(u: UserContext, body_tenant_id: str | None = None) -> uuid.UUID:
    if u.role == "super_admin" and body_tenant_id:
        return uuid.UUID(body_tenant_id)
    return uuid.UUID(u.tenant_id)


@router.get("", summary="Step 8: List my tenant's checklist templates", response_model=ApiResponse[dict])
async def list_templates(r: Request,
                          service_id: uuid.UUID | None = Query(None),
                          u: UserContext = Depends(require_permission(P.FIELD_OPS_CHECKLIST_MANAGE)),
                          s: ChecklistTemplateService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.list_templates(_tenant_id(u), service_id), _rid(r), ENGINE_ID)


@router.post("", status_code=status.HTTP_201_CREATED,
             summary="Step 8: Create a checklist template for a catalog service",
             response_model=ApiResponse[dict])
async def create_template(r: Request,
                           u: UserContext = Depends(require_permission(P.FIELD_OPS_CHECKLIST_MANAGE)),
                           s: ChecklistTemplateService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.create_template(_tenant_id(u, body.get("tenant_id")), body), _rid(r), ENGINE_ID)


@router.get("/{template_id}", summary="Step 8: Get a checklist template with its items",
            response_model=ApiResponse[dict])
async def get_template(template_id: uuid.UUID, r: Request,
                        u: UserContext = Depends(require_permission(P.FIELD_OPS_CHECKLIST_MANAGE)),
                        s: ChecklistTemplateService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_template(template_id), _rid(r), ENGINE_ID)


@router.put("/{template_id}", summary="Step 8: Update a checklist template",
            response_model=ApiResponse[dict])
async def update_template(template_id: uuid.UUID, r: Request,
                           u: UserContext = Depends(require_permission(P.FIELD_OPS_CHECKLIST_MANAGE)),
                           s: ChecklistTemplateService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.update_template(template_id, body), _rid(r), ENGINE_ID)


@router.delete("/{template_id}", summary="Step 8: Soft delete a checklist template",
               response_model=ApiResponse[dict])
async def delete_template(template_id: uuid.UUID, r: Request,
                           u: UserContext = Depends(require_permission(P.FIELD_OPS_CHECKLIST_MANAGE)),
                           s: ChecklistTemplateService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.delete_template(template_id), _rid(r), ENGINE_ID)


@router.get("/{template_id}/items", summary="Step 8: List a template's checklist items",
            response_model=ApiResponse[dict])
async def list_items(template_id: uuid.UUID, r: Request,
                      u: UserContext = Depends(require_permission(P.FIELD_OPS_CHECKLIST_MANAGE)),
                      s: ChecklistTemplateService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.list_items(template_id), _rid(r), ENGINE_ID)


@router.post("/{template_id}/items", status_code=status.HTTP_201_CREATED,
             summary="Step 8: Add a checklist item to a template",
             response_model=ApiResponse[dict])
async def add_item(template_id: uuid.UUID, r: Request,
                    u: UserContext = Depends(require_permission(P.FIELD_OPS_CHECKLIST_MANAGE)),
                    s: ChecklistTemplateService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.add_item(template_id, body), _rid(r), ENGINE_ID)


@router.put("/{template_id}/items/{item_id}", summary="Step 8: Update a checklist template item",
            response_model=ApiResponse[dict])
async def update_item(template_id: uuid.UUID, item_id: uuid.UUID, r: Request,
                       u: UserContext = Depends(require_permission(P.FIELD_OPS_CHECKLIST_MANAGE)),
                       s: ChecklistTemplateService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.update_item(template_id, item_id, body), _rid(r), ENGINE_ID)


@router.delete("/{template_id}/items/{item_id}", summary="Step 8: Soft delete a checklist template item",
               response_model=ApiResponse[dict])
async def delete_item(template_id: uuid.UUID, item_id: uuid.UUID, r: Request,
                       u: UserContext = Depends(require_permission(P.FIELD_OPS_CHECKLIST_MANAGE)),
                       s: ChecklistTemplateService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.delete_item(template_id, item_id), _rid(r), ENGINE_ID)
