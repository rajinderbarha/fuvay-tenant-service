"""Phase 11 — Review + Chat + Webhook (8 tables)
Revision ID: 011
Revises: 010
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Review (4 tables) ────────────────────────────────────────────────────
    op.create_table("reviews",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id",       UUID(as_uuid=True), nullable=False),
        sa.Column("job_id",          sa.String(100),     nullable=False),
        sa.Column("customer_id",     UUID(as_uuid=True), nullable=False),
        sa.Column("staff_id",        UUID(as_uuid=True), nullable=True),
        sa.Column("overall_quality", sa.Float, nullable=False),
        sa.Column("punctuality",     sa.Float, nullable=False),
        sa.Column("cleanliness",     sa.Float, nullable=False),
        sa.Column("value_for_money", sa.Float, nullable=False),
        sa.Column("communication",   sa.Float, nullable=False),
        sa.Column("composite_score", sa.Float, nullable=False),
        sa.Column("comment",         sa.Text,  nullable=True),
        sa.Column("status",          sa.String(20), nullable=False, server_default="published"),
        sa.Column("tenant_reply",    sa.Text,  nullable=True),
        sa.Column("replied_at",      sa.DateTime(timezone=True), nullable=True),
        sa.Column("replied_by",      UUID(as_uuid=True), nullable=True),
        sa.Column("flagged_reason",  sa.String(500), nullable=True),
        sa.Column("flagged_by",      UUID(as_uuid=True), nullable=True),
        sa.Column("resolved_by",     UUID(as_uuid=True), nullable=True),
        sa.Column("idempotency_key", sa.String(64), nullable=True, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("customer_id","job_id", name="uq_review_customer_job"),
    )
    op.create_index("ix_rv_tenant","reviews",["tenant_id"])
    op.create_index("ix_rv_staff","reviews",["staff_id"])
    op.create_index("ix_rv_status","reviews",["status"])

    op.create_table("review_requests",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("job_id",      sa.String(100),     nullable=False, unique=True),
        sa.Column("tenant_id",   UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", UUID(as_uuid=True), nullable=False),
        sa.Column("staff_id",    UUID(as_uuid=True), nullable=True),
        sa.Column("status",      sa.String(20),      nullable=False, server_default="sent"),
        sa.Column("expires_at",  sa.DateTime(timezone=True), nullable=False),
        sa.Column("review_id",   UUID(as_uuid=True), nullable=True),
        sa.Column("notified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at",  sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at",  sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("job_id", name="uq_rvreq_job"),
    )
    op.create_index("ix_rvreq_customer","review_requests",["customer_id"])

    op.create_table("review_aggregates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("entity_type",       sa.String(20),      nullable=False),
        sa.Column("entity_id",         sa.String(100),     nullable=False),
        sa.Column("tenant_id",         UUID(as_uuid=True), nullable=False),
        sa.Column("review_count",      sa.Integer, nullable=False, server_default="0"),
        sa.Column("avg_composite",     sa.Float,   nullable=False, server_default="0"),
        sa.Column("avg_quality",       sa.Float,   nullable=False, server_default="0"),
        sa.Column("avg_punctuality",   sa.Float,   nullable=False, server_default="0"),
        sa.Column("avg_cleanliness",   sa.Float,   nullable=False, server_default="0"),
        sa.Column("avg_value",         sa.Float,   nullable=False, server_default="0"),
        sa.Column("avg_communication", sa.Float,   nullable=False, server_default="0"),
        sa.Column("reply_rate",        sa.Float,   nullable=False, server_default="0"),
        sa.Column("last_computed_at",  sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at",  sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at",  sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("entity_type","entity_id", name="uq_rvagg_entity"),
    )
    op.create_index("ix_rvagg_tenant","review_aggregates",["tenant_id"])

    op.create_table("review_status_history",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("review_id",   UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id",   UUID(as_uuid=True), nullable=False),
        sa.Column("from_status", sa.String(20), nullable=True),
        sa.Column("to_status",   sa.String(20), nullable=False),
        sa.Column("changed_by",  UUID(as_uuid=True), nullable=True),
        sa.Column("reason",      sa.String(500), nullable=True),
        sa.Column("created_at",  sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at",  sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_rvsh_review","review_status_history",["review_id"])

    # ── Chat (2 tables) ──────────────────────────────────────────────────────
    op.create_table("conversations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id",      UUID(as_uuid=True), nullable=False),
        sa.Column("entity_type",    sa.String(20),      nullable=False),
        sa.Column("entity_id",      sa.String(100),     nullable=False),
        sa.Column("status",         sa.String(20),      nullable=False, server_default="active"),
        sa.Column("message_count",  sa.Integer, nullable=False, server_default="0"),
        sa.Column("participants",   JSONB, nullable=False, server_default="[]"),
        sa.Column("last_message_at",sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_message_preview", sa.String(200), nullable=True),
        sa.Column("meta",           JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at",  sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at",  sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("entity_type","entity_id","tenant_id", name="uq_conv_entity"),
    )
    op.create_index("ix_conv_tenant","conversations",["tenant_id"])
    op.create_index("ix_conv_entity","conversations",["entity_type","entity_id"])

    op.create_table("messages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("conversation_id",UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id",      UUID(as_uuid=True), nullable=False),
        sa.Column("sender_id",      UUID(as_uuid=True), nullable=True),
        sa.Column("sender_role",    sa.String(20),      nullable=False),
        sa.Column("message_type",   sa.String(20),      nullable=False, server_default="text"),
        sa.Column("content",        sa.Text,            nullable=False),
        sa.Column("media_id",       UUID(as_uuid=True), nullable=True),
        sa.Column("read_by",        JSONB, nullable=False, server_default="{}"),
        sa.Column("is_deleted",     sa.Boolean, nullable=False, server_default="false"),
        sa.Column("deleted_at",     sa.DateTime(timezone=True), nullable=True),
        sa.Column("edited_at",      sa.DateTime(timezone=True), nullable=True),
        sa.Column("idempotency_key",sa.String(255), nullable=True, unique=True),
        sa.Column("meta",           JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at",  sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at",  sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("idempotency_key", name="uq_msg_idem"),
    )
    op.create_index("ix_msg_conversation","messages",["conversation_id"])
    op.create_index("ix_msg_sender","messages",["sender_id"])
    op.create_index("ix_msg_created","messages",["created_at"])

    # ── Webhook (2 tables) ───────────────────────────────────────────────────
    op.create_table("webhook_endpoints",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id",            UUID(as_uuid=True), nullable=False),
        sa.Column("url",                  sa.String(2000),    nullable=False),
        sa.Column("secret",               sa.String(100),     nullable=False),
        sa.Column("description",          sa.String(255),     nullable=True),
        sa.Column("subscribed_events",    JSONB, nullable=False, server_default="[]"),
        sa.Column("status",               sa.String(20), nullable=False, server_default="active"),
        sa.Column("consecutive_failures", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_deliveries",     sa.Integer, nullable=False, server_default="0"),
        sa.Column("success_rate",         JSONB, nullable=False, server_default="100.0"),
        sa.Column("last_success_at",      sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_failure_at",      sa.DateTime(timezone=True), nullable=True),
        sa.Column("auto_paused_at",       sa.DateTime(timezone=True), nullable=True),
        sa.Column("headers",              JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at",  sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at",  sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_we_tenant","webhook_endpoints",["tenant_id"])

    op.create_table("webhook_deliveries",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("endpoint_id",     UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id",       UUID(as_uuid=True), nullable=False),
        sa.Column("event_id",        sa.String(100), nullable=False),
        sa.Column("event_type",      sa.String(80),  nullable=False),
        sa.Column("payload",         JSONB, nullable=False),
        sa.Column("status",          sa.String(20), nullable=False, server_default="queued"),
        sa.Column("attempt_count",   sa.Integer, nullable=False, server_default="0"),
        sa.Column("response_status", sa.Integer, nullable=True),
        sa.Column("response_body",   sa.Text,    nullable=True),
        sa.Column("latency_ms",      sa.Integer, nullable=True),
        sa.Column("signature",       sa.String(64), nullable=True),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at",    sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_reason",  sa.String(500), nullable=True),
        sa.Column("is_replay",       JSONB, nullable=False, server_default="false"),
        sa.Column("original_delivery_id", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at",  sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at",  sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("event_id","endpoint_id", name="uq_wd_event_endpoint"),
    )
    op.create_index("ix_wd_endpoint","webhook_deliveries",["endpoint_id"])
    op.create_index("ix_wd_tenant","webhook_deliveries",["tenant_id"])
    op.create_index("ix_wd_status","webhook_deliveries",["status"])


def downgrade() -> None:
    for t in ["webhook_deliveries","webhook_endpoints","messages","conversations",
              "review_status_history","review_aggregates","review_requests","reviews"]:
        op.drop_table(t)
