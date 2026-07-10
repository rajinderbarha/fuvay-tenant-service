"""Intelligence Command Center — ORM Models (8 tables, migration 103)."""
from __future__ import annotations
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any
from sqlalchemy import Boolean, DateTime, Float, Integer, Numeric, String, Text, Index, UniqueConstraint, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import ServiceOSBase, utcnow


class RagKnowledgeBase(ServiceOSBase):
    __tablename__ = "rag_knowledge_bases"

    name: Mapped[str] = mapped_column(Text, nullable=False)
    kb_code: Mapped[str | None] = mapped_column(Text, nullable=True, unique=True)
    scope_type: Mapped[str] = mapped_column(Text, default="platform")
    scope_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    vertical_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    category_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    knowledge_type: Mapped[str] = mapped_column(Text, default="faq")
    status: Mapped[str] = mapped_column(Text, default="draft")
    owner_team: Mapped[str] = mapped_column(Text, default="platform")
    approval_required: Mapped[bool] = mapped_column(Boolean, default=False)
    reviewer_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    rag_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    embedding_model: Mapped[str] = mapped_column(Text, default="default_platform_embedding")
    chunk_size: Mapped[int] = mapped_column(Integer, default=800)
    chunk_overlap: Mapped[int] = mapped_column(Integer, default=120)
    retrieval_top_k: Mapped[int] = mapped_column(Integer, default=5)
    similarity_threshold: Mapped[float] = mapped_column(Float, default=0.72)
    reranking_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    citations_required: Mapped[bool] = mapped_column(Boolean, default=True)
    fallback_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    customer_visible: Mapped[bool] = mapped_column(Boolean, default=False)
    tenant_visible: Mapped[bool] = mapped_column(Boolean, default=False)
    staff_visible: Mapped[bool] = mapped_column(Boolean, default=False)
    admin_only: Mapped[bool] = mapped_column(Boolean, default=True)
    sensitive_content: Mapped[bool] = mapped_column(Boolean, default=False)
    allowed_apps_json: Mapped[list] = mapped_column(JSONB, default=list)
    allowed_roles_json: Mapped[list] = mapped_column(JSONB, default=list)
    data_sources_json: Mapped[list] = mapped_column(JSONB, default=list)
    safety_rules_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    indexing_status: Mapped[str] = mapped_column(Text, default="not_indexed")
    auto_reindex: Mapped[bool] = mapped_column(Boolean, default=False)
    reindex_schedule: Mapped[str] = mapped_column(Text, default="manual_only")
    index_priority: Mapped[str] = mapped_column(Text, default="normal")
    index_immediately: Mapped[bool] = mapped_column(Boolean, default=False)
    archive_old_versions: Mapped[bool] = mapped_column(Boolean, default=True)
    document_retention_policy: Mapped[str] = mapped_column(Text, default="keep_all")
    environment: Mapped[str] = mapped_column(Text, default="all")
    icon: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags_json: Mapped[list] = mapped_column(JSONB, default=list)
    max_context_documents: Mapped[int] = mapped_column(Integer, default=5)
    document_count: Mapped[int] = mapped_column(Integer, default=0)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    last_indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "kb_code": self.kb_code,
            "name": self.name,
            "description": self.description,
            "scope_type": self.scope_type,
            "scope_id": str(self.scope_id) if self.scope_id else None,
            "vertical_key": self.vertical_key,
            "category_id": str(self.category_id) if self.category_id else None,
            "tenant_id": str(self.tenant_id) if self.tenant_id else None,
            "knowledge_type": self.knowledge_type,
            "status": self.status,
            "owner_team": self.owner_team,
            "approval_required": self.approval_required,
            "rag_enabled": self.rag_enabled,
            "embedding_model": self.embedding_model,
            "chunk_size": self.chunk_size or 800,
            "chunk_overlap": self.chunk_overlap or 120,
            "retrieval_top_k": self.retrieval_top_k or 5,
            "similarity_threshold": float(self.similarity_threshold) if self.similarity_threshold is not None else 0.72,
            "reranking_enabled": self.reranking_enabled,
            "citations_required": self.citations_required,
            "fallback_message": self.fallback_message,
            "customer_visible": self.customer_visible,
            "tenant_visible": self.tenant_visible,
            "staff_visible": self.staff_visible,
            "admin_only": self.admin_only,
            "sensitive_content": self.sensitive_content,
            "allowed_apps_json": self.allowed_apps_json or [],
            "allowed_roles_json": self.allowed_roles_json or [],
            "data_sources_json": self.data_sources_json or [],
            "safety_rules_json": self.safety_rules_json or {},
            "indexing_status": self.indexing_status,
            "auto_reindex": self.auto_reindex,
            "reindex_schedule": self.reindex_schedule,
            "index_priority": self.index_priority,
            "max_context_documents": self.max_context_documents or 5,
            "document_count": self.document_count or 0,
            "chunk_count": self.chunk_count or 0,
            "last_indexed_at": self.last_indexed_at.isoformat() if self.last_indexed_at else None,
            "archived_at": self.archived_at.isoformat() if self.archived_at else None,
            "tags_json": self.tags_json or [],
            "icon": self.icon,
            "environment": self.environment,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class RagQueryLog(ServiceOSBase):
    __tablename__ = "rag_query_logs"

    knowledge_base_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("rag_knowledge_bases.id", ondelete="SET NULL"), nullable=True)
    app_scope: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    query_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    retrieved_chunks_count: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0)
    cost_amount: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=Decimal("0"))
    status: Mapped[str] = mapped_column(Text, default="success")
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    answer_status: Mapped[str] = mapped_column(Text, default="answered")
    kb_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "knowledge_base_id": str(self.knowledge_base_id) if self.knowledge_base_id else None,
            "kb_id": str(self.kb_id) if self.kb_id else None,
            "app_scope": self.app_scope,
            "query_text": self.query_text,
            "retrieved_chunks_count": self.retrieved_chunks_count or 0,
            "latency_ms": self.latency_ms,
            "tokens_in": self.tokens_in or 0,
            "tokens_out": self.tokens_out or 0,
            "cost_amount": float(self.cost_amount) if self.cost_amount else 0.0,
            "status": self.status,
            "feedback": self.feedback,
            "answer_status": self.answer_status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class IntelRiskScore(ServiceOSBase):
    __tablename__ = "intel_risk_scores"
    __table_args__ = (Index("ix_intel_risk_entity", "entity_type", "entity_id"),)

    entity_type: Mapped[str] = mapped_column(Text, nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    risk_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0"))
    risk_level: Mapped[str] = mapped_column(Text, default="low")
    top_reasons_json: Mapped[list] = mapped_column(JSONB, default=list)
    feature_contributions_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    confidence_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0"))
    model_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "entity_type": self.entity_type,
            "entity_id": str(self.entity_id),
            "risk_score": float(self.risk_score) if self.risk_score is not None else 0.0,
            "risk_level": self.risk_level,
            "top_reasons_json": self.top_reasons_json or [],
            "confidence_score": float(self.confidence_score) if self.confidence_score is not None else 0.0,
            "model_version": self.model_version,
            "computed_at": self.computed_at.isoformat() if self.computed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class IntelAnomaly(ServiceOSBase):
    __tablename__ = "intel_anomalies"

    anomaly_type: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(Text, default="medium")
    entity_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    vertical_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0"))
    status: Mapped[str] = mapped_column(Text, default="open")
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "anomaly_type": self.anomaly_type,
            "severity": self.severity,
            "entity_type": self.entity_type,
            "entity_id": str(self.entity_id) if self.entity_id else None,
            "vertical_key": self.vertical_key,
            "summary": self.summary,
            "confidence_score": float(self.confidence_score) if self.confidence_score is not None else 0.0,
            "status": self.status,
            "detected_at": self.detected_at.isoformat() if self.detected_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class IntelModelRegistry(ServiceOSBase):
    __tablename__ = "intel_model_registry"

    name: Mapped[str] = mapped_column(Text, nullable=False)
    model_type: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[str] = mapped_column(Text, default="1.0.0")
    status: Mapped[str] = mapped_column(Text, default="draft")
    environment: Mapped[str] = mapped_column(Text, default="production")
    accuracy_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    avg_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_trained_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    config_json: Mapped[dict] = mapped_column(JSONB, default=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "name": self.name,
            "model_type": self.model_type,
            "version": self.version,
            "status": self.status,
            "environment": self.environment,
            "accuracy_score": float(self.accuracy_score) if self.accuracy_score is not None else None,
            "avg_latency_ms": self.avg_latency_ms,
            "last_trained_at": self.last_trained_at.isoformat() if self.last_trained_at else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class IntelPredictionJob(ServiceOSBase):
    __tablename__ = "intel_prediction_jobs"

    job_type: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, default="queued")
    scope_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    total_processed: Mapped[int] = mapped_column(Integer, default=0)
    total_failed: Mapped[int] = mapped_column(Integer, default=0)
    triggered_by: Mapped[str] = mapped_column(Text, default="manual")
    started_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    result_summary_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "job_type": self.job_type,
            "status": self.status,
            "total_processed": self.total_processed or 0,
            "total_failed": self.total_failed or 0,
            "triggered_by": self.triggered_by,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result_summary_json": self.result_summary_json or {},
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class IntelDataQualityCheck(ServiceOSBase):
    __tablename__ = "intel_data_quality_checks"
    __table_args__ = (UniqueConstraint("check_key", name="uq_intel_dqc_key"),)

    check_key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    check_name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str] = mapped_column(Text, default="medium")
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_status: Mapped[str] = mapped_column(Text, default="not_run")
    failure_count: Mapped[int] = mapped_column(Integer, default=0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "check_key": self.check_key,
            "check_name": self.check_name,
            "description": self.description,
            "severity": self.severity,
            "is_enabled": self.is_enabled,
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "last_status": self.last_status,
            "failure_count": self.failure_count or 0,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class AiUsageLog(ServiceOSBase):
    __tablename__ = "ai_usage_logs"

    feature_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    app_scope: Mapped[str | None] = mapped_column(Text, nullable=True)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    model_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0)
    cost_amount: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=Decimal("0"))
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(Text, default="success")
    error_code: Mapped[str | None] = mapped_column(Text, nullable=True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "feature_key": self.feature_key,
            "app_scope": self.app_scope,
            "tenant_id": str(self.tenant_id) if self.tenant_id else None,
            "model_name": self.model_name,
            "tokens_in": self.tokens_in or 0,
            "tokens_out": self.tokens_out or 0,
            "cost_amount": float(self.cost_amount) if self.cost_amount else 0.0,
            "latency_ms": self.latency_ms,
            "status": self.status,
            "error_code": self.error_code,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
