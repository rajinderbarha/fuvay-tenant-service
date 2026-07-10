"""Knowledge Base Enterprise — ORM Models (migration 104)."""
from __future__ import annotations
import uuid
from datetime import datetime
from typing import Any
from sqlalchemy import Boolean, BigInteger, DateTime, Float, Integer, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import ServiceOSBase


class RagDocument(ServiceOSBase):
    __tablename__ = "rag_documents"

    kb_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("rag_knowledge_bases.id", ondelete="CASCADE"), nullable=False)
    document_name: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(Text, default="uploaded")
    source_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    file_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    media_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    visibility: Mapped[str] = mapped_column(Text, default="internal")
    indexing_status: Mapped[str] = mapped_column(Text, default="not_indexed")
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    last_indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "kb_id": str(self.kb_id),
            "document_name": self.document_name,
            "source_type": self.source_type,
            "file_type": self.file_type,
            "file_size_bytes": self.file_size_bytes or 0,
            "visibility": self.visibility,
            "indexing_status": self.indexing_status,
            "chunk_count": self.chunk_count or 0,
            "last_indexed_at": self.last_indexed_at.isoformat() if self.last_indexed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class RagManualArticle(ServiceOSBase):
    __tablename__ = "rag_manual_articles"

    kb_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("rag_knowledge_bases.id", ondelete="CASCADE"), nullable=False)
    article_title: Mapped[str] = mapped_column(Text, nullable=False)
    article_slug: Mapped[str] = mapped_column(Text, nullable=False)
    body_markdown: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags_json: Mapped[list] = mapped_column(JSONB, default=list)
    visibility: Mapped[str] = mapped_column(Text, default="internal")
    status: Mapped[str] = mapped_column(Text, default="draft")
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "kb_id": str(self.kb_id),
            "article_title": self.article_title,
            "article_slug": self.article_slug,
            "body_markdown": self.body_markdown,
            "tags_json": self.tags_json or [],
            "visibility": self.visibility,
            "status": self.status,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class RagDocumentChunk(ServiceOSBase):
    __tablename__ = "rag_document_chunks"

    kb_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("rag_knowledge_bases.id", ondelete="CASCADE"), nullable=False)
    document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    article_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, default=0)
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    embedding_status: Mapped[str] = mapped_column(Text, default="pending")
    embedding_model: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "kb_id": str(self.kb_id),
            "document_id": str(self.document_id) if self.document_id else None,
            "article_id": str(self.article_id) if self.article_id else None,
            "chunk_text": self.chunk_text,
            "chunk_index": self.chunk_index or 0,
            "token_count": self.token_count or 0,
            "embedding_status": self.embedding_status,
            "embedding_model": self.embedding_model,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class RagIndexingJob(ServiceOSBase):
    __tablename__ = "rag_indexing_jobs"

    kb_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("rag_knowledge_bases.id", ondelete="CASCADE"), nullable=False)
    job_type: Mapped[str] = mapped_column(Text, default="full_index")
    status: Mapped[str] = mapped_column(Text, default="queued")
    documents_processed: Mapped[int] = mapped_column(Integer, default=0)
    chunks_created: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    is_dry_run: Mapped[bool] = mapped_column(Boolean, default=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "kb_id": str(self.kb_id),
            "job_type": self.job_type,
            "status": self.status,
            "documents_processed": self.documents_processed or 0,
            "chunks_created": self.chunks_created or 0,
            "failed_count": self.failed_count or 0,
            "is_dry_run": self.is_dry_run,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class RagRetrievalFeedback(ServiceOSBase):
    __tablename__ = "rag_retrieval_feedback"

    kb_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("rag_knowledge_bases.id", ondelete="CASCADE"), nullable=False)
    query_log_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    feedback_type: Mapped[str] = mapped_column(Text, default="helpful")
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    flagged_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "kb_id": str(self.kb_id),
            "query_log_id": str(self.query_log_id) if self.query_log_id else None,
            "feedback_type": self.feedback_type,
            "comment": self.comment,
            "flagged_reason": self.flagged_reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class RagKbVersion(ServiceOSBase):
    __tablename__ = "rag_kb_versions"

    kb_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("rag_knowledge_bases.id", ondelete="CASCADE"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    changed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    change_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "kb_id": str(self.kb_id),
            "version_number": self.version_number,
            "snapshot_json": self.snapshot_json or {},
            "change_reason": self.change_reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class RagKbAuditLog(ServiceOSBase):
    __tablename__ = "rag_kb_audit_logs"

    kb_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("rag_knowledge_bases.id", ondelete="CASCADE"), nullable=False)
    action_type: Mapped[str] = mapped_column(Text, nullable=False)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    old_value_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    new_value_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    request_id: Mapped[str | None] = mapped_column(Text, nullable=True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "kb_id": str(self.kb_id),
            "action_type": self.action_type,
            "actor_user_id": str(self.actor_user_id) if self.actor_user_id else None,
            "old_value_json": self.old_value_json,
            "new_value_json": self.new_value_json,
            "reason": self.reason,
            "request_id": self.request_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
