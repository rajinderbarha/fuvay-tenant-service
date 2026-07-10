"""Sprint 29 — AI Hardening + Marketing Automation tables.

Revision: 047
Down revision: 046

New tables:
  ai_action_logs              — structured AI action audit (per backend_action_request)
  marketing_campaigns         — campaign lifecycle
  marketing_campaign_rules    — targeting/schedule/channel rules
  marketing_campaign_messages — per-channel message content
  marketing_campaign_events   — delivery/conversion tracking
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision      = "047"
down_revision = "046"
branch_labels = None
depends_on    = None


def upgrade() -> None:
    # ── ai_action_logs ────────────────────────────────────────────────────────
    op.create_table(
        "ai_action_logs",
        sa.Column("id",               UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("session_id",       UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("customer_id",      UUID(as_uuid=True), nullable=True,  index=True),
        sa.Column("action",           sa.String(100), nullable=False),
        sa.Column("intent",           sa.String(100), nullable=True),
        sa.Column("flow_type",        sa.String(100), nullable=True),
        sa.Column("draft_type",       sa.String(100), nullable=True),
        sa.Column("draft_id",         UUID(as_uuid=True), nullable=True),
        # requested / validated / executed / blocked / failed
        sa.Column("status",           sa.String(50),  nullable=False, server_default="requested"),
        sa.Column("failure_code",     sa.String(100), nullable=True),
        sa.Column("failure_message",  sa.Text,        nullable=True),
        sa.Column("request_payload",  JSONB,          nullable=True),
        sa.Column("response_payload", JSONB,          nullable=True),
        sa.Column("created_at",       sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.text("now()")),
    )

    # ── marketing_campaigns ───────────────────────────────────────────────────
    op.create_table(
        "marketing_campaigns",
        sa.Column("id",                  UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("campaign_key",        sa.String(200), nullable=False, unique=True),
        sa.Column("campaign_name",       sa.String(300), nullable=False),
        # announcement/promotion/reactivation/provider_boost/category_launch/
        # wallet_reminder/subscription_reminder/review_request/complaint_followup
        sa.Column("campaign_type",       sa.String(100), nullable=False),
        # draft/scheduled/running/paused/completed/cancelled/failed
        sa.Column("status",              sa.String(50),  nullable=False, server_default="draft"),
        # customers/providers/staff/admins
        sa.Column("target_audience",     sa.String(50),  nullable=False),
        sa.Column("category_id",         UUID(as_uuid=True), nullable=True),
        sa.Column("tenant_id",           UUID(as_uuid=True), nullable=True),
        sa.Column("city",                sa.String(100), nullable=True),
        sa.Column("zone_id",             UUID(as_uuid=True), nullable=True),
        sa.Column("starts_at",           sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at",             sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id",  UUID(as_uuid=True), nullable=True),
        sa.Column("created_at",          sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at",          sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_mcamp_status",   "marketing_campaigns", ["status"])
    op.create_index("ix_mcamp_type",     "marketing_campaigns", ["campaign_type"])
    op.create_index("ix_mcamp_audience", "marketing_campaigns", ["target_audience"])

    # ── marketing_campaign_rules ──────────────────────────────────────────────
    op.create_table(
        "marketing_campaign_rules",
        sa.Column("id",          UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("campaign_id", UUID(as_uuid=True), nullable=False, index=True),
        # segment/trigger/schedule/limit/channel
        sa.Column("rule_type",   sa.String(50),  nullable=False),
        sa.Column("rule_config", JSONB,          nullable=False, server_default="{}"),
        sa.Column("is_active",   sa.Boolean,     nullable=False, server_default="true"),
        sa.Column("created_at",  sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at",  sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.text("now()")),
    )

    # ── marketing_campaign_messages ───────────────────────────────────────────
    op.create_table(
        "marketing_campaign_messages",
        sa.Column("id",           UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("campaign_id",  UUID(as_uuid=True), nullable=False, index=True),
        # in_app/email/sms/whatsapp/push
        sa.Column("channel",      sa.String(50),  nullable=False),
        sa.Column("title",        sa.String(300), nullable=False),
        sa.Column("body",         sa.Text,        nullable=False),
        sa.Column("action_label", sa.String(100), nullable=True),
        sa.Column("action_url",   sa.String(500), nullable=True),
        sa.Column("is_active",    sa.Boolean,     nullable=False, server_default="true"),
        sa.Column("created_at",   sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at",   sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.text("now()")),
    )

    # ── marketing_campaign_events ─────────────────────────────────────────────
    op.create_table(
        "marketing_campaign_events",
        sa.Column("id",                  UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("campaign_id",         UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("recipient_user_id",   UUID(as_uuid=True), nullable=True,  index=True),
        sa.Column("tenant_id",           UUID(as_uuid=True), nullable=True),
        # targeted/sent/delivered/opened/clicked/converted/failed/skipped
        sa.Column("event_type",          sa.String(50),  nullable=False),
        sa.Column("source_record_type",  sa.String(100), nullable=True),
        sa.Column("source_record_id",    UUID(as_uuid=True), nullable=True),
        sa.Column("camp_metadata",       JSONB,          nullable=True),
        sa.Column("created_at",          sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_mcevent_type", "marketing_campaign_events", ["event_type"])


def downgrade() -> None:
    op.drop_table("marketing_campaign_events")
    op.drop_table("marketing_campaign_messages")
    op.drop_table("marketing_campaign_rules")
    op.drop_table("marketing_campaigns")
    op.drop_table("ai_action_logs")
