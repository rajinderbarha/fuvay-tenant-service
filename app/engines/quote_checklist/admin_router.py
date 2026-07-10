"""Sprint 22 — Admin checklist template + job checklist endpoints."""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies.auth import get_current_user
from app.dependencies.db import get_db
from app.schemas.base import ok
from app.engines.quote_checklist.checklist_service import ServiceChecklistService
from app.engines.quote_checklist.quote_service import ServiceJobQuoteService

checklist_svc = ServiceChecklistService()
quote_svc = ServiceJobQuoteService()

admin_router = APIRouter(prefix="/admin/checklist-templates", tags=["admin-checklist-templates"])
admin_quote_router = APIRouter(prefix="/admin/quotes", tags=["admin-quotes"])


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


# ── Admin: checklist template CRUD ────────────────────────────────────────────

@admin_router.post("")
async def admin_create_template(
    body: dict, r: Request,
    user=Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    data = await checklist_svc.create_template(
        db,
        template_name=body["template_name"],
        template_type=body["template_type"],
        applies_to=body.get("applies_to", "offering"),
        category_id=body.get("category_id"),
        offering_id=body.get("offering_id"),
        tenant_id=body.get("tenant_id"),
        is_required=bool(body.get("is_required", False)),
    )
    return ok(data, _rid(r), "admin_create_template")


@admin_router.get("")
async def admin_list_templates(
    r: Request,
    user=Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    data = await checklist_svc.list_templates(db)
    return ok(data, _rid(r), "admin_list_templates")


@admin_router.get("/{template_id}")
async def admin_get_template(
    template_id: str, r: Request,
    user=Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    data = await checklist_svc.get_template(db, template_id)
    return ok(data, _rid(r), "admin_get_template")


@admin_router.post("/{template_id}/items")
async def admin_add_template_item(
    template_id: str, body: dict, r: Request,
    user=Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    data = await checklist_svc.add_template_item(
        db, template_id,
        item_label=body["item_label"],
        item_description=body.get("item_description"),
        input_type=body.get("input_type", "checkbox"),
        is_required=bool(body.get("is_required", False)),
        sort_order=int(body.get("sort_order", 0)),
        options=body.get("options"),
    )
    return ok(data, _rid(r), "admin_add_template_item")


# ── Admin: view job checklists ─────────────────────────────────────────────────

@admin_router.get("/jobs/{job_id}")
async def admin_job_checklists(
    job_id: str, r: Request,
    user=Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    # admin can query any tenant's job checklists — omit tenant filter
    from sqlalchemy import select
    from app.engines.quote_checklist.models import ServiceJobChecklist
    import uuid
    db_session = db
    res = await db_session.execute(
        select(ServiceJobChecklist)
        .where(ServiceJobChecklist.job_id == uuid.UUID(job_id))
        .order_by(ServiceJobChecklist.created_at.desc())
    )
    data = [cl.to_dict() for cl in res.scalars().all()]
    return ok(data, _rid(r), "admin_job_checklists")


# ── Admin: view quotes for a job ──────────────────────────────────────────────

@admin_quote_router.get("/jobs/{job_id}")
async def admin_list_job_quotes(
    job_id: str, r: Request,
    user=Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select
    from app.engines.quote_checklist.models import ServiceJobQuote
    import uuid
    res = await db.execute(
        select(ServiceJobQuote)
        .where(ServiceJobQuote.job_id == uuid.UUID(job_id))
        .order_by(ServiceJobQuote.created_at.desc())
    )
    data = [q.to_dict() for q in res.scalars().all()]
    return ok(data, _rid(r), "admin_list_job_quotes")


@admin_quote_router.get("/{quote_id}")
async def admin_get_quote(
    quote_id: str, r: Request,
    user=Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    data = await quote_svc.get_quote(db, quote_id)
    return ok(data, _rid(r), "admin_get_quote")


@admin_quote_router.get("/{quote_id}/events")
async def admin_quote_events(
    quote_id: str, r: Request,
    user=Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    data = await quote_svc.list_quote_events(db, quote_id)
    return ok(data, _rid(r), "admin_quote_events")
