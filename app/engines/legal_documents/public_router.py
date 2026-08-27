"""Legal Documents — public read API (`/v1/public/legal/*`).

Unauthenticated by design. These documents are what a person reads BEFORE
they have an account: the signup consent checkbox links to them, and the
mobile apps show them on the login screen. Requiring a session would make the
one moment they matter most the one moment they are unreachable.

Only published, already-effective versions are ever served — see
``service.get_live``.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.db import get_db
from app.schemas.base import ApiResponse, ok

from app.engines.legal_documents import constants as C
from app.engines.legal_documents import service as svc

router = APIRouter(prefix="/v1/public/legal", tags=["Public — Legal Documents"])


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", None) or r.headers.get("X-Request-ID", "—")


@router.get("", response_model=ApiResponse[dict],
            summary="List the legal documents that are currently in force")
async def list_documents(
    r: Request,
    audience: str = Query(C.AUDIENCE_ALL),
    locale: str = Query(C.DEFAULT_LOCALE),
    db: AsyncSession = Depends(get_db),
):
    """Index for a footer or a settings screen.

    Returns only document types with a live version, so every entry is
    guaranteed to resolve.
    """
    documents = await svc.list_live(db, audience=audience, locale=locale)
    return ok({"documents": documents, "total": len(documents)},
              _rid(r), engine_id=C.ENGINE_ID)


@router.get("/{doc_type}", response_model=ApiResponse[dict],
            summary="Read the legal document currently in force")
async def get_document(
    doc_type: str,
    r: Request,
    audience: str = Query(C.AUDIENCE_ALL),
    locale: str = Query(C.DEFAULT_LOCALE),
    db: AsyncSession = Depends(get_db),
):
    row = await svc.require_live(db, doc_type=doc_type, audience=audience, locale=locale)
    return ok(row.to_public_dict(), _rid(r), engine_id=C.ENGINE_ID)


@router.get("/{doc_type}/versions/{version_id}", response_model=ApiResponse[dict],
            summary="Read one specific version by id")
async def get_document_version(
    doc_type: str,
    version_id: str,
    r: Request,
    db: AsyncSession = Depends(get_db),
):
    """Resolve a version referenced by a consent record.

    A person is entitled to read the exact text they agreed to, which by then
    is usually archived. Archived versions are therefore readable here, but
    drafts are not — an unpublished draft is not a document anyone agreed to
    and must not leak before it is published.
    """
    import uuid as _uuid

    from app.exceptions import ServiceOSException

    try:
        parsed = _uuid.UUID(version_id)
    except ValueError:
        raise ServiceOSException(
            "LEGAL_DOC_VERSION_NOT_FOUND",
            "That legal document version does not exist.",
            status_code=404,
        )

    row = await svc.get_version(db, parsed)
    if row.doc_type != doc_type or row.status == C.STATUS_DRAFT:
        raise ServiceOSException(
            "LEGAL_DOC_VERSION_NOT_FOUND",
            "That legal document version does not exist.",
            status_code=404,
        )
    return ok(row.to_public_dict(), _rid(r), engine_id=C.ENGINE_ID)
