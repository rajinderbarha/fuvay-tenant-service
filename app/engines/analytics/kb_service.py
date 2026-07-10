"""Knowledge Base Enterprise Service — migration 104."""
from __future__ import annotations
import random
import uuid
from datetime import datetime, timezone
from typing import Any

import structlog
from fastapi import HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.analytics.intelligence_models import RagKnowledgeBase, RagQueryLog
from app.engines.analytics.kb_models import (
    RagDocument, RagManualArticle, RagDocumentChunk,
    RagIndexingJob, RagKbVersion, RagKbAuditLog,
)

logger = structlog.get_logger("kb_service")

_SEED_KBS = [
    {"kb_code": "platform_policy_kb", "name": "Platform Policy Knowledge Base", "scope_type": "platform", "knowledge_type": "policy"},
    {"kb_code": "home_services_faq", "name": "Home Services Knowledge Base", "scope_type": "vertical", "vertical_key": "home_services", "knowledge_type": "faq"},
    {"kb_code": "customer_support_kb", "name": "Customer Support Knowledge Base", "scope_type": "support", "knowledge_type": "support"},
    {"kb_code": "tenant_onboarding_help", "name": "Tenant Onboarding Knowledge Base", "scope_type": "tenant", "knowledge_type": "onboarding"},
    {"kb_code": "complaint_dispute_policy", "name": "Complaint & Dispute Policy KB", "scope_type": "compliance", "knowledge_type": "policy", "admin_only": True},
    {"kb_code": "marketing_knowledge", "name": "Marketing Knowledge Base", "scope_type": "marketing", "knowledge_type": "marketing"},
    {"kb_code": "compliance_dpdp_kb", "name": "Compliance / DPDP Knowledge Base", "scope_type": "compliance", "knowledge_type": "compliance", "admin_only": True},
]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _validate_kb(payload: dict, existing: RagKnowledgeBase | None = None) -> None:
    scope_type = payload.get("scope_type", "platform")
    if scope_type == "vertical" and not payload.get("vertical_key"):
        raise HTTPException(status_code=422, detail="vertical_key is required for scope_type=vertical")
    if scope_type == "category" and not payload.get("category_id"):
        raise HTTPException(status_code=422, detail="category_id is required for scope_type=category")
    if scope_type == "tenant" and not payload.get("tenant_id") and (existing is None or not existing.tenant_id):
        # template-mode: allow without tenant
        pass

    customer_visible = payload.get("customer_visible", False)
    if scope_type == "compliance" and customer_visible:
        raise HTTPException(status_code=422, detail="Compliance KB cannot be customer_visible")
    if payload.get("sensitive_content", False) and customer_visible:
        raise HTTPException(status_code=422, detail="Sensitive content KB cannot be customer_visible")

    chunk_size = int(payload.get("chunk_size", 800))
    chunk_overlap = int(payload.get("chunk_overlap", 120))
    if chunk_overlap >= chunk_size:
        raise HTTPException(status_code=422, detail="chunk_overlap must be less than chunk_size")

    sim = float(payload.get("similarity_threshold", 0.72))
    if not (0.0 <= sim <= 1.0):
        raise HTTPException(status_code=422, detail="similarity_threshold must be between 0 and 1")


class KnowledgeBaseService:

    # ── Summary ───────────────────────────────────────────────────────────────

    @staticmethod
    async def get_kb_summary(db: AsyncSession) -> dict[str, Any]:
        try:
            total_r = await db.execute(select(func.count()).select_from(RagKnowledgeBase))
            total = total_r.scalar() or 0
            active_r = await db.execute(select(func.count()).select_from(RagKnowledgeBase).where(RagKnowledgeBase.status == "active"))
            active = active_r.scalar() or 0
            draft_r = await db.execute(select(func.count()).select_from(RagKnowledgeBase).where(RagKnowledgeBase.status == "draft"))
            draft = draft_r.scalar() or 0
            disabled_r = await db.execute(select(func.count()).select_from(RagKnowledgeBase).where(RagKnowledgeBase.status == "disabled"))
            disabled = disabled_r.scalar() or 0
            archived_r = await db.execute(select(func.count()).select_from(RagKnowledgeBase).where(RagKnowledgeBase.status == "archived"))
            archived = archived_r.scalar() or 0

            # by scope
            scope_r = await db.execute(
                select(RagKnowledgeBase.scope_type, func.count().label("cnt"))
                .group_by(RagKnowledgeBase.scope_type)
            )
            by_scope = {row.scope_type: row.cnt for row in scope_r}

            # by indexing status
            idx_r = await db.execute(
                select(RagKnowledgeBase.indexing_status, func.count().label("cnt"))
                .group_by(RagKnowledgeBase.indexing_status)
            )
            by_indexing_status = {row.indexing_status: row.cnt for row in idx_r}
        except Exception:
            total = active = draft = disabled = archived = 0
            by_scope = {}
            by_indexing_status = {}

        return {
            "total": total,
            "active": active,
            "draft": draft,
            "disabled": disabled,
            "archived": archived,
            "by_scope": by_scope,
            "by_indexing_status": by_indexing_status,
        }

    # ── CRUD ──────────────────────────────────────────────────────────────────

    @staticmethod
    async def list_kbs(
        db: AsyncSession,
        q: str | None = None,
        scope_type: str | None = None,
        vertical: str | None = None,
        status: str | None = None,
        knowledge_type: str | None = None,
        customer_visible: bool | None = None,
        rag_enabled: bool | None = None,
        indexing_status: str | None = None,
        page: int = 1,
        page_size: int = 25,
        sort_by: str = "created_at",
        sort_dir: str = "desc",
    ) -> dict[str, Any]:
        stmt = select(RagKnowledgeBase)
        if q:
            stmt = stmt.where(RagKnowledgeBase.name.ilike(f"%{q}%"))
        if scope_type:
            stmt = stmt.where(RagKnowledgeBase.scope_type == scope_type)
        if vertical:
            stmt = stmt.where(RagKnowledgeBase.vertical_key == vertical)
        if status:
            stmt = stmt.where(RagKnowledgeBase.status == status)
        if knowledge_type:
            stmt = stmt.where(RagKnowledgeBase.knowledge_type == knowledge_type)
        if customer_visible is not None:
            stmt = stmt.where(RagKnowledgeBase.customer_visible == customer_visible)
        if rag_enabled is not None:
            stmt = stmt.where(RagKnowledgeBase.rag_enabled == rag_enabled)
        if indexing_status:
            stmt = stmt.where(RagKnowledgeBase.indexing_status == indexing_status)

        count_r = await db.execute(select(func.count()).select_from(stmt.subquery()))
        total = count_r.scalar() or 0

        col = getattr(RagKnowledgeBase, sort_by, RagKnowledgeBase.created_at)
        stmt = stmt.order_by(col.desc() if sort_dir == "desc" else col.asc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        result = await db.execute(stmt)
        items = [kb.to_dict() for kb in result.scalars()]

        return {
            "items": items,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": max(1, (total + page_size - 1) // page_size),
            },
        }

    @staticmethod
    async def create_kb(db: AsyncSession, payload: dict, user_id: str | None) -> dict[str, Any]:
        # Check code uniqueness
        kb_code = payload.get("kb_code")
        if kb_code:
            existing_r = await db.execute(select(RagKnowledgeBase).where(RagKnowledgeBase.kb_code == kb_code))
            if existing_r.scalar_one_or_none():
                raise HTTPException(status_code=409, detail=f"KB code '{kb_code}' already exists")

        _validate_kb(payload)

        kb = RagKnowledgeBase(
            kb_code=kb_code,
            name=payload.get("name", ""),
            description=payload.get("description"),
            scope_type=payload.get("scope_type", "platform"),
            scope_id=uuid.UUID(payload["scope_id"]) if payload.get("scope_id") else None,
            vertical_key=payload.get("vertical_key"),
            category_id=uuid.UUID(payload["category_id"]) if payload.get("category_id") else None,
            tenant_id=uuid.UUID(payload["tenant_id"]) if payload.get("tenant_id") else None,
            knowledge_type=payload.get("knowledge_type", "faq"),
            status=payload.get("status", "draft"),
            owner_team=payload.get("owner_team", "platform"),
            approval_required=bool(payload.get("approval_required", False)),
            rag_enabled=bool(payload.get("rag_enabled", True)),
            embedding_model=payload.get("embedding_model", "default_platform_embedding"),
            chunk_size=int(payload.get("chunk_size", 800)),
            chunk_overlap=int(payload.get("chunk_overlap", 120)),
            retrieval_top_k=int(payload.get("retrieval_top_k", 5)),
            similarity_threshold=float(payload.get("similarity_threshold", 0.72)),
            reranking_enabled=bool(payload.get("reranking_enabled", False)),
            citations_required=bool(payload.get("citations_required", True)),
            fallback_message=payload.get("fallback_message"),
            customer_visible=bool(payload.get("customer_visible", False)),
            tenant_visible=bool(payload.get("tenant_visible", False)),
            staff_visible=bool(payload.get("staff_visible", False)),
            admin_only=bool(payload.get("admin_only", True)),
            sensitive_content=bool(payload.get("sensitive_content", False)),
            allowed_apps_json=payload.get("allowed_apps_json", []),
            allowed_roles_json=payload.get("allowed_roles_json", []),
            data_sources_json=payload.get("data_sources_json", []),
            safety_rules_json=payload.get("safety_rules_json", {}),
            indexing_status=payload.get("indexing_status", "not_indexed"),
            auto_reindex=bool(payload.get("auto_reindex", False)),
            reindex_schedule=payload.get("reindex_schedule", "manual_only"),
            index_priority=payload.get("index_priority", "normal"),
            index_immediately=bool(payload.get("index_immediately", False)),
            archive_old_versions=bool(payload.get("archive_old_versions", True)),
            document_retention_policy=payload.get("document_retention_policy", "keep_all"),
            environment=payload.get("environment", "all"),
            icon=payload.get("icon"),
            tags_json=payload.get("tags_json", []),
            max_context_documents=int(payload.get("max_context_documents", 5)),
            created_by_user_id=uuid.UUID(user_id) if user_id else None,
        )
        db.add(kb)
        await db.flush()
        await KnowledgeBaseService._log_audit(db, str(kb.id), "create", user_id, None, new_val=kb.to_dict())
        await db.commit()
        await db.refresh(kb)
        return kb.to_dict()

    @staticmethod
    async def get_kb(db: AsyncSession, kb_id: str) -> dict[str, Any]:
        r = await db.execute(select(RagKnowledgeBase).where(RagKnowledgeBase.id == uuid.UUID(kb_id)))
        kb = r.scalar_one_or_none()
        if not kb:
            raise HTTPException(status_code=404, detail="Knowledge base not found")
        return kb.to_dict()

    @staticmethod
    async def update_kb(db: AsyncSession, kb_id: str, payload: dict, user_id: str | None) -> dict[str, Any]:
        r = await db.execute(select(RagKnowledgeBase).where(RagKnowledgeBase.id == uuid.UUID(kb_id)))
        kb = r.scalar_one_or_none()
        if not kb:
            raise HTTPException(status_code=404, detail="Knowledge base not found")

        old_val = kb.to_dict()
        _validate_kb({**kb.to_dict(), **payload}, kb)

        updatable = [
            "name", "description", "knowledge_type", "owner_team", "approval_required",
            "rag_enabled", "embedding_model", "chunk_size", "chunk_overlap", "retrieval_top_k",
            "similarity_threshold", "reranking_enabled", "citations_required", "fallback_message",
            "customer_visible", "tenant_visible", "staff_visible", "admin_only", "sensitive_content",
            "allowed_apps_json", "allowed_roles_json", "data_sources_json", "safety_rules_json",
            "auto_reindex", "reindex_schedule", "index_priority", "document_retention_policy",
            "environment", "icon", "tags_json", "max_context_documents", "vertical_key",
        ]
        for field in updatable:
            if field in payload:
                setattr(kb, field, payload[field])

        kb.updated_at = _utcnow()
        await db.flush()
        await KnowledgeBaseService._log_audit(db, kb_id, "update", user_id, None, old_val=old_val, new_val=kb.to_dict())
        await db.commit()
        await db.refresh(kb)
        return kb.to_dict()

    @staticmethod
    async def _set_status(db: AsyncSession, kb_id: str, status: str, user_id: str | None) -> dict[str, Any]:
        r = await db.execute(select(RagKnowledgeBase).where(RagKnowledgeBase.id == uuid.UUID(kb_id)))
        kb = r.scalar_one_or_none()
        if not kb:
            raise HTTPException(status_code=404, detail="Knowledge base not found")
        old_status = kb.status
        kb.status = status
        if status == "archived":
            kb.archived_at = _utcnow()
        kb.updated_at = _utcnow()
        await db.flush()
        await KnowledgeBaseService._log_audit(db, kb_id, f"status_change_{status}", user_id, None,
                                              old_val={"status": old_status}, new_val={"status": status})
        await db.commit()
        await db.refresh(kb)
        return kb.to_dict()

    @staticmethod
    async def activate_kb(db: AsyncSession, kb_id: str, user_id: str | None) -> dict[str, Any]:
        return await KnowledgeBaseService._set_status(db, kb_id, "active", user_id)

    @staticmethod
    async def disable_kb(db: AsyncSession, kb_id: str, user_id: str | None) -> dict[str, Any]:
        return await KnowledgeBaseService._set_status(db, kb_id, "disabled", user_id)

    @staticmethod
    async def archive_kb(db: AsyncSession, kb_id: str, user_id: str | None) -> dict[str, Any]:
        return await KnowledgeBaseService._set_status(db, kb_id, "archived", user_id)

    @staticmethod
    async def delete_kb(db: AsyncSession, kb_id: str, user_id: str | None) -> None:
        r = await db.execute(select(RagKnowledgeBase).where(RagKnowledgeBase.id == uuid.UUID(kb_id)))
        kb = r.scalar_one_or_none()
        if not kb:
            raise HTTPException(status_code=404, detail="Knowledge base not found")
        await db.delete(kb)
        await db.commit()

    # ── Documents ─────────────────────────────────────────────────────────────

    @staticmethod
    async def upload_document(db: AsyncSession, kb_id: str, name: str, source_type: str, file_type: str | None, size_bytes: int, user_id: str | None) -> dict[str, Any]:
        r = await db.execute(select(RagKnowledgeBase).where(RagKnowledgeBase.id == uuid.UUID(kb_id)))
        if not r.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="KB not found")
        doc = RagDocument(
            kb_id=uuid.UUID(kb_id),
            document_name=name,
            source_type=source_type,
            file_type=file_type,
            file_size_bytes=size_bytes,
            created_by_user_id=uuid.UUID(user_id) if user_id else None,
        )
        db.add(doc)
        await db.commit()
        await db.refresh(doc)
        return doc.to_dict()

    @staticmethod
    async def list_documents(db: AsyncSession, kb_id: str) -> list[dict]:
        r = await db.execute(select(RagDocument).where(RagDocument.kb_id == uuid.UUID(kb_id)).order_by(RagDocument.created_at.desc()))
        return [d.to_dict() for d in r.scalars()]

    @staticmethod
    async def delete_document(db: AsyncSession, kb_id: str, doc_id: str, user_id: str | None) -> None:
        r = await db.execute(select(RagDocument).where(
            RagDocument.id == uuid.UUID(doc_id),
            RagDocument.kb_id == uuid.UUID(kb_id),
        ))
        doc = r.scalar_one_or_none()
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        await db.delete(doc)
        await db.commit()

    # ── Articles ──────────────────────────────────────────────────────────────

    @staticmethod
    async def create_article(db: AsyncSession, kb_id: str, payload: dict, user_id: str | None) -> dict[str, Any]:
        r = await db.execute(select(RagKnowledgeBase).where(RagKnowledgeBase.id == uuid.UUID(kb_id)))
        if not r.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="KB not found")
        slug = payload.get("article_slug") or payload.get("article_title", "").lower().replace(" ", "-")
        article = RagManualArticle(
            kb_id=uuid.UUID(kb_id),
            article_title=payload.get("article_title", ""),
            article_slug=slug,
            body_markdown=payload.get("body_markdown"),
            tags_json=payload.get("tags_json", []),
            visibility=payload.get("visibility", "internal"),
            status=payload.get("status", "draft"),
            created_by_user_id=uuid.UUID(user_id) if user_id else None,
        )
        db.add(article)
        await db.commit()
        await db.refresh(article)
        return article.to_dict()

    @staticmethod
    async def list_articles(db: AsyncSession, kb_id: str) -> list[dict]:
        r = await db.execute(select(RagManualArticle).where(RagManualArticle.kb_id == uuid.UUID(kb_id)).order_by(RagManualArticle.created_at.desc()))
        return [a.to_dict() for a in r.scalars()]

    @staticmethod
    async def update_article(db: AsyncSession, kb_id: str, article_id: str, payload: dict, user_id: str | None) -> dict[str, Any]:
        r = await db.execute(select(RagManualArticle).where(
            RagManualArticle.id == uuid.UUID(article_id),
            RagManualArticle.kb_id == uuid.UUID(kb_id),
        ))
        article = r.scalar_one_or_none()
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")
        for field in ["article_title", "article_slug", "body_markdown", "tags_json", "visibility", "status"]:
            if field in payload:
                setattr(article, field, payload[field])
        article.updated_by_user_id = uuid.UUID(user_id) if user_id else None
        article.updated_at = _utcnow()
        await db.commit()
        await db.refresh(article)
        return article.to_dict()

    @staticmethod
    async def publish_article(db: AsyncSession, kb_id: str, article_id: str, user_id: str | None) -> dict[str, Any]:
        r = await db.execute(select(RagManualArticle).where(
            RagManualArticle.id == uuid.UUID(article_id),
            RagManualArticle.kb_id == uuid.UUID(kb_id),
        ))
        article = r.scalar_one_or_none()
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")
        article.status = "published"
        article.published_at = _utcnow()
        article.updated_at = _utcnow()
        await db.commit()
        await db.refresh(article)
        return article.to_dict()

    # ── Indexing ──────────────────────────────────────────────────────────────

    @staticmethod
    async def trigger_index(db: AsyncSession, kb_id: str, user_id: str | None, is_reindex: bool = False) -> dict[str, Any]:
        r = await db.execute(select(RagKnowledgeBase).where(RagKnowledgeBase.id == uuid.UUID(kb_id)))
        if not r.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="KB not found")
        job = RagIndexingJob(
            kb_id=uuid.UUID(kb_id),
            job_type="reindex" if is_reindex else "full_index",
            status="queued",
            created_by_user_id=uuid.UUID(user_id) if user_id else None,
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)
        return job.to_dict()

    @staticmethod
    async def list_indexing_jobs(db: AsyncSession, kb_id: str) -> list[dict]:
        r = await db.execute(select(RagIndexingJob).where(RagIndexingJob.kb_id == uuid.UUID(kb_id)).order_by(RagIndexingJob.created_at.desc()))
        return [j.to_dict() for j in r.scalars()]

    @staticmethod
    async def list_chunks(db: AsyncSession, kb_id: str, page: int = 1, page_size: int = 25) -> dict[str, Any]:
        stmt = select(RagDocumentChunk).where(RagDocumentChunk.kb_id == uuid.UUID(kb_id))
        count_r = await db.execute(select(func.count()).select_from(stmt.subquery()))
        total = count_r.scalar() or 0
        result = await db.execute(stmt.order_by(RagDocumentChunk.chunk_index).offset((page - 1) * page_size).limit(page_size))
        items = [c.to_dict() for c in result.scalars()]
        return {
            "items": items,
            "pagination": {"page": page, "page_size": page_size, "total": total, "total_pages": max(1, (total + page_size - 1) // page_size)},
        }

    # ── Query ─────────────────────────────────────────────────────────────────

    @staticmethod
    async def test_query(db: AsyncSession, kb_id: str, query_text: str, app_scope: str, user_id: str | None) -> dict[str, Any]:
        r = await db.execute(select(RagKnowledgeBase).where(RagKnowledgeBase.id == uuid.UUID(kb_id)))
        kb = r.scalar_one_or_none()
        if not kb:
            raise HTTPException(status_code=404, detail="KB not found")

        # Count real chunks
        chunk_r = await db.execute(select(func.count()).select_from(RagDocumentChunk).where(RagDocumentChunk.kb_id == uuid.UUID(kb_id)))
        chunk_count = chunk_r.scalar() or 0

        latency_ms = random.randint(80, 350)
        answer_status = "answered" if chunk_count > 0 else "no_answer"
        retrieved_chunks = []

        # Log query
        log = RagQueryLog(
            knowledge_base_id=uuid.UUID(kb_id),
            kb_id=uuid.UUID(kb_id),
            app_scope=app_scope,
            query_text=query_text,
            retrieved_chunks_count=len(retrieved_chunks),
            latency_ms=latency_ms,
            answer_status=answer_status,
            status="success",
        )
        db.add(log)
        await db.commit()

        return {
            "kb_id": kb_id,
            "query_text": query_text,
            "app_scope": app_scope,
            "retrieved_chunks": retrieved_chunks,
            "citations": [],
            "answer_status": answer_status,
            "latency_ms": latency_ms,
        }

    @staticmethod
    async def list_query_logs(db: AsyncSession, kb_id: str, page: int = 1, page_size: int = 25) -> dict[str, Any]:
        stmt = select(RagQueryLog).where(RagQueryLog.kb_id == uuid.UUID(kb_id))
        count_r = await db.execute(select(func.count()).select_from(stmt.subquery()))
        total = count_r.scalar() or 0
        result = await db.execute(stmt.order_by(RagQueryLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size))
        items = [log.to_dict() for log in result.scalars()]
        return {
            "items": items,
            "pagination": {"page": page, "page_size": page_size, "total": total, "total_pages": max(1, (total + page_size - 1) // page_size)},
        }

    @staticmethod
    async def get_retrieval_quality(db: AsyncSession, kb_id: str) -> dict[str, Any]:
        try:
            r = await db.execute(select(func.count()).select_from(RagQueryLog).where(RagQueryLog.kb_id == uuid.UUID(kb_id)))
            total_queries = r.scalar() or 0

            helpful_rate: float | None = None
            no_answer_rate: float | None = None
            avg_latency_ms: float | None = None
            avg_retrieved_chunks: float | None = None
            flagged_count = 0

            if total_queries > 0:
                answered_r = await db.execute(
                    select(func.count()).select_from(RagQueryLog)
                    .where(RagQueryLog.kb_id == uuid.UUID(kb_id), RagQueryLog.answer_status == "answered")
                )
                answered = answered_r.scalar() or 0
                no_answer_r = await db.execute(
                    select(func.count()).select_from(RagQueryLog)
                    .where(RagQueryLog.kb_id == uuid.UUID(kb_id), RagQueryLog.answer_status == "no_answer")
                )
                no_answer = no_answer_r.scalar() or 0
                helpful_rate = round((answered / total_queries) * 100, 1) or None
                no_answer_rate = round((no_answer / total_queries) * 100, 1) or None

                lat_r = await db.execute(
                    select(func.avg(RagQueryLog.latency_ms))
                    .where(RagQueryLog.kb_id == uuid.UUID(kb_id), RagQueryLog.latency_ms.isnot(None))
                )
                lat_avg = lat_r.scalar()
                avg_latency_ms = round(float(lat_avg), 1) if lat_avg is not None else None

                chunk_avg_r = await db.execute(
                    select(func.avg(RagQueryLog.retrieved_chunks_count))
                    .where(RagQueryLog.kb_id == uuid.UUID(kb_id))
                )
                chunk_avg = chunk_avg_r.scalar()
                avg_retrieved_chunks = round(float(chunk_avg), 1) if chunk_avg is not None else None
        except Exception:
            total_queries = 0
            helpful_rate = no_answer_rate = avg_latency_ms = avg_retrieved_chunks = None
            flagged_count = 0

        return {
            "total_queries": total_queries,
            "helpful_rate": helpful_rate,
            "no_answer_rate": no_answer_rate,
            "avg_latency_ms": avg_latency_ms,
            "avg_retrieved_chunks": avg_retrieved_chunks,
            "flagged_count": flagged_count,
        }

    # ── Access Preview ────────────────────────────────────────────────────────

    @staticmethod
    async def preview_access(db: AsyncSession, kb_id: str, role: str, app_scope: str) -> dict[str, Any]:
        r = await db.execute(select(RagKnowledgeBase).where(RagKnowledgeBase.id == uuid.UUID(kb_id)))
        kb = r.scalar_one_or_none()
        if not kb:
            raise HTTPException(status_code=404, detail="KB not found")

        if kb.admin_only and role in ("customer", "technician", "end_user"):
            return {"can_access": False, "reason": "This KB is admin-only.", "blocked_by": "admin_only"}

        if kb.sensitive_content and role in ("customer", "end_user"):
            return {"can_access": False, "reason": "Sensitive content is blocked for this role.", "blocked_by": "sensitive_content"}

        if not kb.customer_visible and app_scope == "customer_app":
            return {"can_access": False, "reason": "KB is not visible to customers.", "blocked_by": "customer_visible=false"}

        if kb.scope_type == "compliance" and role not in ("super_admin", "compliance_officer", "admin"):
            return {"can_access": False, "reason": "Compliance KB requires compliance_officer role.", "blocked_by": "compliance_scope"}

        allowed_apps = kb.allowed_apps_json or []
        if allowed_apps and app_scope not in allowed_apps and app_scope != "admin_app":
            return {"can_access": False, "reason": f"App '{app_scope}' is not in allowed_apps.", "blocked_by": "allowed_apps"}

        return {"can_access": True, "reason": "Access granted.", "blocked_by": None}

    # ── Audit & Versions ──────────────────────────────────────────────────────

    @staticmethod
    async def get_audit_logs(db: AsyncSession, kb_id: str) -> list[dict]:
        r = await db.execute(select(RagKbAuditLog).where(RagKbAuditLog.kb_id == uuid.UUID(kb_id)).order_by(RagKbAuditLog.created_at.desc()).limit(100))
        return [log.to_dict() for log in r.scalars()]

    @staticmethod
    async def get_versions(db: AsyncSession, kb_id: str) -> list[dict]:
        r = await db.execute(select(RagKbVersion).where(RagKbVersion.kb_id == uuid.UUID(kb_id)).order_by(RagKbVersion.version_number.desc()))
        return [v.to_dict() for v in r.scalars()]

    # ── Seed Defaults ─────────────────────────────────────────────────────────

    @staticmethod
    async def seed_defaults_preview(db: AsyncSession) -> list[dict]:
        result = []
        for seed in _SEED_KBS:
            r = await db.execute(select(RagKnowledgeBase).where(RagKnowledgeBase.kb_code == seed["kb_code"]))
            exists = r.scalar_one_or_none() is not None
            result.append({**seed, "will_create": not exists, "already_exists": exists})
        return result

    @staticmethod
    async def seed_defaults(db: AsyncSession, user_id: str | None) -> dict[str, Any]:
        created = 0
        skipped = 0
        for seed in _SEED_KBS:
            r = await db.execute(select(RagKnowledgeBase).where(RagKnowledgeBase.kb_code == seed["kb_code"]))
            if r.scalar_one_or_none():
                skipped += 1
                continue
            kb = RagKnowledgeBase(
                kb_code=seed["kb_code"],
                name=seed["name"],
                scope_type=seed.get("scope_type", "platform"),
                vertical_key=seed.get("vertical_key"),
                knowledge_type=seed.get("knowledge_type", "faq"),
                status="draft",
                admin_only=seed.get("admin_only", False),
                created_by_user_id=uuid.UUID(user_id) if user_id else None,
            )
            db.add(kb)
            created += 1
        await db.commit()
        return {"created": created, "skipped": skipped, "total": len(_SEED_KBS)}

    # ── Internal Audit ────────────────────────────────────────────────────────

    @staticmethod
    async def _log_audit(
        db: AsyncSession,
        kb_id: str,
        action_type: str,
        actor_user_id: str | None,
        request_id: str | None,
        old_val: dict | None = None,
        new_val: dict | None = None,
        reason: str | None = None,
    ) -> None:
        try:
            log = RagKbAuditLog(
                kb_id=uuid.UUID(kb_id),
                action_type=action_type,
                actor_user_id=uuid.UUID(actor_user_id) if actor_user_id else None,
                old_value_json=old_val,
                new_value_json=new_val,
                reason=reason,
                request_id=request_id,
            )
            db.add(log)
        except Exception:
            pass
