"""Conditional Question Engine -- admin router (migration 155).

Backs the approved Admin Catalog page's Problems & Questions tab (question
side) + the DeepSeek/customer-flow question resolver. Writes are super-admin
only; the resolver read is open to authenticated users (the customer flow
needs it).
"""
import uuid

from fastapi import APIRouter, Depends, Query, Request, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user, UserContext, require_super_admin
from app.dependencies.db import get_db
from app.engines.admin_catalog.question_service import CatalogQuestionService
from app.schemas.base import ApiResponse, ok

router = APIRouter(prefix="/v1/admin/catalog/questions", tags=["Admin Catalog Questions"])
ENGINE_ID = "admin_catalog"


def _svc(db: AsyncSession = Depends(get_db), u: UserContext = Depends(get_current_user)) -> CatalogQuestionService:
    return CatalogQuestionService(db=db, actor_id=uuid.UUID(u.user_id) if u.user_id else None)


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


@router.get("", response_model=ApiResponse[dict],
            summary="List questions for a (master_service, job_type) with options + rules")
async def list_questions(r: Request, master_service_id: uuid.UUID = Query(...),
                          job_type_id: uuid.UUID | None = Query(None),
                          u: UserContext = Depends(get_current_user),
                          s: CatalogQuestionService = Depends(_svc)):
    return ok(await s.list_questions(master_service_id, job_type_id), _rid(r), ENGINE_ID)


@router.post("", response_model=ApiResponse[dict], status_code=201, summary="Create a question")
async def create_question(r: Request, payload: dict = Body(...),
                           u: UserContext = Depends(require_super_admin),
                           s: CatalogQuestionService = Depends(_svc)):
    return ok(await s.create_question(payload), _rid(r), ENGINE_ID)


@router.put("/{question_id}", response_model=ApiResponse[dict], summary="Update a question")
async def update_question(question_id: uuid.UUID, r: Request, payload: dict = Body(...),
                           u: UserContext = Depends(require_super_admin),
                           s: CatalogQuestionService = Depends(_svc)):
    return ok(await s.update_question(question_id, payload), _rid(r), ENGINE_ID)


@router.post("/{question_id}/options", response_model=ApiResponse[dict], status_code=201,
             summary="Add a static option to a question")
async def add_option(question_id: uuid.UUID, r: Request, payload: dict = Body(...),
                     u: UserContext = Depends(require_super_admin),
                     s: CatalogQuestionService = Depends(_svc)):
    return ok(await s.add_option(question_id, payload), _rid(r), ENGINE_ID)


@router.post("/{question_id}/rules", response_model=ApiResponse[dict], status_code=201,
             summary="Add a show-when rule to a question")
async def add_rule(question_id: uuid.UUID, r: Request, payload: dict = Body(...),
                   u: UserContext = Depends(require_super_admin),
                   s: CatalogQuestionService = Depends(_svc)):
    return ok(await s.add_rule(question_id, payload), _rid(r), ENGINE_ID)


@router.delete("/rules/{rule_id}", response_model=ApiResponse[dict], summary="Delete a show-when rule")
async def delete_rule(rule_id: uuid.UUID, r: Request,
                      u: UserContext = Depends(require_super_admin),
                      s: CatalogQuestionService = Depends(_svc)):
    return ok(await s.delete_rule(rule_id), _rid(r), ENGINE_ID)


@router.post("/resolve", response_model=ApiResponse[dict],
             summary="Resolve applicable questions for a context (the DeepSeek/customer-flow contract)")
async def resolve_questions(r: Request, payload: dict = Body(...),
                            u: UserContext = Depends(get_current_user),
                            s: CatalogQuestionService = Depends(_svc)):
    master_service_id = uuid.UUID(payload["master_service_id"])
    job_type_id = uuid.UUID(payload["job_type_id"]) if payload.get("job_type_id") else None
    context = payload.get("context", {})
    return ok(await s.resolve_applicable_questions(master_service_id, job_type_id, context), _rid(r), ENGINE_ID)
