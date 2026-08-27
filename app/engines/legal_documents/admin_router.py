"""Legal Documents — platform admin authoring API (`/v1/admin/legal/*`).

Platform-side only. These documents govern the whole product, not one
workspace, so there is no tenant-scoped variant of this router: a tenant must
not be able to rewrite the Terms it is bound by.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import P, permission_checker
from app.dependencies.auth import UserContext, get_current_user
from app.dependencies.db import get_db
from app.schemas.base import ApiResponse, ok

from app.engines.legal_documents import constants as C
from app.engines.legal_documents import service as svc

router = APIRouter(prefix="/v1/admin/legal", tags=["Admin — Legal Documents"])


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", None) or r.headers.get("X-Request-ID", "—")


def _require_view(user: UserContext) -> None:
    if not permission_checker.has(user.role, P.LEGAL_ADMIN_VIEW, user.permission_overrides):
        raise HTTPException(403, "You cannot view legal documents.")


def _require_manage(user: UserContext) -> None:
    if not permission_checker.has(user.role, P.LEGAL_ADMIN_MANAGE, user.permission_overrides):
        raise HTTPException(403, "You cannot author or publish legal documents.")


def _actor(user: UserContext) -> uuid.UUID | None:
    """`UserContext.user_id` is a str from the JWT; the columns are UUID."""
    try:
        return uuid.UUID(str(user.user_id))
    except (TypeError, ValueError):
        return None


# ── Bodies ───────────────────────────────────────────────────────────────────
class DraftIn(BaseModel):
    doc_type: str
    version: str = Field(..., min_length=1, max_length=20)
    title: str = Field(..., min_length=2, max_length=200)
    body: str = Field(..., min_length=1)
    summary: str | None = None
    audience: str = C.AUDIENCE_ALL
    locale: str = Field(C.DEFAULT_LOCALE, min_length=2, max_length=10)
    requires_reacceptance: bool = False
    change_note: str | None = None


class DraftPatch(BaseModel):
    version: str | None = Field(None, min_length=1, max_length=20)
    title: str | None = Field(None, min_length=2, max_length=200)
    body: str | None = Field(None, min_length=1)
    summary: str | None = None
    requires_reacceptance: bool | None = None
    change_note: str | None = None


class PublishIn(BaseModel):
    #: Leave unset to take effect immediately. A future timestamp schedules
    #: the change and leaves the incumbent version live until then.
    effective_at: datetime | None = None


# ── Metadata ─────────────────────────────────────────────────────────────────
@router.get("/meta", response_model=ApiResponse[dict],
            summary="Document types, audiences and statuses the console offers")
async def get_meta(r: Request, user: UserContext = Depends(get_current_user)):
    """Drives the authoring form's dropdowns.

    Served from the constants rather than hardcoded in the frontend so adding
    a document type is a one-file backend change.
    """
    _require_view(user)
    return ok({
        "doc_types": [{"value": k, "label": v} for k, v in C.VALID_DOC_TYPES.items()],
        "audiences": sorted(C.VALID_AUDIENCES),
        "statuses": sorted(C.VALID_STATUSES),
        "default_locale": C.DEFAULT_LOCALE,
        "body_format": C.BODY_FORMAT_MARKDOWN,
        "signup_consent_doc_types": list(C.SIGNUP_CONSENT_DOC_TYPES),
    }, _rid(r), engine_id=C.ENGINE_ID)


# ── Read ─────────────────────────────────────────────────────────────────────
@router.get("/versions", response_model=ApiResponse[dict],
            summary="List legal document versions")
async def list_versions(
    r: Request,
    doc_type: str | None = Query(None),
    status: str | None = Query(None),
    audience: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_view(user)
    rows, total = await svc.list_versions(
        db, doc_type=doc_type, status=status, audience=audience,
        limit=limit, offset=offset,
    )
    # Bodies are omitted from the list: a legal document runs to thousands of
    # words and the table only renders metadata.
    return ok({
        "versions": [row.to_admin_dict(include_body=False) for row in rows],
        "total": total, "limit": limit, "offset": offset,
    }, _rid(r), engine_id=C.ENGINE_ID)


@router.get("/versions/{version_id}", response_model=ApiResponse[dict],
            summary="Read one version, including its body")
async def get_version(
    version_id: uuid.UUID,
    r: Request,
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_view(user)
    row = await svc.get_version(db, version_id)
    return ok(row.to_admin_dict(), _rid(r), engine_id=C.ENGINE_ID)


# ── Author ───────────────────────────────────────────────────────────────────
@router.post("/versions", response_model=ApiResponse[dict], status_code=201,
             summary="Create a draft version")
async def create_draft(
    body: DraftIn,
    r: Request,
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_manage(user)
    row = await svc.create_draft(
        db, doc_type=body.doc_type, version=body.version, title=body.title,
        body=body.body, summary=body.summary, audience=body.audience,
        locale=body.locale, requires_reacceptance=body.requires_reacceptance,
        change_note=body.change_note, actor_id=_actor(user),
    )
    await db.commit()
    await db.refresh(row)
    return ok(row.to_admin_dict(), _rid(r), engine_id=C.ENGINE_ID)


@router.patch("/versions/{version_id}", response_model=ApiResponse[dict],
              summary="Edit a draft version")
async def update_draft(
    version_id: uuid.UUID,
    body: DraftPatch,
    r: Request,
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_manage(user)
    row = await svc.update_draft(
        db, version_id, title=body.title, summary=body.summary, body=body.body,
        version=body.version, requires_reacceptance=body.requires_reacceptance,
        change_note=body.change_note,
    )
    await db.commit()
    await db.refresh(row)
    return ok(row.to_admin_dict(), _rid(r), engine_id=C.ENGINE_ID)


@router.post("/versions/{version_id}/publish", response_model=ApiResponse[dict],
             summary="Publish a draft version")
async def publish_version(
    version_id: uuid.UUID,
    body: PublishIn,
    r: Request,
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_manage(user)
    row = await svc.publish(
        db, version_id, effective_at=body.effective_at, actor_id=_actor(user),
    )
    await db.commit()
    await db.refresh(row)
    return ok(row.to_admin_dict(), _rid(r), engine_id=C.ENGINE_ID)


@router.post("/versions/{version_id}/archive", response_model=ApiResponse[dict],
             summary="Archive a published version")
async def archive_version(
    version_id: uuid.UUID,
    r: Request,
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_manage(user)
    row = await svc.archive(db, version_id)
    await db.commit()
    await db.refresh(row)
    return ok(row.to_admin_dict(), _rid(r), engine_id=C.ENGINE_ID)


@router.delete("/versions/{version_id}", response_model=ApiResponse[dict],
               summary="Delete a draft version")
async def delete_draft(
    version_id: uuid.UUID,
    r: Request,
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_manage(user)
    await svc.delete_draft(db, version_id)
    await db.commit()
    return ok({"deleted": True, "id": str(version_id)}, _rid(r), engine_id=C.ENGINE_ID)
