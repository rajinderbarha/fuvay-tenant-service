"""Phase 12 — Security Engine (5 tables)
Revision ID: 012
Revises: 011
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("tenant_api_keys",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id",     UUID(as_uuid=True), nullable=False),
        sa.Column("name",          sa.String(100),     nullable=False),
        sa.Column("description",   sa.String(500),     nullable=True),
        sa.Column("key_hash",      sa.String(64),      nullable=False, unique=True),
        sa.Column("key_prefix",    sa.String(8),       nullable=False, unique=True),
        sa.Column("environment",   sa.String(10),      nullable=False, server_default="live"),
        sa.Column("scopes",        JSONB,              nullable=False, server_default="[]"),
        sa.Column("status",        sa.String(20),      nullable=False, server_default="active"),
        sa.Column("expires_at",    sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at",  sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_ip",  sa.String(50),      nullable=True),
        sa.Column("use_count",     sa.Integer,         nullable=False, server_default="0"),
        sa.Column("created_by",    UUID(as_uuid=True), nullable=True),
        sa.Column("rotated_to",    UUID(as_uuid=True), nullable=True),
        sa.Column("revoked_at",    sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_by",    UUID(as_uuid=True), nullable=True),
        sa.Column("revoke_reason", sa.String(500),     nullable=True),
        sa.Column("created_at",    sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at",    sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("key_hash",   name="uq_ak_hash"),
        sa.UniqueConstraint("key_prefix", name="uq_ak_prefix"),
    )
    op.create_index("ix_ak_tenant", "tenant_api_keys", ["tenant_id"])
    op.create_index("ix_ak_status", "tenant_api_keys", ["status"])

    op.create_table("ip_blocklist",
        sa.Column("id",           UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("ip_or_cidr",   sa.String(50),      nullable=False),
        sa.Column("entry_type",   sa.String(10),      nullable=False),
        sa.Column("tenant_id",    UUID(as_uuid=True), nullable=True),
        sa.Column("reason",       sa.String(500),     nullable=False),
        sa.Column("threat_level", sa.String(20),      nullable=False),
        sa.Column("is_global",    sa.Boolean,         nullable=False, server_default="false"),
        sa.Column("is_active",    sa.Boolean,         nullable=False, server_default="true"),
        sa.Column("expires_at",   sa.DateTime(timezone=True), nullable=True),
        sa.Column("blocked_by",   UUID(as_uuid=True), nullable=True),
        sa.Column("created_at",   sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at",   sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("ip_or_cidr","tenant_id", name="uq_ibl_ip_tenant"),
    )
    op.create_index("ix_ibl_ip",     "ip_blocklist", ["ip_or_cidr"])
    op.create_index("ix_ibl_tenant", "ip_blocklist", ["tenant_id"])

    op.create_table("suspicious_activity_logs",
        sa.Column("id",             UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id",      UUID(as_uuid=True), nullable=True),
        sa.Column("entity_id",      sa.String(100),     nullable=True),
        sa.Column("entity_type",    sa.String(30),      nullable=True),
        sa.Column("activity_type",  sa.String(60),      nullable=False),
        sa.Column("threat_level",   sa.String(20),      nullable=False),
        sa.Column("description",    sa.String(500),     nullable=False),
        sa.Column("ip_address",     sa.String(50),      nullable=True),
        sa.Column("user_agent",     sa.String(500),     nullable=True),
        sa.Column("detected_value", sa.Integer,         nullable=False),
        sa.Column("threshold",      sa.Integer,         nullable=False),
        sa.Column("context",        JSONB,              nullable=False, server_default="{}"),
        sa.Column("status",         sa.String(20),      nullable=False, server_default="open"),
        sa.Column("acknowledged_by",UUID(as_uuid=True), nullable=True),
        sa.Column("acknowledged_at",sa.DateTime(timezone=True), nullable=True),
        sa.Column("auto_actioned",  sa.Boolean,         nullable=False, server_default="false"),
        sa.Column("created_at",     sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at",     sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_sal_entity",  "suspicious_activity_logs", ["entity_id"])
    op.create_index("ix_sal_type",    "suspicious_activity_logs", ["activity_type"])
    op.create_index("ix_sal_threat",  "suspicious_activity_logs", ["threat_level"])
    op.create_index("ix_sal_created", "suspicious_activity_logs", ["created_at"])
    op.create_index("ix_sal_tenant",  "suspicious_activity_logs", ["tenant_id"])

    op.create_table("platform_audit_logs",
        sa.Column("id",           UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id",    UUID(as_uuid=True), nullable=True),
        sa.Column("actor_id",     UUID(as_uuid=True), nullable=True),
        sa.Column("actor_role",   sa.String(30),      nullable=True),
        sa.Column("actor_ip",     sa.String(50),      nullable=True),
        sa.Column("operation",    sa.String(100),     nullable=False),
        sa.Column("engine_id",    sa.String(50),      nullable=False),
        sa.Column("entity_type",  sa.String(50),      nullable=True),
        sa.Column("entity_id",    sa.String(100),     nullable=True),
        sa.Column("before_state", JSONB,              nullable=True),
        sa.Column("after_state",  JSONB,              nullable=True),
        sa.Column("request_id",   sa.String(100),     nullable=True),
        sa.Column("is_high_risk", sa.Boolean,         nullable=False, server_default="false"),
        sa.Column("meta",         JSONB,              nullable=False, server_default="{}"),
        sa.Column("created_at",   sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at",   sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_pal_actor",     "platform_audit_logs", ["actor_id"])
    op.create_index("ix_pal_tenant",    "platform_audit_logs", ["tenant_id"])
    op.create_index("ix_pal_operation", "platform_audit_logs", ["operation"])
    op.create_index("ix_pal_created",   "platform_audit_logs", ["created_at"])
    op.create_index("ix_pal_entity",    "platform_audit_logs", ["entity_type", "entity_id"])

    op.create_table("session_inventory",
        sa.Column("id",           UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id",      UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id",    UUID(as_uuid=True), nullable=True),
        sa.Column("session_id",   sa.String(100),     nullable=False, unique=True),
        sa.Column("device_info",  JSONB,              nullable=False, server_default="{}"),
        sa.Column("ip_address",   sa.String(50),      nullable=True),
        sa.Column("user_agent",   sa.String(500),     nullable=True),
        sa.Column("is_active",    sa.Boolean,         nullable=False, server_default="true"),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expires_at",   sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at",   sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_by",   UUID(as_uuid=True), nullable=True),
        sa.Column("revoke_reason",sa.String(200),     nullable=True),
        sa.Column("created_at",   sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at",   sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("session_id", name="uq_si_session_id"),
    )
    op.create_index("ix_si_user",   "session_inventory", ["user_id"])
    op.create_index("ix_si_tenant", "session_inventory", ["tenant_id"])
    op.create_index("ix_si_active", "session_inventory", ["is_active"])


def downgrade() -> None:
    for t in ["session_inventory","platform_audit_logs","suspicious_activity_logs",
              "ip_blocklist","tenant_api_keys"]:
        op.drop_table(t)
