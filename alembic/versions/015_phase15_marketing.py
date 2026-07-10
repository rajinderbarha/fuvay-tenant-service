"""Phase 15 — Marketing Automation Engine (5 tables)
Revision ID: 015
Revises: 014
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("social_accounts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("platform",          sa.String(20),  nullable=False),
        sa.Column("page_id",           sa.String(100), nullable=False),
        sa.Column("page_name",         sa.String(200), nullable=False),
        sa.Column("ig_user_id",        sa.String(100), nullable=True),
        sa.Column("access_token",      sa.Text,        nullable=False),
        sa.Column("token_expires_at",  sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_refreshed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status",            sa.String(20),  nullable=False, server_default="active"),
        sa.Column("follower_count",    sa.Integer,     nullable=False, server_default="0"),
        sa.Column("post_count",        sa.Integer,     nullable=False, server_default="0"),
        sa.Column("is_primary",        sa.Boolean,     nullable=False, server_default="false"),
        sa.Column("meta",              JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("platform","page_id", name="uq_sa_platform_page"),
    )
    op.create_index("ix_sa_platform", "social_accounts", ["platform"])
    op.create_index("ix_sa_status",   "social_accounts", ["status"])

    op.create_table("content_templates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("post_type",        sa.String(50),  nullable=False),
        sa.Column("vertical",         sa.String(50),  nullable=True),
        sa.Column("name",             sa.String(200), nullable=False),
        sa.Column("dalle_prompt",     sa.Text,        nullable=False),
        sa.Column("caption_template", sa.Text,        nullable=False),
        sa.Column("required_vars",    JSONB, nullable=False, server_default="[]"),
        sa.Column("default_tags",     JSONB, nullable=False, server_default="[]"),
        sa.Column("is_active",        sa.Boolean, nullable=False, server_default="true"),
        sa.Column("version",          sa.String(10), nullable=False, server_default="1.0"),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_ct_post_type", "content_templates", ["post_type"])

    op.create_table("generated_assets",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("post_type",       sa.String(50),   nullable=False),
        sa.Column("dalle_model",     sa.String(30),   nullable=False),
        sa.Column("dalle_size",      sa.String(20),   nullable=False),
        sa.Column("prompt_used",     sa.Text,         nullable=False),
        sa.Column("prompt_hash",     sa.String(64),   nullable=False),
        sa.Column("generated_date",  sa.String(10),   nullable=False),
        sa.Column("cost_inr",        sa.Numeric(8,2), nullable=False),
        sa.Column("dalle_url",       sa.String(2000), nullable=True),
        sa.Column("media_file_id",   UUID(as_uuid=True), nullable=True),
        sa.Column("storage_key",     sa.String(500),  nullable=True),
        sa.Column("api_response",    JSONB, nullable=False, server_default="{}"),
        sa.Column("variables_used",  JSONB, nullable=False, server_default="{}"),
        sa.Column("generated_by",    sa.String(20),   nullable=False,
                  server_default="celery"),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("prompt_hash","generated_date", name="uq_ga_prompt_date"),
    )
    op.create_index("ix_ga_post_type", "generated_assets", ["post_type"])
    op.create_index("ix_ga_created",   "generated_assets", ["created_at"])

    op.create_table("scheduled_posts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("account_id",     UUID(as_uuid=True), nullable=False),
        sa.Column("post_type",      sa.String(50),  nullable=False),
        sa.Column("template_id",    UUID(as_uuid=True), nullable=True),
        sa.Column("asset_id",       UUID(as_uuid=True), nullable=True),
        sa.Column("tenant_id",      UUID(as_uuid=True), nullable=True),
        sa.Column("scheduled_date", sa.String(10),  nullable=False),
        sa.Column("scheduled_at",   sa.DateTime(timezone=True), nullable=False),
        sa.Column("status",         sa.String(20),  nullable=False, server_default="draft"),
        sa.Column("caption",        sa.Text,        nullable=True),
        sa.Column("tags",           JSONB, nullable=False, server_default="[]"),
        sa.Column("variables",      JSONB, nullable=False, server_default="{}"),
        sa.Column("published_at",   sa.DateTime(timezone=True), nullable=True),
        sa.Column("meta_post_id",   sa.String(100), nullable=True),
        sa.Column("cancelled_at",   sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_reason",  sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        # PROVEN: prevents duplicate post for same type on same date on same account
        sa.UniqueConstraint("post_type","scheduled_date","account_id",
                            name="uq_sp_post_date_account"),
    )
    op.create_index("ix_sp_status",    "scheduled_posts", ["status"])
    op.create_index("ix_sp_scheduled", "scheduled_posts", ["scheduled_at"])
    op.create_index("ix_sp_account",   "scheduled_posts", ["account_id"])

    op.create_table("post_deliveries",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("scheduled_post_id", UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("account_id",        UUID(as_uuid=True), nullable=False),
        sa.Column("platform",          sa.String(20),  nullable=False),
        sa.Column("status",            sa.String(20),  nullable=False),
        sa.Column("http_status",       sa.Integer,     nullable=True),
        sa.Column("response_body",     JSONB, nullable=False, server_default="{}"),
        sa.Column("meta_post_id",      sa.String(100), nullable=True),
        sa.Column("meta_media_id",     sa.String(100), nullable=True),
        sa.Column("latency_ms",        sa.Integer,     nullable=True),
        sa.Column("attempt_count",     sa.Integer,     nullable=False, server_default="1"),
        sa.Column("error_message",     sa.String(500), nullable=True),
        sa.Column("delivered_at",      sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        # PROVEN: one delivery per scheduled post
        sa.UniqueConstraint("scheduled_post_id", name="uq_pd_post"),
    )
    op.create_index("ix_pd_status",  "post_deliveries", ["status"])
    op.create_index("ix_pd_account", "post_deliveries", ["account_id"])
    op.create_index("ix_pd_created", "post_deliveries", ["created_at"])


def downgrade() -> None:
    for t in ["post_deliveries","scheduled_posts","generated_assets",
              "content_templates","social_accounts"]:
        op.drop_table(t)
