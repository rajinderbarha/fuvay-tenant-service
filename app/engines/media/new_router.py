"""
Media Engine — Phase 0A Router.

Endpoints:
  POST   /v1/media/upload           — multipart upload
  GET    /v1/media                  — list assets (paginated, scoped)
  GET    /v1/media/{media_id}       — get asset metadata
  GET    /v1/media/{media_id}/view  — serve/redirect to file
  POST   /v1/media/{media_id}/replace — replace file
  DELETE /v1/media/{media_id}       — soft delete

Profile photo shortcuts:
  POST   /v1/me/profile-photo       — upload own profile photo
  DELETE /v1/me/profile-photo       — remove own profile photo
  POST   /v1/customer/profile/photo — customer profile photo
  DELETE /v1/customer/profile/photo — remove customer photo
  POST   /v1/provider/profile/logo  — provider business logo
  DELETE /v1/provider/profile/logo  — remove provider logo

All endpoints require authentication.
"""
from __future__ import annotations

import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile, status
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_staff_or_above_mutation, require_mutation_access_scope
from app.dependencies.auth import (
    UserContext,
    get_current_user,
    require_customer,
    require_technician,
)
from app.dependencies.db import get_db
from app.engines.media.asset_service import MediaAssetService
from app.schemas.base import ApiResponse, ok

logger = structlog.get_logger("media.new_router")


def _req_id(r: Request) -> str:
    return getattr(r.state, "request_id", "")

# ── Media assets router ───────────────────────────────────────────────────────
router = APIRouter(prefix="/v1/media", tags=["Media"])


def _svc(
    db: AsyncSession = Depends(get_db),
    actor: UserContext = Depends(get_current_user),
) -> MediaAssetService:
    return MediaAssetService(db=db, actor=actor)


@router.post(
    "/upload",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[dict],
    summary="Upload a file (multipart/form-data)",
    description=(
        "Upload any file through the Media Engine. "
        "`media_context` must be a valid context (e.g. `provider_document`, `complaint_evidence`). "
        "`owner_type` and `owner_id` identify what entity owns this file. "
        "tenant_id and customer_id are extracted from JWT — never trusted from the request body."
    ),
)
async def upload_media(
    r: Request,
    file: Annotated[UploadFile, File(description="The file to upload")],
    media_context: Annotated[str, Form(description="Media context (e.g. provider_document)")],
    owner_type: Annotated[str, Form(description="Owner type (e.g. tenant, user, customer)")] = "user",
    owner_id: Annotated[str | None, Form(description="Owner UUID")] = None,
    is_public: Annotated[bool, Form(description="Make file publicly accessible")] = False,
    actor: UserContext = Depends(require_mutation_access_scope),
    svc: MediaAssetService = Depends(_svc),
) -> ApiResponse[dict]:
    # Default owner_id to the actor's own ID
    effective_owner_id = owner_id or actor.user_id
    data = await svc.upload(
        file=file,
        media_context=media_context,
        owner_type=owner_type,
        owner_id=effective_owner_id,
        is_public=is_public,
    )
    # Real bug fixed here: `ok()` ALREADY builds the {data, links, meta}
    # envelope, so wrapping the payload in another {"success", "data"} made
    # this the only media route that returned a double envelope -- a client
    # reading `response.data.preview_url` got undefined, because the asset
    # was actually at `response.data.data.preview_url`. Every other route in
    # this file (list_media, get_media) passes `data` straight through.
    return ok(data, _req_id(r))


@router.get(
    "",
    response_model=ApiResponse[dict],
    summary="List media assets (paginated, actor-scoped)",
)
async def list_media(
    r: Request,
    media_context: str | None = Query(None),
    owner_type: str | None = Query(None),
    owner_id: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    actor: UserContext = Depends(get_current_user),
    svc: MediaAssetService = Depends(_svc),
) -> ApiResponse[dict]:
    data = await svc.list_assets(
        media_context=media_context,
        owner_type=owner_type,
        owner_id=owner_id,
        page=page,
        page_size=page_size,
    )
    return ok(data, _req_id(r))


@router.get(
    "/{media_id}",
    response_model=ApiResponse[dict],
    summary="Get media asset metadata",
)
async def get_media(
    media_id: uuid.UUID,
    r: Request,
    actor: UserContext = Depends(get_current_user),
    svc: MediaAssetService = Depends(_svc),
) -> ApiResponse[dict]:
    data = await svc.get_asset(media_id)
    return ok(data, _req_id(r))


@router.get(
    "/{media_id}/view",
    summary="View/serve a media file (access-checked)",
    response_class=FileResponse,
)
async def view_media(
    media_id: uuid.UUID,
    r: Request,
    actor: UserContext = Depends(get_current_user),
    svc: MediaAssetService = Depends(_svc),
):
    """
    Serves local files directly; redirects to CDN URL for remote storage.
    Performs access check before serving — private files never bypass auth.

    BUG FIX (2026-08-04): the "redirects to CDN URL for remote storage" this
    docstring promised never actually happened for cloudinary-stored assets
    -- to_dict() didn't expose storage_key, and the only thing checked here
    (data.get("preview_url")) is always the self-referential
    "/v1/media/{id}/view" path (doesn't start with "http"), so this always
    fell through to 404 "File not available." for every cloudinary asset,
    confirmed live (10 of 16 media assets platform-wide use cloudinary).
    app.cloudinary_client.build_delivery_url already existed and is used by
    the OLDER media/service.py engine, but was never wired into this one.
    """
    try:
        path, mime_type = await svc.get_local_file_for_serve(media_id)
        return FileResponse(str(path), media_type=mime_type)
    except Exception:
        # Not a local file — try redirect to CDN or StaticFiles URL
        try:
            data = await svc.get_asset(media_id)
        except Exception:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="File not available.")
        preview_url = data.get("preview_url") or data.get("public_url")
        if preview_url and preview_url.startswith("http"):
            return RedirectResponse(url=preview_url, status_code=302)
        if data.get("storage_driver") == "cloudinary" and data.get("storage_key"):
            from app.cloudinary_client import build_delivery_url
            resource_type = "image" if str(data.get("mime_type", "")).startswith("image/") else "raw"
            return RedirectResponse(url=build_delivery_url(data["storage_key"], resource_type), status_code=302)
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="File not available.")


@router.get(
    "/{media_id}/download",
    summary="Download a media file (Content-Disposition: attachment)",
    response_class=FileResponse,
)
async def download_media(
    media_id: uuid.UUID,
    r: Request,
    actor: UserContext = Depends(get_current_user),
    svc: MediaAssetService = Depends(_svc),
):
    """
    Forces file download (Content-Disposition: attachment).
    Performs same access check as /view.
    For CDN-stored files, redirects to public URL (browser handles download).
    """
    try:
        path, mime_type = await svc.get_local_file_for_serve(media_id)
        asset_data = await svc.get_asset(media_id)
        filename = asset_data.get("file_name_original", "download")
        return FileResponse(
            str(path),
            media_type=mime_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception:
        try:
            data = await svc.get_asset(media_id)
        except Exception:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="File not available.")
        preview_url = data.get("preview_url") or data.get("public_url")
        if preview_url and preview_url.startswith("http"):
            return RedirectResponse(url=preview_url, status_code=302)
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="File not available.")


@router.post(
    "/{media_id}/replace",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[dict],
    summary="Replace a media file (marks old as replaced)",
)
async def replace_media(
    media_id: uuid.UUID,
    r: Request,
    file: Annotated[UploadFile, File()],
    is_public: Annotated[bool, Form()] = False,
    actor: UserContext = Depends(require_mutation_access_scope),
    svc: MediaAssetService = Depends(_svc),
) -> ApiResponse[dict]:
    data = await svc.replace_asset(media_id=media_id, file=file, is_public=is_public)
    return ok(data, _req_id(r))


@router.delete(
    "/{media_id}",
    response_model=ApiResponse[dict],
    summary="Soft-delete a media asset",
)
async def delete_media(
    media_id: uuid.UUID,
    r: Request,
    actor: UserContext = Depends(get_current_user),
    svc: MediaAssetService = Depends(_svc),
) -> ApiResponse[dict]:
    data = await svc.delete_asset(media_id)
    return ok(data, _req_id(r))


# ── Profile photo shortcuts ───────────────────────────────────────────────────

profile_router = APIRouter(prefix="/v1", tags=["Profile Media"])


@profile_router.post(
    "/me/profile-photo",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[dict],
    summary="Upload own profile photo",
)
async def upload_my_profile_photo(
    r: Request,
    file: Annotated[UploadFile, File()],
    actor: UserContext = Depends(get_current_user),
    svc: MediaAssetService = Depends(_svc),
) -> ApiResponse[dict]:
    data = await svc.set_user_profile_photo(file)
    return ok(data, _req_id(r))


@profile_router.delete(
    "/me/profile-photo",
    response_model=ApiResponse[dict],
    summary="Remove own profile photo",
)
async def remove_my_profile_photo(
    r: Request,
    actor: UserContext = Depends(get_current_user),
    svc: MediaAssetService = Depends(_svc),
) -> ApiResponse[dict]:
    data = await svc.remove_user_profile_photo()
    return ok(data, _req_id(r))


@profile_router.post(
    "/customer/profile/photo",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[dict],
    summary="Customer: upload profile photo",
)
async def upload_customer_profile_photo(
    r: Request,
    file: Annotated[UploadFile, File()],
    actor: UserContext = Depends(require_customer),
    svc: MediaAssetService = Depends(_svc),
) -> ApiResponse[dict]:
    data = await svc.set_user_profile_photo(file)
    return ok(data, _req_id(r))


@profile_router.delete(
    "/customer/profile/photo",
    response_model=ApiResponse[dict],
    summary="Customer: remove profile photo",
)
async def remove_customer_profile_photo(
    r: Request,
    actor: UserContext = Depends(require_customer),
    svc: MediaAssetService = Depends(_svc),
) -> ApiResponse[dict]:
    data = await svc.remove_user_profile_photo()
    return ok(data, _req_id(r))


@profile_router.post(
    "/provider/profile/logo",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[dict],
    summary="Provider: upload business logo",
)
async def upload_provider_logo(
    r: Request,
    file: Annotated[UploadFile, File()],
    actor: UserContext = Depends(require_staff_or_above_mutation),
    svc: MediaAssetService = Depends(_svc),
) -> ApiResponse[dict]:
    data = await svc.set_tenant_business_logo(file)
    return ok(data, _req_id(r))


@profile_router.delete(
    "/provider/profile/logo",
    response_model=ApiResponse[dict],
    summary="Provider: remove business logo",
)
async def remove_provider_logo(
    media_id: uuid.UUID,
    r: Request,
    actor: UserContext = Depends(require_staff_or_above_mutation),
    svc: MediaAssetService = Depends(_svc),
) -> ApiResponse[dict]:
    data = await svc.remove_tenant_business_logo(media_id)
    return ok(data, _req_id(r))


@profile_router.post(
    "/provider/profile/shop-photo",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[dict],
    summary="Provider: upload shop / storefront photo",
)
async def upload_provider_shop_photo(
    r: Request,
    file: Annotated[UploadFile, File()],
    actor: UserContext = Depends(require_staff_or_above_mutation),
    svc: MediaAssetService = Depends(_svc),
) -> ApiResponse[dict]:
    data = await svc.set_tenant_shop_photo(file)
    return ok(data, _req_id(r))


@profile_router.delete(
    "/provider/profile/shop-photo",
    response_model=ApiResponse[dict],
    summary="Provider: remove shop photo",
)
async def remove_provider_shop_photo(
    media_id: uuid.UUID,
    r: Request,
    actor: UserContext = Depends(require_staff_or_above_mutation),
    svc: MediaAssetService = Depends(_svc),
) -> ApiResponse[dict]:
    data = await svc.remove_tenant_shop_photo(media_id)
    return ok(data, _req_id(r))


@profile_router.post(
    "/staff/profile/photo",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[dict],
    summary="Staff: upload profile photo",
)
async def upload_staff_profile_photo(
    r: Request,
    file: Annotated[UploadFile, File()],
    actor: UserContext = Depends(require_staff_or_above_mutation),
    svc: MediaAssetService = Depends(_svc),
) -> ApiResponse[dict]:
    data = await svc.set_user_profile_photo(file)
    return ok(data, _req_id(r))


@profile_router.delete(
    "/staff/profile/photo",
    response_model=ApiResponse[dict],
    summary="Staff: remove profile photo",
)
async def remove_staff_profile_photo(
    r: Request,
    actor: UserContext = Depends(require_staff_or_above_mutation),
    svc: MediaAssetService = Depends(_svc),
) -> ApiResponse[dict]:
    data = await svc.remove_user_profile_photo()
    return ok(data, _req_id(r))
