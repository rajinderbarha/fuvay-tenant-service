"""Admin Media Library Router — /v1/admin/media/* endpoints.

All write endpoints require require_super_admin.
All read endpoints require get_current_user (super_admin role enforced in service).
Signed token resolution (/v1/media/signed/{token}) is unauthenticated — the
token IS the credential, and it's single-use with a 15-min TTL.
"""
from __future__ import annotations

import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.base import ApiResponse, ok
from app.dependencies.db import get_db as get_async_session
from app.dependencies.auth import UserContext, get_current_user, require_super_admin
from app.engines.media.admin_service import MediaLibraryAdminService

router = APIRouter(prefix="/v1/admin/media", tags=["Admin — Media Library"])
signed_router = APIRouter(prefix="/v1/media", tags=["Media — Signed Access"])


class ArchiveMediaBody(BaseModel):
    reason: str = Field(default="Archived by administrator", min_length=3, max_length=500)


class VisibilityBody(BaseModel):
    is_public: bool


class ModerationBody(BaseModel):
    reason: str = Field(min_length=3, max_length=80)


class BulkMediaBody(BaseModel):
    ids: list[uuid.UUID] = Field(min_length=1, max_length=100)
    reason: str | None = Field(default=None, max_length=500)


class BulkDeleteBody(BulkMediaBody):
    force: bool = False


class BulkVisibilityBody(BulkMediaBody):
    is_public: bool


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "")


def _svc(
    db: AsyncSession = Depends(get_async_session),
    u: UserContext = Depends(require_super_admin),
) -> MediaLibraryAdminService:
    return MediaLibraryAdminService(db, u)


# ── Summary + filter options ─────────────────────────────────────────────────

@router.get("/summary", response_model=ApiResponse[dict])
async def get_media_summary(r: Request, svc: MediaLibraryAdminService = Depends(_svc), u: UserContext = Depends(require_super_admin)):
    return ok(await svc.get_summary(), _rid(r))


@router.get("/storage-summary", response_model=ApiResponse[dict])
async def get_storage_summary(r: Request, svc: MediaLibraryAdminService = Depends(_svc), u: UserContext = Depends(require_super_admin)):
    return ok(await svc.get_storage_summary(), _rid(r))


@router.get("/filter-options", response_model=ApiResponse[dict])
async def get_filter_options(r: Request, svc: MediaLibraryAdminService = Depends(_svc), u: UserContext = Depends(require_super_admin)):
    return ok(await svc.get_filter_options(), _rid(r))


# ── Enterprise list ──────────────────────────────────────────────────────────

@router.get("", response_model=ApiResponse[dict])
async def list_media(
    r: Request,
    q: str | None = Query(None),
    context: str | None = Query(None),
    owner_type: str | None = Query(None),
    visibility: str | None = Query(None),
    status: str | None = Query(None),
    moderation_status: str | None = Query(None),
    is_flagged: bool | None = Query(None),
    tenant_id: str | None = Query(None),
    customer_id: str | None = Query(None),
    file_type: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    sort: Literal["newest", "oldest", "largest", "smallest"] = Query("newest"),
    cursor: str | None = Query(None, max_length=1000),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    svc: MediaLibraryAdminService = Depends(_svc),
    u: UserContext = Depends(require_super_admin),
):
    return ok(await svc.list_assets_admin(
        q=q, context=context, owner_type=owner_type, visibility=visibility,
        status=status, moderation_status=moderation_status, is_flagged=is_flagged,
        tenant_id=tenant_id, customer_id=customer_id, file_type=file_type,
        date_from=date_from, date_to=date_to, sort=sort, cursor=cursor,
        page=page, page_size=page_size,
    ), _rid(r))


# ── Single asset ─────────────────────────────────────────────────────────────

@router.get("/{media_id}", response_model=ApiResponse[dict])
async def get_media_detail(
    r: Request,
    media_id: uuid.UUID,
    svc: MediaLibraryAdminService = Depends(_svc),
    u: UserContext = Depends(require_super_admin),
):
    return ok(await svc.get_detail(media_id), _rid(r))


@router.get("/{media_id}/linked-records", response_model=ApiResponse[list])
async def get_linked_records(
    r: Request,
    media_id: uuid.UUID,
    svc: MediaLibraryAdminService = Depends(_svc),
    u: UserContext = Depends(require_super_admin),
):
    return ok(await svc.get_linked_records(media_id), _rid(r))


@router.get("/{media_id}/audit-logs", response_model=ApiResponse[list])
async def get_audit_logs(
    r: Request,
    media_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=200),
    svc: MediaLibraryAdminService = Depends(_svc),
    u: UserContext = Depends(require_super_admin),
):
    return ok(await svc.get_audit_logs(media_id, limit=limit), _rid(r))


# ── Signed URLs ──────────────────────────────────────────────────────────────

@router.post("/{media_id}/signed-preview-url", response_model=ApiResponse[dict])
async def create_signed_preview_url(
    r: Request,
    media_id: uuid.UUID,
    svc: MediaLibraryAdminService = Depends(_svc),
    u: UserContext = Depends(require_super_admin),
):
    return ok(await svc.create_signed_preview_url(media_id), _rid(r))


@router.post("/{media_id}/signed-download-url", response_model=ApiResponse[dict])
async def create_signed_download_url(
    r: Request,
    media_id: uuid.UUID,
    svc: MediaLibraryAdminService = Depends(_svc),
    u: UserContext = Depends(require_super_admin),
):
    return ok(await svc.create_signed_download_url(media_id), _rid(r))


async def _serve_admin_media(db: AsyncSession, actor: UserContext, media_id: uuid.UUID, purpose: str):
    """Serve protected media through the API so browser previews avoid CDN CORS redirects."""
    from app.engines.media.asset_service import MediaAssetService
    from app.engines.media.models import MediaAsset
    from sqlalchemy import select

    asset = (await db.execute(select(MediaAsset).where(
        MediaAsset.id == media_id, MediaAsset.deleted_at.is_(None),
    ))).scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Media not found.")
    service = MediaAssetService(db=db, actor=actor)
    disposition = "inline" if purpose != "download" else "attachment"
    if asset.storage_driver == "local":
        path, mime_type = await service.get_local_file_for_serve(media_id)
        return FileResponse(
            str(path), media_type=mime_type or "application/octet-stream",
            headers={"Content-Disposition": f'{disposition}; filename="{asset.file_name_original}"',
                     "Cache-Control": "private, no-store"},
        )

    delivery_url, mime_type = await service.get_remote_url_for_serve(media_id)
    if not delivery_url.startswith("https://res.cloudinary.com/"):
        return RedirectResponse(url=delivery_url, status_code=302)

    import httpx
    client = httpx.AsyncClient(timeout=30.0, follow_redirects=False)
    try:
        response = await client.send(client.build_request("GET", delivery_url), stream=True)
        if response.status_code != 200:
            await response.aclose()
            await client.aclose()
            raise HTTPException(status_code=404, detail="Media file not available.")
    except Exception:
        await client.aclose()
        raise

    async def content():
        try:
            async for chunk in response.aiter_bytes():
                yield chunk
        finally:
            await response.aclose()
            await client.aclose()

    return StreamingResponse(
        content(), media_type=mime_type or "application/octet-stream",
        headers={"Content-Disposition": f'{disposition}; filename="{asset.file_name_original}"',
                 "Cache-Control": "private, no-store"},
    )


@router.get("/{media_id}/thumbnail", summary="Authenticated admin image thumbnail")
async def get_media_thumbnail(
    media_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_session),
    actor: UserContext = Depends(require_super_admin),
):
    from app.engines.media.models import MediaAsset
    from sqlalchemy import select

    asset = (await db.execute(select(MediaAsset).where(
        MediaAsset.id == media_id, MediaAsset.deleted_at.is_(None),
    ))).scalar_one_or_none()
    if not asset or not asset.mime_type.startswith("image/"):
        raise HTTPException(status_code=404, detail="Image not found.")
    await MediaLibraryAdminService(db, actor)._log_audit(media_id, "admin_thumbnail_accessed")
    return await _serve_admin_media(db, actor, media_id, "thumbnail")


# ── Lifecycle ────────────────────────────────────────────────────────────────

@router.post("/{media_id}/archive", response_model=ApiResponse[dict])
async def archive_media(
    r: Request,
    media_id: uuid.UUID,
    payload: ArchiveMediaBody,
    svc: MediaLibraryAdminService = Depends(_svc),
    u: UserContext = Depends(require_super_admin),
):
    return ok(await svc.archive_asset(media_id, reason=payload.reason), _rid(r))


@router.post("/{media_id}/restore", response_model=ApiResponse[dict])
async def restore_media(
    r: Request,
    media_id: uuid.UUID,
    svc: MediaLibraryAdminService = Depends(_svc),
    u: UserContext = Depends(require_super_admin),
):
    return ok(await svc.restore_asset(media_id), _rid(r))


@router.delete("/{media_id}", response_model=ApiResponse[dict])
async def delete_media(
    r: Request,
    media_id: uuid.UUID,
    force: bool = Query(False),
    svc: MediaLibraryAdminService = Depends(_svc),
    u: UserContext = Depends(require_super_admin),
):
    return ok(await svc.delete_asset(media_id, force=force), _rid(r))


@router.post("/{media_id}/change-visibility", response_model=ApiResponse[dict])
async def change_visibility(
    r: Request,
    media_id: uuid.UUID,
    payload: VisibilityBody,
    svc: MediaLibraryAdminService = Depends(_svc),
    u: UserContext = Depends(require_super_admin),
):
    return ok(await svc.change_visibility(media_id, payload.is_public), _rid(r))


# ── Moderation ───────────────────────────────────────────────────────────────

@router.post("/{media_id}/flag", response_model=ApiResponse[dict])
async def flag_media(
    r: Request,
    media_id: uuid.UUID,
    payload: ModerationBody,
    svc: MediaLibraryAdminService = Depends(_svc),
    u: UserContext = Depends(require_super_admin),
):
    return ok(await svc.flag_asset(media_id, reason=payload.reason), _rid(r))


@router.post("/{media_id}/mark-clean", response_model=ApiResponse[dict])
async def mark_clean(
    r: Request,
    media_id: uuid.UUID,
    svc: MediaLibraryAdminService = Depends(_svc),
    u: UserContext = Depends(require_super_admin),
):
    return ok(await svc.mark_clean(media_id), _rid(r))


@router.post("/{media_id}/quarantine", response_model=ApiResponse[dict])
async def quarantine_media(
    r: Request,
    media_id: uuid.UUID,
    payload: ModerationBody,
    svc: MediaLibraryAdminService = Depends(_svc),
    u: UserContext = Depends(require_super_admin),
):
    return ok(await svc.quarantine_asset(media_id, reason=payload.reason), _rid(r))


# ── Bulk ─────────────────────────────────────────────────────────────────────

@router.post("/bulk/archive", response_model=ApiResponse[dict])
async def bulk_archive(
    r: Request,
    payload: BulkMediaBody,
    svc: MediaLibraryAdminService = Depends(_svc),
    u: UserContext = Depends(require_super_admin),
):
    return ok(await svc.bulk_archive([str(value) for value in payload.ids]), _rid(r))


@router.post("/bulk/delete", response_model=ApiResponse[dict])
async def bulk_delete(
    r: Request,
    payload: BulkDeleteBody,
    svc: MediaLibraryAdminService = Depends(_svc),
    u: UserContext = Depends(require_super_admin),
):
    return ok(await svc.bulk_delete([str(value) for value in payload.ids], force=payload.force), _rid(r))


@router.post("/bulk/change-visibility", response_model=ApiResponse[dict])
async def bulk_change_visibility(
    r: Request,
    payload: BulkVisibilityBody,
    svc: MediaLibraryAdminService = Depends(_svc),
    u: UserContext = Depends(require_super_admin),
):
    done, failed = [], []
    for media_id in payload.ids:
        mid_str = str(media_id)
        try:
            await svc.change_visibility(media_id, payload.is_public)
            done.append(mid_str)
        except Exception as e:
            failed.append({"id": mid_str, "error": str(e)})
    return ok({"updated": done, "failed": failed}, _rid(r))


# ── Export ───────────────────────────────────────────────────────────────────

@router.get("/export/csv")
async def export_csv(
    r: Request,
    q: str | None = Query(None),
    context: str | None = Query(None),
    owner_type: str | None = Query(None),
    visibility: str | None = Query(None),
    status: str | None = Query(None),
    is_flagged: bool | None = Query(None),
    file_type: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    sort: Literal["newest", "oldest", "largest", "smallest"] = Query("newest"),
    svc: MediaLibraryAdminService = Depends(_svc),
    u: UserContext = Depends(require_super_admin),
):
    csv_text = await svc.export_csv(
        q=q, context=context, owner_type=owner_type, visibility=visibility,
        status=status, is_flagged=is_flagged, file_type=file_type,
        date_from=date_from, date_to=date_to, sort=sort,
    )
    return StreamingResponse(
        iter([csv_text]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=media_export.csv"},
    )


# ── Signed token resolution (public route — token IS the credential) ─────────

@signed_router.get("/signed/{token}")
async def resolve_signed_media(
    token: str,
    r: Request,
    db: AsyncSession = Depends(get_async_session),
    u: UserContext = Depends(get_current_user),
):
    """
    Resolve a signed preview/download URL token.
    The token is single-use and expires. Requires the requester to still be
    authenticated (the token proves which file, not who can access anything).
    """
    from app.engines.media.admin_service import MediaLibraryAdminService
    import uuid as _uuid

    svc = MediaLibraryAdminService(db, u)
    info = await svc.resolve_signed_token(token)

    media_id = _uuid.UUID(info["media_id"])
    purpose = info["purpose"]

    await svc._log_audit(media_id, f"signed_{purpose}_accessed",
                         {"token": token[:12] + "...", "purpose": purpose})
    return await _serve_admin_media(db, u, media_id, purpose)
