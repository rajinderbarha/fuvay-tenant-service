"""Phase 5 — Settings + Notification + Media + Analytics (11 tables)

Revision ID: 005
Revises: 004
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Settings (4 tables) ───────────────────────────────────────────────────
    op.create_table("platform_settings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("key", sa.String(200), nullable=False, unique=True),
        sa.Column("value", JSONB, nullable=False),
        sa.Column("setting_type", sa.String(20), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("is_public", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("set_by", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("key", name="uq_ps_key"),
    )
    op.create_table("plan_settings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("plan_type", sa.String(30), nullable=False),
        sa.Column("key", sa.String(200), nullable=False),
        sa.Column("value", JSONB, nullable=False),
        sa.Column("setting_type", sa.String(20), nullable=False),
        sa.Column("set_by", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("plan_type","key", name="uq_plan_setting"),
    )
    op.create_index("ix_plan_setting_key","plan_settings",["plan_type","key"])
    op.create_table("tenant_settings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("key", sa.String(200), nullable=False),
        sa.Column("value", JSONB, nullable=False),
        sa.Column("setting_type", sa.String(20), nullable=False),
        sa.Column("set_by", UUID(as_uuid=True), nullable=True),
        sa.Column("reason", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("tenant_id","key", name="uq_tenant_setting"),
    )
    op.create_index("ix_tenant_setting_key","tenant_settings",["tenant_id","key"])
    op.create_table("setting_audit_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=True),
        sa.Column("tier", sa.String(20), nullable=False),
        sa.Column("key", sa.String(200), nullable=False),
        sa.Column("old_value", JSONB, nullable=True),
        sa.Column("new_value", JSONB, nullable=False),
        sa.Column("changed_by", UUID(as_uuid=True), nullable=True),
        sa.Column("reason", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_sal_tenant_key","setting_audit_logs",["tenant_id","key"])

    # ── Notification (3 tables) ───────────────────────────────────────────────
    op.create_table("notification_templates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=True),
        sa.Column("notif_type", sa.String(80), nullable=False),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("variables", JSONB, nullable=False, server_default="[]"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("vertical", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("tenant_id","notif_type","channel", name="uq_nt_tenant_type_channel"),
    )
    op.create_index("ix_nt_tenant","notification_templates",["tenant_id"])
    op.create_table("notification_records",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("recipient_id", UUID(as_uuid=True), nullable=False),
        sa.Column("recipient_type", sa.String(30), nullable=False),
        sa.Column("notif_type", sa.String(80), nullable=False),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("data", JSONB, nullable=False, server_default="{}"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("attempt_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_reason", sa.String(500), nullable=True),
        sa.Column("idempotency_key", sa.String(255), nullable=True, unique=True),
        sa.Column("reference_id", sa.String(100), nullable=True),
        sa.Column("reference_type", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_nr_tenant","notification_records",["tenant_id"])
    op.create_index("ix_nr_recipient","notification_records",["recipient_id"])
    op.create_index("ix_nr_status","notification_records",["status"])
    op.create_index("ix_nr_created","notification_records",["created_at"])
    op.create_table("notification_channel_configs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("is_enabled", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("config", JSONB, nullable=False, server_default="{}"),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("tenant_id","channel", name="uq_ncc_tenant_channel"),
    )

    # ── Media (2 tables) ──────────────────────────────────────────────────────
    op.create_table("media_files",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", UUID(as_uuid=True), nullable=False),
        sa.Column("entity_type", sa.String(60), nullable=True),
        sa.Column("entity_id", sa.String(100), nullable=True),
        sa.Column("original_name", sa.String(255), nullable=False),
        sa.Column("storage_key", sa.String(500), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("size_bytes", sa.Integer, nullable=False),
        sa.Column("is_public", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scan_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("meta", JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_mf_tenant_entity","media_files",["tenant_id","entity_type","entity_id"])
    op.create_index("ix_mf_owner","media_files",["owner_id"])
    op.create_table("media_upload_sessions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", UUID(as_uuid=True), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("size_bytes", sa.Integer, nullable=False),
        sa.Column("storage_key", sa.String(500), nullable=False),
        sa.Column("upload_url", sa.String(2000), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("entity_type", sa.String(60), nullable=True),
        sa.Column("entity_id", sa.String(100), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_mus_tenant","media_upload_sessions",["tenant_id"])

    # ── Analytics (2 tables) ──────────────────────────────────────────────────
    op.create_table("analytics_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("event_id", sa.String(100), nullable=False, unique=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("engine_id", sa.String(50), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=True),
        sa.Column("entity_id", sa.String(100), nullable=True),
        sa.Column("actor_id", UUID(as_uuid=True), nullable=True),
        sa.Column("payload", JSONB, nullable=False, server_default="{}"),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("event_id", name="uq_ae_event_id"),
    )
    op.create_index("ix_ae_tenant_type","analytics_events",["tenant_id","event_type"])
    op.create_index("ix_ae_created","analytics_events",["created_at"])
    op.create_table("daily_metrics",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=True),
        sa.Column("metric_date", sa.Date, nullable=False),
        sa.Column("metric_key", sa.String(100), nullable=False),
        sa.Column("value_num", sa.Numeric(14,4), nullable=True),
        sa.Column("value_json", JSONB, nullable=True),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("tenant_id","metric_date","metric_key", name="uq_dm_tenant_date_key"),
    )
    op.create_index("ix_dm_tenant_date","daily_metrics",["tenant_id","metric_date"])


def downgrade() -> None:
    for t in ["daily_metrics","analytics_events","media_upload_sessions","media_files",
              "notification_channel_configs","notification_records","notification_templates",
              "setting_audit_logs","tenant_settings","plan_settings","platform_settings"]:
        op.drop_table(t)
