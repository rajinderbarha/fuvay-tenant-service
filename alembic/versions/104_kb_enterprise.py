"""Knowledge Base Enterprise — 8 tables + alter rag_knowledge_bases.

Revision ID: 104
Revises: 103
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "104"
down_revision = "103"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── ALTER rag_knowledge_bases (already exists from migration 103) ──────────
    cols_to_add = [
        sa.Column("kb_code", sa.Text(), nullable=True),
        sa.Column("knowledge_type", sa.Text(), server_default="faq"),
        sa.Column("owner_team", sa.Text(), server_default="platform"),
        sa.Column("approval_required", sa.Boolean(), server_default="false"),
        sa.Column("reviewer_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("rag_enabled", sa.Boolean(), server_default="true"),
        sa.Column("embedding_model", sa.Text(), server_default="default_platform_embedding"),
        sa.Column("chunk_size", sa.Integer(), server_default="800"),
        sa.Column("chunk_overlap", sa.Integer(), server_default="120"),
        sa.Column("retrieval_top_k", sa.Integer(), server_default="5"),
        sa.Column("similarity_threshold", sa.Float(), server_default="0.72"),
        sa.Column("reranking_enabled", sa.Boolean(), server_default="false"),
        sa.Column("citations_required", sa.Boolean(), server_default="true"),
        sa.Column("fallback_message", sa.Text(), nullable=True),
        sa.Column("customer_visible", sa.Boolean(), server_default="false"),
        sa.Column("tenant_visible", sa.Boolean(), server_default="false"),
        sa.Column("staff_visible", sa.Boolean(), server_default="false"),
        sa.Column("admin_only", sa.Boolean(), server_default="true"),
        sa.Column("sensitive_content", sa.Boolean(), server_default="false"),
        sa.Column("allowed_apps_json", JSONB, server_default="[]"),
        sa.Column("allowed_roles_json", JSONB, server_default="[]"),
        sa.Column("data_sources_json", JSONB, server_default="[]"),
        sa.Column("safety_rules_json", JSONB, server_default="{}"),
        sa.Column("indexing_status", sa.Text(), server_default="not_indexed"),
        sa.Column("last_indexed_at_kb", sa.DateTime(timezone=True), nullable=True),
        sa.Column("auto_reindex", sa.Boolean(), server_default="false"),
        sa.Column("reindex_schedule", sa.Text(), server_default="manual_only"),
        sa.Column("index_priority", sa.Text(), server_default="normal"),
        sa.Column("index_immediately", sa.Boolean(), server_default="false"),
        sa.Column("archive_old_versions", sa.Boolean(), server_default="true"),
        sa.Column("document_retention_policy", sa.Text(), server_default="keep_all"),
        sa.Column("environment", sa.Text(), server_default="all"),
        sa.Column("icon", sa.Text(), nullable=True),
        sa.Column("tags_json", JSONB, server_default="[]"),
        sa.Column("max_context_documents", sa.Integer(), server_default="5"),
        sa.Column("category_id", UUID(as_uuid=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
    ]
    for col in cols_to_add:
        try:
            op.add_column("rag_knowledge_bases", col)
        except Exception:
            pass

    # Add unique constraint on kb_code (after populating)
    try:
        op.create_unique_constraint("uq_rag_kb_code", "rag_knowledge_bases", ["kb_code"])
    except Exception:
        pass

    # ── ALTER rag_query_logs (add answer_status, kb_id) ──────────────────────
    try:
        op.add_column("rag_query_logs", sa.Column("answer_status", sa.Text(), server_default="answered"))
    except Exception:
        pass
    try:
        op.add_column("rag_query_logs", sa.Column("kb_id", UUID(as_uuid=True), nullable=True))
    except Exception:
        pass

    # ── NEW TABLES ────────────────────────────────────────────────────────────

    op.create_table(
        "rag_documents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("kb_id", UUID(as_uuid=True), sa.ForeignKey("rag_knowledge_bases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_name", sa.Text(), nullable=False),
        sa.Column("source_type", sa.Text(), server_default="uploaded"),
        sa.Column("source_id", UUID(as_uuid=True), nullable=True),
        sa.Column("file_type", sa.Text(), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger(), server_default="0"),
        sa.Column("media_id", UUID(as_uuid=True), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("visibility", sa.Text(), server_default="internal"),
        sa.Column("indexing_status", sa.Text(), server_default="not_indexed"),
        sa.Column("chunk_count", sa.Integer(), server_default="0"),
        sa.Column("last_indexed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_rag_documents_kb_id", "rag_documents", ["kb_id"])

    op.create_table(
        "rag_manual_articles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("kb_id", UUID(as_uuid=True), sa.ForeignKey("rag_knowledge_bases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("article_title", sa.Text(), nullable=False),
        sa.Column("article_slug", sa.Text(), nullable=False),
        sa.Column("body_markdown", sa.Text(), nullable=True),
        sa.Column("tags_json", JSONB, server_default="[]"),
        sa.Column("visibility", sa.Text(), server_default="internal"),
        sa.Column("status", sa.Text(), server_default="draft"),
        sa.Column("created_by_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_rag_manual_articles_kb_id", "rag_manual_articles", ["kb_id"])

    op.create_table(
        "rag_document_chunks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("kb_id", UUID(as_uuid=True), sa.ForeignKey("rag_knowledge_bases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_id", UUID(as_uuid=True), nullable=True),
        sa.Column("article_id", UUID(as_uuid=True), nullable=True),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), server_default="0"),
        sa.Column("token_count", sa.Integer(), server_default="0"),
        sa.Column("embedding_status", sa.Text(), server_default="pending"),
        sa.Column("embedding_model", sa.Text(), nullable=True),
        sa.Column("metadata_json", JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_rag_document_chunks_kb_id", "rag_document_chunks", ["kb_id"])

    op.create_table(
        "rag_indexing_jobs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("kb_id", UUID(as_uuid=True), sa.ForeignKey("rag_knowledge_bases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_type", sa.Text(), server_default="full_index"),
        sa.Column("status", sa.Text(), server_default="queued"),
        sa.Column("documents_processed", sa.Integer(), server_default="0"),
        sa.Column("chunks_created", sa.Integer(), server_default="0"),
        sa.Column("failed_count", sa.Integer(), server_default="0"),
        sa.Column("is_dry_run", sa.Boolean(), server_default="false"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_rag_indexing_jobs_kb_id", "rag_indexing_jobs", ["kb_id"])

    op.create_table(
        "rag_retrieval_feedback",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("kb_id", UUID(as_uuid=True), sa.ForeignKey("rag_knowledge_bases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("query_log_id", UUID(as_uuid=True), nullable=True),
        sa.Column("feedback_type", sa.Text(), server_default="helpful"),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("flagged_reason", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "rag_kb_versions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("kb_id", UUID(as_uuid=True), sa.ForeignKey("rag_knowledge_bases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("snapshot_json", JSONB, server_default="{}"),
        sa.Column("changed_by_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("change_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_rag_kb_versions_kb_id", "rag_kb_versions", ["kb_id"])

    op.create_table(
        "rag_kb_audit_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("kb_id", UUID(as_uuid=True), sa.ForeignKey("rag_knowledge_bases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("action_type", sa.Text(), nullable=False),
        sa.Column("actor_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("old_value_json", JSONB, nullable=True),
        sa.Column("new_value_json", JSONB, nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("request_id", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_rag_kb_audit_logs_kb_id", "rag_kb_audit_logs", ["kb_id"])


def downgrade() -> None:
    op.drop_table("rag_kb_audit_logs")
    op.drop_table("rag_kb_versions")
    op.drop_table("rag_retrieval_feedback")
    op.drop_table("rag_indexing_jobs")
    op.drop_table("rag_document_chunks")
    op.drop_table("rag_manual_articles")
    op.drop_table("rag_documents")
