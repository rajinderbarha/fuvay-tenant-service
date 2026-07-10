"""Phase 6 — RAG Engine (4 tables + pgvector extension)

Revision ID: 006
Revises: 005
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable pgvector extension (idempotent)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table("knowledge_bases",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("vertical", sa.String(50), nullable=True),
        sa.Column("embedding_model", sa.String(80), nullable=False, server_default="text-embedding-3-small"),
        sa.Column("chunk_size", sa.Integer, nullable=False, server_default="512"),
        sa.Column("chunk_overlap", sa.Integer, nullable=False, server_default="64"),
        sa.Column("top_k", sa.Integer, nullable=False, server_default="5"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("document_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("indexed_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_chunks", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_tokens_used", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_by", UUID(as_uuid=True), nullable=True),
        sa.Column("meta", JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_kb_tenant", "knowledge_bases", ["tenant_id"])

    op.create_table("kb_documents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("kb_id", UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("raw_text", sa.Text, nullable=True),
        sa.Column("char_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("chunk_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("token_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("status_message", sa.String(500), nullable=True),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("uploaded_by", UUID(as_uuid=True), nullable=True),
        sa.Column("source_url", sa.String(2000), nullable=True),
        sa.Column("tags", JSONB, nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("kb_id", "content_hash", name="uq_kbdoc_kb_hash"),
    )
    op.create_index("ix_kbdoc_kb_id", "kb_documents", ["kb_id"])
    op.create_index("ix_kbdoc_status", "kb_documents", ["status"])

    op.create_table("document_chunks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("kb_id", UUID(as_uuid=True), nullable=False),
        sa.Column("doc_id", UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("token_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("char_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("embedding_placeholder", sa.Text, nullable=True),  # replaced below
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("meta", JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    # Replace placeholder text column with proper vector type
    op.execute("ALTER TABLE document_chunks DROP COLUMN embedding_placeholder")
    op.execute("ALTER TABLE document_chunks ADD COLUMN embedding vector(1536)")
    op.create_index("ix_chunk_doc_id", "document_chunks", ["doc_id"])
    op.create_index("ix_chunk_kb_active", "document_chunks", ["kb_id", "is_active"])
    op.create_index("ix_chunk_version", "document_chunks", ["doc_id", "version", "is_active"])
    # pgvector IVFFlat index for approximate nearest-neighbour search
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_chunk_embedding_ivfflat "
        "ON document_chunks USING ivfflat (embedding vector_cosine_ops) "
        "WITH (lists = 100)"
    )

    op.create_table("rag_queries",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("kb_id", UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("asked_by", UUID(as_uuid=True), nullable=True),
        sa.Column("asked_by_role", sa.String(30), nullable=True),
        sa.Column("question", sa.Text, nullable=False),
        sa.Column("answer", sa.Text, nullable=True),
        sa.Column("retrieved_chunks", JSONB, nullable=False, server_default="[]"),
        sa.Column("citations", JSONB, nullable=False, server_default="[]"),
        sa.Column("top_similarity", sa.Float, nullable=True),
        sa.Column("low_confidence", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("embedding_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("completion_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("latency_ms", sa.Integer, nullable=False, server_default="0"),
        sa.Column("model_used", sa.String(80), nullable=True),
        sa.Column("error_message", sa.String(500), nullable=True),
        sa.Column("idempotency_key", sa.String(255), nullable=True, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_rq_tenant", "rag_queries", ["tenant_id"])
    op.create_index("ix_rq_kb", "rag_queries", ["kb_id"])
    op.create_index("ix_rq_created", "rag_queries", ["created_at"])


def downgrade() -> None:
    for t in ["rag_queries", "document_chunks", "kb_documents", "knowledge_bases"]:
        op.drop_table(t)
