"""Knowledge Base Enterprise Router — /v1/admin/intelligence/knowledge-bases (migration 104)."""
from __future__ import annotations
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import require_super_admin
from app.dependencies.db import get_db
from app.engines.analytics.kb_service import KnowledgeBaseService
from app.schemas.base import ok

_svc = KnowledgeBaseService()


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


router = APIRouter(
    prefix="/v1/admin/intelligence/knowledge-bases",
    tags=["Knowledge Base Enterprise"],
    dependencies=[Depends(require_super_admin)],
)


# ── Static paths FIRST ────────────────────────────────────────────────────────

@router.get("/summary")
async def get_kb_summary(r: Request, db: AsyncSession = Depends(get_db)):
    data = await _svc.get_kb_summary(db)
    return ok(data, _rid(r), "kb.summary")


@router.post("/seed-defaults/preview")
async def seed_defaults_preview(r: Request, db: AsyncSession = Depends(get_db)):
    data = await _svc.seed_defaults_preview(db)
    return ok(data, _rid(r), "kb.seed_defaults.preview")


@router.post("/seed-defaults")
async def seed_defaults(r: Request, db: AsyncSession = Depends(get_db)):
    data = await _svc.seed_defaults(db, None)
    return ok(data, _rid(r), "kb.seed_defaults")


@router.get("")
async def list_kbs(
    r: Request, db: AsyncSession = Depends(get_db),
    q: Optional[str] = Query(None),
    scope_type: Optional[str] = Query(None),
    vertical: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    knowledge_type: Optional[str] = Query(None),
    customer_visible: Optional[bool] = Query(None),
    rag_enabled: Optional[bool] = Query(None),
    indexing_status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    sort_by: str = Query("created_at"),
    sort_dir: str = Query("desc"),
):
    data = await _svc.list_kbs(
        db, q=q, scope_type=scope_type, vertical=vertical, status=status,
        knowledge_type=knowledge_type, customer_visible=customer_visible,
        rag_enabled=rag_enabled, indexing_status=indexing_status,
        page=page, page_size=page_size, sort_by=sort_by, sort_dir=sort_dir,
    )
    return ok(data, _rid(r), "kb.list")


@router.post("")
async def create_kb(payload: dict, r: Request, db: AsyncSession = Depends(get_db)):
    data = await _svc.create_kb(db, payload, None)
    return ok(data, _rid(r), "kb.create")


# ── Parameterized paths ───────────────────────────────────────────────────────

@router.get("/{kb_id}")
async def get_kb(kb_id: str, r: Request, db: AsyncSession = Depends(get_db)):
    data = await _svc.get_kb(db, kb_id)
    return ok(data, _rid(r), "kb.get")


@router.put("/{kb_id}")
async def update_kb(kb_id: str, payload: dict, r: Request, db: AsyncSession = Depends(get_db)):
    data = await _svc.update_kb(db, kb_id, payload, None)
    return ok(data, _rid(r), "kb.update")


@router.post("/{kb_id}/activate")
async def activate_kb(kb_id: str, r: Request, db: AsyncSession = Depends(get_db)):
    data = await _svc.activate_kb(db, kb_id, None)
    return ok(data, _rid(r), "kb.activate")


@router.post("/{kb_id}/disable")
async def disable_kb(kb_id: str, r: Request, db: AsyncSession = Depends(get_db)):
    data = await _svc.disable_kb(db, kb_id, None)
    return ok(data, _rid(r), "kb.disable")


@router.post("/{kb_id}/archive")
async def archive_kb(kb_id: str, r: Request, db: AsyncSession = Depends(get_db)):
    data = await _svc.archive_kb(db, kb_id, None)
    return ok(data, _rid(r), "kb.archive")


@router.delete("/{kb_id}")
async def delete_kb(kb_id: str, r: Request, db: AsyncSession = Depends(get_db)):
    await _svc.delete_kb(db, kb_id, None)
    return ok({"deleted": True}, _rid(r), "kb.delete")


# ── Documents ─────────────────────────────────────────────────────────────────

@router.post("/{kb_id}/documents/upload")
async def upload_document(kb_id: str, payload: dict, r: Request, db: AsyncSession = Depends(get_db)):
    data = await _svc.upload_document(
        db, kb_id,
        name=payload.get("document_name", "unnamed"),
        source_type=payload.get("source_type", "uploaded"),
        file_type=payload.get("file_type"),
        size_bytes=int(payload.get("file_size_bytes", 0)),
        user_id=None,
    )
    return ok(data, _rid(r), "kb.document.upload")


@router.post("/{kb_id}/documents/link-media")
async def link_media(kb_id: str, payload: dict, r: Request, db: AsyncSession = Depends(get_db)):
    data = await _svc.upload_document(
        db, kb_id,
        name=payload.get("document_name", "media"),
        source_type="media",
        file_type=payload.get("file_type"),
        size_bytes=0,
        user_id=None,
    )
    return ok(data, _rid(r), "kb.document.link_media")


@router.post("/{kb_id}/sources/url")
async def add_url_source(kb_id: str, payload: dict, r: Request, db: AsyncSession = Depends(get_db)):
    data = await _svc.upload_document(
        db, kb_id,
        name=payload.get("url", "url_source"),
        source_type="url",
        file_type="html",
        size_bytes=0,
        user_id=None,
    )
    return ok(data, _rid(r), "kb.document.url_source")


@router.get("/{kb_id}/documents")
async def list_documents(kb_id: str, r: Request, db: AsyncSession = Depends(get_db)):
    data = await _svc.list_documents(db, kb_id)
    return ok(data, _rid(r), "kb.documents.list")


@router.delete("/{kb_id}/documents/{document_id}")
async def delete_document(kb_id: str, document_id: str, r: Request, db: AsyncSession = Depends(get_db)):
    await _svc.delete_document(db, kb_id, document_id, None)
    return ok({"deleted": True}, _rid(r), "kb.document.delete")


# ── Articles ──────────────────────────────────────────────────────────────────

@router.post("/{kb_id}/articles")
async def create_article(kb_id: str, payload: dict, r: Request, db: AsyncSession = Depends(get_db)):
    data = await _svc.create_article(db, kb_id, payload, None)
    return ok(data, _rid(r), "kb.article.create")


@router.get("/{kb_id}/articles")
async def list_articles(kb_id: str, r: Request, db: AsyncSession = Depends(get_db)):
    data = await _svc.list_articles(db, kb_id)
    return ok(data, _rid(r), "kb.articles.list")


@router.put("/{kb_id}/articles/{article_id}")
async def update_article(kb_id: str, article_id: str, payload: dict, r: Request, db: AsyncSession = Depends(get_db)):
    data = await _svc.update_article(db, kb_id, article_id, payload, None)
    return ok(data, _rid(r), "kb.article.update")


@router.post("/{kb_id}/articles/{article_id}/publish")
async def publish_article(kb_id: str, article_id: str, r: Request, db: AsyncSession = Depends(get_db)):
    data = await _svc.publish_article(db, kb_id, article_id, None)
    return ok(data, _rid(r), "kb.article.publish")


# ── Indexing ──────────────────────────────────────────────────────────────────

@router.post("/{kb_id}/index")
async def trigger_index(kb_id: str, r: Request, db: AsyncSession = Depends(get_db)):
    data = await _svc.trigger_index(db, kb_id, None, is_reindex=False)
    return ok(data, _rid(r), "kb.index.trigger")


@router.post("/{kb_id}/reindex")
async def trigger_reindex(kb_id: str, r: Request, db: AsyncSession = Depends(get_db)):
    data = await _svc.trigger_index(db, kb_id, None, is_reindex=True)
    return ok(data, _rid(r), "kb.reindex.trigger")


@router.get("/{kb_id}/indexing-jobs")
async def list_indexing_jobs(kb_id: str, r: Request, db: AsyncSession = Depends(get_db)):
    data = await _svc.list_indexing_jobs(db, kb_id)
    return ok(data, _rid(r), "kb.indexing_jobs.list")


@router.get("/{kb_id}/chunks")
async def list_chunks(
    kb_id: str, r: Request, db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
):
    data = await _svc.list_chunks(db, kb_id, page=page, page_size=page_size)
    return ok(data, _rid(r), "kb.chunks.list")


# ── Query ─────────────────────────────────────────────────────────────────────

@router.post("/{kb_id}/test-query")
async def test_query(kb_id: str, payload: dict, r: Request, db: AsyncSession = Depends(get_db)):
    data = await _svc.test_query(
        db, kb_id,
        query_text=payload.get("query_text", payload.get("query", "")),
        app_scope=payload.get("app_scope", "admin_app"),
        user_id=None,
    )
    return ok(data, _rid(r), "kb.test_query")


@router.get("/{kb_id}/query-logs")
async def list_query_logs(
    kb_id: str, r: Request, db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
):
    data = await _svc.list_query_logs(db, kb_id, page=page, page_size=page_size)
    return ok(data, _rid(r), "kb.query_logs.list")


@router.get("/{kb_id}/retrieval-quality")
async def get_retrieval_quality(kb_id: str, r: Request, db: AsyncSession = Depends(get_db)):
    data = await _svc.get_retrieval_quality(db, kb_id)
    return ok(data, _rid(r), "kb.retrieval_quality")


# ── Access Preview ────────────────────────────────────────────────────────────

@router.post("/{kb_id}/access-preview")
async def preview_access(kb_id: str, payload: dict, r: Request, db: AsyncSession = Depends(get_db)):
    data = await _svc.preview_access(db, kb_id, role=payload.get("role", "admin"), app_scope=payload.get("app_scope", "admin_app"))
    return ok(data, _rid(r), "kb.access_preview")


# ── Audit & Versions ──────────────────────────────────────────────────────────

@router.get("/{kb_id}/audit-logs")
async def get_audit_logs(kb_id: str, r: Request, db: AsyncSession = Depends(get_db)):
    data = await _svc.get_audit_logs(db, kb_id)
    return ok(data, _rid(r), "kb.audit_logs")


@router.get("/{kb_id}/versions")
async def get_versions(kb_id: str, r: Request, db: AsyncSession = Depends(get_db)):
    data = await _svc.get_versions(db, kb_id)
    return ok(data, _rid(r), "kb.versions")
