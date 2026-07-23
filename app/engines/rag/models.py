"""RAG Engine — Models (4 tables). pgvector for embeddings."""
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean, DateTime, Float, Index, Integer,
    Numeric, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector

from app.engines.rag.constants import EMBEDDING_DIMENSIONS
from app.models.base import ServiceOSBase, utcnow


class KnowledgeBase(ServiceOSBase):
    """One KB per logical domain per tenant. Tenants can have multiple KBs."""
    __tablename__ = "knowledge_bases"
    __table_args__ = (Index("ix_kb_tenant", "tenant_id"),)

    tenant_id:        Mapped[uuid.UUID]   = mapped_column(UUID(as_uuid=True), nullable=False)
    name:             Mapped[str]         = mapped_column(String(200), nullable=False)
    description:      Mapped[str | None]  = mapped_column(Text, nullable=True)
    vertical:         Mapped[str | None]  = mapped_column(String(50), nullable=True)
    embedding_model:  Mapped[str]         = mapped_column(String(80), default="text-embedding-3-small", nullable=False)
    chunk_size:       Mapped[int]         = mapped_column(Integer, default=512, nullable=False)
    chunk_overlap:    Mapped[int]         = mapped_column(Integer, default=64, nullable=False)
    top_k:            Mapped[int]         = mapped_column(Integer, default=5, nullable=False)
    is_active:        Mapped[bool]        = mapped_column(Boolean, default=True, nullable=False)
    document_count:   Mapped[int]         = mapped_column(Integer, default=0, nullable=False)
    indexed_count:    Mapped[int]         = mapped_column(Integer, default=0, nullable=False)
    total_chunks:     Mapped[int]         = mapped_column(Integer, default=0, nullable=False)
    total_tokens_used:Mapped[int]         = mapped_column(Integer, default=0, nullable=False)
    created_by:       Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    meta:             Mapped[dict]        = mapped_column(JSONB, default=dict, nullable=False)


class KBDocument(ServiceOSBase):
    """A document ingested into a knowledge base. Idempotent on content_hash."""
    __tablename__ = "kb_documents"
    __table_args__ = (
        UniqueConstraint("kb_id", "content_hash", name="uq_kbdoc_kb_hash"),
        Index("ix_kbdoc_kb_id", "kb_id"),
        Index("ix_kbdoc_status", "status"),
    )

    kb_id:          Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id:      Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), nullable=False)
    file_name:      Mapped[str]          = mapped_column(String(255), nullable=False)
    mime_type:      Mapped[str]          = mapped_column(String(100), nullable=False)
    content_hash:   Mapped[str]          = mapped_column(String(64), nullable=False)
    raw_text:       Mapped[str | None]   = mapped_column(Text, nullable=True)
    char_count:     Mapped[int]          = mapped_column(Integer, default=0, nullable=False)
    chunk_count:    Mapped[int]          = mapped_column(Integer, default=0, nullable=False)
    token_count:    Mapped[int]          = mapped_column(Integer, default=0, nullable=False)
    status:         Mapped[str]          = mapped_column(String(20), default="pending", nullable=False)
    status_message: Mapped[str | None]   = mapped_column(String(500), nullable=True)
    version:        Mapped[int]          = mapped_column(Integer, default=1, nullable=False)
    indexed_at:     Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    uploaded_by:    Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    source_url:     Mapped[str | None]   = mapped_column(String(2000), nullable=True)
    tags:           Mapped[list]         = mapped_column(JSONB, default=list, nullable=False)


class DocumentChunk(ServiceOSBase):
    """Individual text chunk with embedding vector. Immutable after insertion.
    Re-indexing soft-deletes old chunks and inserts new version."""
    __tablename__ = "document_chunks"
    __table_args__ = (
        Index("ix_chunk_doc_id", "doc_id"),
        Index("ix_chunk_kb_active", "kb_id", "is_active"),
        Index("ix_chunk_version", "doc_id", "version", "is_active"),
    )

    kb_id:        Mapped[uuid.UUID]  = mapped_column(UUID(as_uuid=True), nullable=False)
    doc_id:       Mapped[uuid.UUID]  = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id:    Mapped[uuid.UUID]  = mapped_column(UUID(as_uuid=True), nullable=False)
    chunk_index:  Mapped[int]        = mapped_column(Integer, nullable=False)
    content:      Mapped[str]        = mapped_column(Text, nullable=False)
    token_count:  Mapped[int]        = mapped_column(Integer, default=0, nullable=False)
    char_count:   Mapped[int]        = mapped_column(Integer, default=0, nullable=False)
    # MODULE-L5-51: real pgvector column (was ARRAY(Float) in the ORM despite
    # the live column already being `vector(1536)` at the DB level since
    # migration 006 -- a real type mismatch, now corrected). Dimension is
    # 384 (all-MiniLM-L6-v2, sentence-transformers) — migration 147 alters
    # the column from vector(1536) to vector(384) and rebuilds the index.
    embedding:    Mapped[list | None]= mapped_column(Vector(EMBEDDING_DIMENSIONS), nullable=True)
    # Full-text search column (real keyword-search leg of hybrid retrieval).
    # Populated via a DB trigger (see migration 147) so it's always in sync
    # with `content`, including on raw SQL updates.
    content_tsv:  Mapped[str | None] = mapped_column(TSVECTOR, nullable=True)
    is_active:    Mapped[bool]       = mapped_column(Boolean, default=True, nullable=False)
    version:      Mapped[int]        = mapped_column(Integer, default=1, nullable=False)
    meta:         Mapped[dict]       = mapped_column(JSONB, default=dict, nullable=False)


class RAGQuery(ServiceOSBase):
    """Every query stored with full pipeline trace. Never ephemeral."""
    __tablename__ = "rag_queries"
    __table_args__ = (
        Index("ix_rq_tenant", "tenant_id"),
        Index("ix_rq_kb", "kb_id"),
        Index("ix_rq_created", "created_at"),
    )

    kb_id:              Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id:          Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), nullable=False)
    asked_by:           Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    asked_by_role:      Mapped[str | None]   = mapped_column(String(30), nullable=True)
    question:           Mapped[str]          = mapped_column(Text, nullable=False)
    answer:             Mapped[str | None]   = mapped_column(Text, nullable=True)
    retrieved_chunks:   Mapped[list]         = mapped_column(JSONB, default=list, nullable=False)
    citations:          Mapped[list]         = mapped_column(JSONB, default=list, nullable=False)
    top_similarity:     Mapped[float | None] = mapped_column(Float, nullable=True)
    low_confidence:     Mapped[bool]         = mapped_column(Boolean, default=False, nullable=False)
    status:             Mapped[str]          = mapped_column(String(20), default="pending", nullable=False)
    embedding_tokens:   Mapped[int]          = mapped_column(Integer, default=0, nullable=False)
    completion_tokens:  Mapped[int]          = mapped_column(Integer, default=0, nullable=False)
    total_tokens:       Mapped[int]          = mapped_column(Integer, default=0, nullable=False)
    latency_ms:         Mapped[int]          = mapped_column(Integer, default=0, nullable=False)
    model_used:         Mapped[str | None]   = mapped_column(String(80), nullable=True)
    error_message:      Mapped[str | None]   = mapped_column(String(500), nullable=True)
    idempotency_key:    Mapped[str | None]   = mapped_column(String(255), nullable=True, unique=True)


# ── GraphRAG (single-hop entity co-occurrence expansion) ──────────────────
# MODULE-L5-51: a real, bounded graph layer. Entities + relationships are
# extracted per-chunk by an LLM call (DeepSeekClientService, structured JSON
# extraction — same "LLM call -> parse JSON -> store rows" pattern as
# app/engines/inventory/extraction_service.py). At query time, entities
# mentioned in the top hybrid-ranked chunks are used to pull in OTHER chunks
# that mention a related/connected entity, widening context beyond pure
# lexical/semantic similarity. This is single-hop entity co-occurrence
# expansion, NOT full community detection/summarization as in the original
# Microsoft GraphRAG paper — documented honestly, not oversold.
class KBEntity(ServiceOSBase):
    """A named entity extracted from KB documents (per-tenant, per-KB)."""
    __tablename__ = "kb_entities"
    __table_args__ = (
        UniqueConstraint("kb_id", "name", "entity_type", name="uq_kbentity_kb_name_type"),
        Index("ix_kbentity_kb", "kb_id"),
    )

    kb_id:        Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id:    Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    name:         Mapped[str]       = mapped_column(String(200), nullable=False)
    entity_type:  Mapped[str]       = mapped_column(String(50), nullable=False, default="other")
    description:  Mapped[str | None] = mapped_column(Text, nullable=True)
    mention_count: Mapped[int]      = mapped_column(Integer, default=0, nullable=False)


class KBEntityRelationship(ServiceOSBase):
    """A directed relationship between two entities, as asserted by the LLM
    extraction for a specific source chunk (kept for provenance)."""
    __tablename__ = "kb_entity_relationships"
    __table_args__ = (
        Index("ix_kbrel_kb", "kb_id"),
        Index("ix_kbrel_source", "source_entity_id"),
        Index("ix_kbrel_target", "target_entity_id"),
    )

    kb_id:             Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id:         Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    source_entity_id:  Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    target_entity_id:  Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    relationship:      Mapped[str]       = mapped_column(String(200), nullable=False)
    source_chunk_id:   Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)


class KBChunkEntity(ServiceOSBase):
    """Links a chunk to the entities it mentions (many-to-many)."""
    __tablename__ = "kb_chunk_entities"
    __table_args__ = (
        UniqueConstraint("chunk_id", "entity_id", name="uq_kbchunkentity_chunk_entity"),
        Index("ix_kbchunkentity_chunk", "chunk_id"),
        Index("ix_kbchunkentity_entity", "entity_id"),
    )

    chunk_id:  Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    kb_id:     Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
