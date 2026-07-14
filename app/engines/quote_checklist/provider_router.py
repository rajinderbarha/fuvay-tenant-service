"""Sprint 22 — Provider/Staff quote and checklist endpoints."""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies.auth import get_current_user
from app.dependencies.db import get_db
from app.schemas.base import ok
from app.engines.quote_checklist.quote_service import ServiceJobQuoteService
from app.engines.quote_checklist.checklist_service import ServiceChecklistService

quote_svc = ServiceJobQuoteService()
checklist_svc = ServiceChecklistService()

provider_router = APIRouter(prefix="/provider/quotes", tags=["provider-quotes"])
staff_router    = APIRouter(prefix="/staff/quotes",    tags=["staff-quotes"])
checklist_router = APIRouter(prefix="/staff/checklists", tags=["staff-checklists"])


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


# ── Provider: list quotes for a job ──────────────────────────────────────────

@provider_router.get("/jobs/{job_id}")
async def provider_list_job_quotes(
    job_id: str, r: Request,
    user=Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    data = await quote_svc.list_quotes_for_job(db, job_id, str(user.tenant_id))
    return ok(data, _rid(r), "provider_list_job_quotes")


@provider_router.get("/{quote_id}")
async def provider_get_quote(
    quote_id: str, r: Request,
    user=Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    data = await quote_svc.get_quote(db, quote_id)
    return ok(data, _rid(r), "provider_get_quote")


@provider_router.get("/{quote_id}/events")
async def provider_quote_events(
    quote_id: str, r: Request,
    user=Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    data = await quote_svc.list_quote_events(db, quote_id, str(user.tenant_id))
    return ok(data, _rid(r), "provider_quote_events")


@provider_router.post("/{quote_id}/cancel")
async def provider_cancel_quote(
    quote_id: str, body: dict, r: Request,
    user=Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    data = await quote_svc.cancel_quote(
        db, quote_id, str(user.tenant_id),
        reason=body.get("reason"), user_id=str(user.user_id), request_id=_rid(r),
    )
    return ok(data, _rid(r), "provider_cancel_quote")


# ── Staff: full quote management ──────────────────────────────────────────────

@staff_router.post("")
async def staff_create_quote(
    body: dict, r: Request,
    user=Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    data = await quote_svc.create_quote(
        db,
        job_id=body["job_id"],
        tenant_id=str(user.tenant_id),
        quote_type=body.get("quote_type", "repair_quote"),
        user_id=str(user.user_id),
        # MODULE-L5-02 bug #17: UserContext has no `staff_member_id` -> 500.
        # Staff identity is keyed off users.id; fall back to it.
        staff_member_id=str(getattr(user, "staff_member_id", None) or user.user_id),
        notes=body.get("notes"),
        request_id=_rid(r),
    )
    return ok(data, _rid(r), "staff_create_quote")


@staff_router.get("/jobs/{job_id}")
async def staff_list_job_quotes(
    job_id: str, r: Request,
    user=Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    data = await quote_svc.list_quotes_for_job(db, job_id, str(user.tenant_id))
    return ok(data, _rid(r), "staff_list_job_quotes")


@staff_router.get("/{quote_id}")
async def staff_get_quote(
    quote_id: str, r: Request,
    user=Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    data = await quote_svc.get_quote(db, quote_id)
    return ok(data, _rid(r), "staff_get_quote")


@staff_router.post("/{quote_id}/items")
async def staff_add_item(
    quote_id: str, body: dict, r: Request,
    user=Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    data = await quote_svc.add_item(
        db, quote_id, str(user.tenant_id),
        item_type=body["item_type"],
        item_name=body["item_name"],
        item_description=body.get("item_description"),
        quantity=float(body.get("quantity", 1)),
        unit_price=float(body.get("unit_price", 0)),
        is_required=bool(body.get("is_required", True)),
        is_customer_visible=bool(body.get("is_customer_visible", True)),
        user_id=str(user.user_id),
        request_id=_rid(r),
    )
    return ok(data, _rid(r), "staff_add_item")


@staff_router.put("/{quote_id}/items/{item_id}")
async def staff_update_item(
    quote_id: str, item_id: str, body: dict, r: Request,
    user=Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    data = await quote_svc.update_item(
        db, quote_id, item_id, str(user.tenant_id),
        item_name=body.get("item_name"),
        item_description=body.get("item_description"),
        quantity=body.get("quantity"),
        unit_price=body.get("unit_price"),
        is_customer_visible=body.get("is_customer_visible"),
        user_id=str(user.user_id),
        request_id=_rid(r),
    )
    return ok(data, _rid(r), "staff_update_item")


@staff_router.delete("/{quote_id}/items/{item_id}")
async def staff_remove_item(
    quote_id: str, item_id: str, r: Request,
    user=Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    data = await quote_svc.remove_item(
        db, quote_id, item_id, str(user.tenant_id),
        user_id=str(user.user_id), request_id=_rid(r),
    )
    return ok(data, _rid(r), "staff_remove_item")


@staff_router.post("/{quote_id}/send-to-customer")
async def staff_send_to_customer(
    quote_id: str, body: dict, r: Request,
    user=Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    data = await quote_svc.send_to_customer(
        db, quote_id, str(user.tenant_id),
        customer_notes=body.get("customer_notes"),
        user_id=str(user.user_id),
        request_id=_rid(r),
    )
    return ok(data, _rid(r), "staff_send_to_customer")


@staff_router.post("/{quote_id}/mark-revised")
async def staff_mark_revised(
    quote_id: str, r: Request,
    user=Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    data = await quote_svc.mark_revised(
        db, quote_id, str(user.tenant_id),
        user_id=str(user.user_id), request_id=_rid(r),
    )
    return ok(data, _rid(r), "staff_mark_revised")


@staff_router.get("/{quote_id}/events")
async def staff_quote_events(
    quote_id: str, r: Request,
    user=Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    data = await quote_svc.list_quote_events(db, quote_id, str(user.tenant_id))
    return ok(data, _rid(r), "staff_quote_events")


@staff_router.post("/{quote_id}/cancel")
async def staff_cancel_quote(
    quote_id: str, body: dict, r: Request,
    user=Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    data = await quote_svc.cancel_quote(
        db, quote_id, str(user.tenant_id),
        reason=body.get("reason"),
        user_id=str(user.user_id), request_id=_rid(r),
    )
    return ok(data, _rid(r), "staff_cancel_quote")


# ── Staff: checklist management ────────────────────────────────────────────────

@checklist_router.post("")
async def staff_create_checklist(
    body: dict, r: Request,
    user=Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    data = await checklist_svc.create_checklist(
        db,
        job_id=body["job_id"],
        booking_id=body["booking_id"],
        tenant_id=str(user.tenant_id),
        checklist_type=body.get("checklist_type", "inspection"),
        template_id=body.get("template_id"),
        user_id=str(user.user_id),
        custom_items=body.get("custom_items"),
    )
    return ok(data, _rid(r), "staff_create_checklist")


@checklist_router.get("/jobs/{job_id}")
async def staff_list_job_checklists(
    job_id: str, r: Request,
    user=Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    data = await checklist_svc.list_checklists_for_job(db, job_id, str(user.tenant_id))
    return ok(data, _rid(r), "staff_list_job_checklists")


@checklist_router.get("/{checklist_id}")
async def staff_get_checklist(
    checklist_id: str, r: Request,
    user=Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    data = await checklist_svc.get_checklist(db, checklist_id)
    return ok(data, _rid(r), "staff_get_checklist")


@checklist_router.put("/{checklist_id}/items/{item_id}")
async def staff_update_checklist_item(
    checklist_id: str, item_id: str, body: dict, r: Request,
    user=Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    data = await checklist_svc.update_checklist_item(
        db, checklist_id, item_id, str(user.tenant_id),
        user_id=str(user.user_id),
        value_text=body.get("value_text"),
        value_number=body.get("value_number"),
        value_json=body.get("value_json"),
        media_url=body.get("media_url"),
        status=body.get("status"),
    )
    return ok(data, _rid(r), "staff_update_checklist_item")


@checklist_router.post("/{checklist_id}/complete")
async def staff_complete_checklist(
    checklist_id: str, r: Request,
    user=Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    data = await checklist_svc.complete_checklist(
        db, checklist_id, str(user.tenant_id), str(user.user_id),
    )
    return ok(data, _rid(r), "staff_complete_checklist")
