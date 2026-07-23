"""MODULE-L5-51 — RAG hybrid search + GraphRAG

Real embeddings (sentence-transformers all-MiniLM-L6-v2, 384-dim) replace the
never-configured 1536-dim OpenAI placeholder, so the pgvector column and its
ivfflat index (created for real back in migration 006, but never actually
populated with real vectors) must be rebuilt at the new dimension.

Also adds:
  - content_tsv (tsvector) + GIN index + trigger on document_chunks, for the
    real keyword-search leg of hybrid retrieval.
  - kb_entities / kb_entity_relationships / kb_chunk_entities — the GraphRAG
    entity-graph tables (single-hop entity co-occurrence expansion).

Revision ID: 147
Revises: 146
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID

revision = "147"
down_revision = "146"
branch_labels = None
depends_on = None

NEW_DIM = 384


def upgrade() -> None:
    # ── 1. Rebuild embedding column at the new dimension ───────────────────
    # Existing embeddings were produced by _mock_embed() (a deterministic
    # hash, not a real model) — they carry zero real semantic value, so they
    # are dropped rather than "migrated". Documents must be reindexed after
    # this migration to get real vectors (this is expected and communicated
    # in the final report, not silently swept under the rug).
    op.execute("DROP INDEX IF EXISTS ix_chunk_embedding_ivfflat")
    op.execute("ALTER TABLE document_chunks DROP COLUMN IF EXISTS embedding")
    op.execute(f"ALTER TABLE document_chunks ADD COLUMN embedding vector({NEW_DIM})")
    # ivfflat requires at least some rows to pick sane `lists`; with an
    # empty/small table this still builds fine (falls back gracefully) and
    # will be genuinely useful once documents are reindexed.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_chunk_embedding_ivfflat "
        "ON document_chunks USING ivfflat (embedding vector_cosine_ops) "
        "WITH (lists = 100)"
    )

    # ── 2. Full-text search column (real keyword-search leg of hybrid) ─────
    op.add_column("document_chunks", sa.Column("content_tsv", TSVECTOR, nullable=True))
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_chunk_content_tsv "
        "ON document_chunks USING GIN (content_tsv)"
    )
    op.execute("""
        CREATE OR REPLACE FUNCTION rag_chunk_tsv_trigger() RETURNS trigger AS $$
        BEGIN
            NEW.content_tsv := to_tsvector('english', coalesce(NEW.content, ''));
            RETURN NEW;
        END
        $$ LANGUAGE plpgsql;
    """)
    op.execute("DROP TRIGGER IF EXISTS trg_rag_chunk_tsv ON document_chunks")
    op.execute("""
        CREATE TRIGGER trg_rag_chunk_tsv
        BEFORE INSERT OR UPDATE OF content ON document_chunks
        FOR EACH ROW EXECUTE FUNCTION rag_chunk_tsv_trigger();
    """)
    # Backfill any existing rows (none expected post-embedding-reset, but
    # defensive in case content-only rows survived).
    op.execute("UPDATE document_chunks SET content_tsv = to_tsvector('english', coalesce(content, ''))")

    # ── 3. GraphRAG entity tables ───────────────────────────────────────────
    op.create_table("kb_entities",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("kb_id", UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False, server_default="other"),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("mention_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("kb_id", "name", "entity_type", name="uq_kbentity_kb_name_type"),
    )
    op.create_index("ix_kbentity_kb", "kb_entities", ["kb_id"])

    op.create_table("kb_entity_relationships",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("kb_id", UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("source_entity_id", UUID(as_uuid=True), nullable=False),
        sa.Column("target_entity_id", UUID(as_uuid=True), nullable=False),
        sa.Column("relationship", sa.String(200), nullable=False),
        sa.Column("source_chunk_id", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_kbrel_kb", "kb_entity_relationships", ["kb_id"])
    op.create_index("ix_kbrel_source", "kb_entity_relationships", ["source_entity_id"])
    op.create_index("ix_kbrel_target", "kb_entity_relationships", ["target_entity_id"])

    op.create_table("kb_chunk_entities",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("chunk_id", UUID(as_uuid=True), nullable=False),
        sa.Column("entity_id", UUID(as_uuid=True), nullable=False),
        sa.Column("kb_id", UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("chunk_id", "entity_id", name="uq_kbchunkentity_chunk_entity"),
    )
    op.create_index("ix_kbchunkentity_chunk", "kb_chunk_entities", ["chunk_id"])
    op.create_index("ix_kbchunkentity_entity", "kb_chunk_entities", ["entity_id"])


def downgrade() -> None:
    op.drop_table("kb_chunk_entities")
    op.drop_table("kb_entity_relationships")
    op.drop_table("kb_entities")

    op.execute("DROP TRIGGER IF EXISTS trg_rag_chunk_tsv ON document_chunks")
    op.execute("DROP FUNCTION IF EXISTS rag_chunk_tsv_trigger()")
    op.execute("DROP INDEX IF EXISTS ix_chunk_content_tsv")
    op.drop_column("document_chunks", "content_tsv")

    op.execute("DROP INDEX IF EXISTS ix_chunk_embedding_ivfflat")
    op.execute("ALTER TABLE document_chunks DROP COLUMN IF EXISTS embedding")
    op.execute("ALTER TABLE document_chunks ADD COLUMN embedding vector(1536)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_chunk_embedding_ivfflat "
        "ON document_chunks USING ivfflat (embedding vector_cosine_ops) "
        "WITH (lists = 100)"
    )
