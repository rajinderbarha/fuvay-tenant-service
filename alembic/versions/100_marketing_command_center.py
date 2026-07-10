"""Marketing Automation Command Center — migration 100.

Extends the two pre-existing marketing engines (Sprint 15 `app/engines/marketing`
and Sprint 29 `app/engines/marketing_automation`) additively rather than
duplicating them, and adds the new tables needed for the enterprise command
center: posts, post assets, AI budget + ledger, content templates (v2),
publish attempts, and audit logs.

Platform-pays-AI-cost rule: marketing_ai_budget / marketing_ai_budget_ledger
are entirely separate from tenant_wallets / customer_service_credits — no FK,
no shared table, so tenant usage credits can never be touched by this engine.

Revision ID: 100
Revises: 099
"""
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import text

revision = "100"
down_revision = "099"
branch_labels = None
depends_on = None


def _col_exists(conn, table: str, col: str) -> bool:
    r = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.columns WHERE table_name=:t AND column_name=:c"),
        {"t": table, "c": col})
    return bool(r.fetchone())


def upgrade() -> None:
    conn = op.get_bind()

    # ── Extend marketing_campaigns (Sprint 29) additively ──────────────────────
    if not _col_exists(conn, "marketing_campaigns", "goal"):
        op.add_column("marketing_campaigns", sa.Column("goal", sa.Text, nullable=True))
    if not _col_exists(conn, "marketing_campaigns", "vertical_key"):
        op.add_column("marketing_campaigns", sa.Column("vertical_key", sa.Text, nullable=True))
    if not _col_exists(conn, "marketing_campaigns", "budget_amount"):
        op.add_column("marketing_campaigns", sa.Column("budget_amount", sa.Numeric(10, 2), nullable=True))
    if not _col_exists(conn, "marketing_campaigns", "budget_used_amount"):
        op.add_column("marketing_campaigns", sa.Column("budget_used_amount", sa.Numeric(10, 2), nullable=False, server_default="0"))
    if not _col_exists(conn, "marketing_campaigns", "channels_json"):
        op.add_column("marketing_campaigns", sa.Column("channels_json", JSONB, nullable=True))
    if not _col_exists(conn, "marketing_campaigns", "owner_user_id"):
        op.add_column("marketing_campaigns", sa.Column("owner_user_id", UUID(as_uuid=True), nullable=True))

    # ── Extend social_accounts (Sprint 15) additively ──────────────────────────
    if not _col_exists(conn, "social_accounts", "publishing_enabled"):
        op.add_column("social_accounts", sa.Column("publishing_enabled", sa.Boolean, nullable=False, server_default="true"))
    if not _col_exists(conn, "social_accounts", "daily_post_limit"):
        op.add_column("social_accounts", sa.Column("daily_post_limit", sa.Integer, nullable=False, server_default="10"))
    if not _col_exists(conn, "social_accounts", "connection_status"):
        op.add_column("social_accounts", sa.Column("connection_status", sa.Text, nullable=False, server_default="connected"))
    if not _col_exists(conn, "social_accounts", "last_sync_at"):
        op.add_column("social_accounts", sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True))

    # ── marketing_posts ─────────────────────────────────────────────────────────
    op.create_table(
        "marketing_posts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
        sa.Column("post_code", sa.Text, unique=True, nullable=False),
        sa.Column("campaign_id", UUID(as_uuid=True), sa.ForeignKey("marketing_campaigns.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("caption", sa.Text, nullable=True),
        sa.Column("short_caption", sa.Text, nullable=True),
        sa.Column("hashtags_json", JSONB, nullable=True),
        sa.Column("vertical_key", sa.Text, nullable=True),
        sa.Column("category_id", UUID(as_uuid=True), nullable=True),
        sa.Column("service_id", UUID(as_uuid=True), nullable=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=True),
        sa.Column("target_locations_json", JSONB, nullable=True),
        sa.Column("language", sa.Text, nullable=False, server_default="english"),
        sa.Column("tone", sa.Text, nullable=True),
        sa.Column("post_type", sa.Text, nullable=False, server_default="image_post"),
        sa.Column("goal", sa.Text, nullable=True),
        sa.Column("cta", sa.Text, nullable=True),
        sa.Column("channels_json", JSONB, nullable=True),
        sa.Column("status", sa.Text, nullable=False, server_default="draft"),
        sa.Column("approval_status", sa.Text, nullable=False, server_default="not_required"),
        sa.Column("approved_by_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text, nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=text("now()")),
    )
    op.create_index("ix_mpost_status", "marketing_posts", ["status"])
    op.create_index("ix_mpost_campaign", "marketing_posts", ["campaign_id"])
    op.create_index("ix_mpost_scheduled", "marketing_posts", ["scheduled_at"])
    op.create_index("ix_mpost_vertical", "marketing_posts", ["vertical_key"])

    # ── marketing_post_assets ────────────────────────────────────────────────────
    op.create_table(
        "marketing_post_assets",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
        sa.Column("post_id", UUID(as_uuid=True), sa.ForeignKey("marketing_posts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("asset_type", sa.Text, nullable=False, server_default="image"),
        sa.Column("media_id", UUID(as_uuid=True), nullable=True),
        sa.Column("url", sa.Text, nullable=True),
        sa.Column("generated_by_ai", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("ai_model", sa.Text, nullable=True),
        sa.Column("ai_prompt", sa.Text, nullable=True),
        sa.Column("alt_text", sa.Text, nullable=True),
        sa.Column("cost_amount", sa.Numeric(10, 2), nullable=True),
        sa.Column("status", sa.Text, nullable=False, server_default="ready"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=text("now()")),
    )
    op.create_index("ix_mpasset_post", "marketing_post_assets", ["post_id"])

    # ── marketing_ai_budget (single-row-per-scope platform budget config) ───────
    op.create_table(
        "marketing_ai_budget",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
        sa.Column("scope", sa.Text, unique=True, nullable=False, server_default="platform"),
        sa.Column("daily_budget", sa.Numeric(10, 2), nullable=False, server_default="500"),
        sa.Column("monthly_budget", sa.Numeric(10, 2), nullable=False, server_default="10000"),
        sa.Column("cost_alert_threshold_pct", sa.Integer, nullable=False, server_default="80"),
        sa.Column("auto_disable_on_exceed", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("require_approval_above_cost", sa.Numeric(10, 2), nullable=True),
        sa.Column("updated_by_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=text("now()")),
    )

    # ── marketing_ai_budget_ledger ───────────────────────────────────────────────
    op.create_table(
        "marketing_ai_budget_ledger",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
        sa.Column("generation_type", sa.Text, nullable=False),
        sa.Column("model", sa.Text, nullable=True),
        sa.Column("cost_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("post_id", UUID(as_uuid=True), sa.ForeignKey("marketing_posts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("campaign_id", UUID(as_uuid=True), sa.ForeignKey("marketing_campaigns.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_by_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=text("now()")),
    )
    op.create_index("ix_maibl_created", "marketing_ai_budget_ledger", ["created_at"])

    # ── marketing_content_templates (v2 — richer than Sprint 15 content_templates) ──
    op.create_table(
        "marketing_content_templates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
        sa.Column("template_name", sa.Text, nullable=False),
        sa.Column("vertical_key", sa.Text, nullable=True),
        sa.Column("post_type", sa.Text, nullable=False, server_default="image_post"),
        sa.Column("language", sa.Text, nullable=False, server_default="english"),
        sa.Column("prompt_template", sa.Text, nullable=True),
        sa.Column("caption_structure", sa.Text, nullable=True),
        sa.Column("hashtag_set_json", JSONB, nullable=True),
        sa.Column("cta", sa.Text, nullable=True),
        sa.Column("status", sa.Text, nullable=False, server_default="active"),
        sa.Column("created_by_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=text("now()")),
    )

    # ── marketing_publish_attempts ───────────────────────────────────────────────
    op.create_table(
        "marketing_publish_attempts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
        sa.Column("post_id", UUID(as_uuid=True), sa.ForeignKey("marketing_posts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("channel", sa.Text, nullable=False),
        sa.Column("social_account_id", UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.Text, nullable=False, server_default="pending"),
        sa.Column("attempt_number", sa.Integer, nullable=False, server_default="1"),
        sa.Column("external_post_id", sa.Text, nullable=True),
        sa.Column("error_code", sa.Text, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=text("now()")),
    )
    op.create_index("ix_mpattempt_post", "marketing_publish_attempts", ["post_id"])
    op.create_index("ix_mpattempt_status", "marketing_publish_attempts", ["status"])

    # ── marketing_audit_logs ─────────────────────────────────────────────────────
    op.create_table(
        "marketing_audit_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
        sa.Column("actor_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("action_type", sa.Text, nullable=False),
        sa.Column("target_type", sa.Text, nullable=False),
        sa.Column("target_id", sa.Text, nullable=True),
        sa.Column("old_value_json", JSONB, nullable=True),
        sa.Column("new_value_json", JSONB, nullable=True),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("request_id", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=text("now()")),
    )
    op.create_index("ix_maudit_action", "marketing_audit_logs", ["action_type"])
    op.create_index("ix_maudit_created", "marketing_audit_logs", ["created_at"])

    # Seed a default platform AI budget row so GET /ai-budget never 404s.
    op.execute(text(
        "INSERT INTO marketing_ai_budget (id, scope, daily_budget, monthly_budget) "
        "VALUES (gen_random_uuid(), 'platform', 500, 10000) "
        "ON CONFLICT (scope) DO NOTHING"
    ))


def downgrade() -> None:
    op.drop_table("marketing_audit_logs")
    op.drop_table("marketing_publish_attempts")
    op.drop_table("marketing_content_templates")
    op.drop_table("marketing_ai_budget_ledger")
    op.drop_table("marketing_ai_budget")
    op.drop_table("marketing_post_assets")
    op.drop_table("marketing_posts")
    for col in ("last_sync_at", "connection_status", "daily_post_limit", "publishing_enabled"):
        op.drop_column("social_accounts", col)
    for col in ("owner_user_id", "channels_json", "budget_used_amount", "budget_amount", "vertical_key", "goal"):
        op.drop_column("marketing_campaigns", col)
