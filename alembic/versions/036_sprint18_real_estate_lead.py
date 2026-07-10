"""Sprint 18 — Real Estate Chatbot Lead Flow.

Creates:
  real_estate_lead_drafts
  real_estate_lead_draft_events
  real_estate_lead_routing_rules
  real_estate_lead_scores

Revision: 036
Down: 035
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision   = "036"
down_revision = "035"
branch_labels = None
depends_on    = None


def upgrade() -> None:
    # ── real_estate_lead_drafts ───────────────────────────────────────────────
    op.create_table(
        "real_estate_lead_drafts",
        sa.Column("id",                      UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("customer_id",             UUID(as_uuid=True), nullable=True),
        sa.Column("guest_session_id",        sa.String(120),     nullable=True),
        sa.Column("ai_session_id",           UUID(as_uuid=True), nullable=True),
        sa.Column("category_id",             UUID(as_uuid=True), nullable=False),
        sa.Column("offering_id",             UUID(as_uuid=True), nullable=False),
        sa.Column("selected_tenant_id",      UUID(as_uuid=True), nullable=True),
        sa.Column("selected_agent_id",       UUID(as_uuid=True), nullable=True),
        # status
        sa.Column("status",                  sa.String(40),  nullable=False, server_default="draft"),
        # lead intent
        sa.Column("lead_intent",             sa.String(40),  nullable=True),
        # property details
        sa.Column("property_type",           sa.String(40),  nullable=True),
        sa.Column("city",                    sa.String(100), nullable=True),
        sa.Column("locality",                sa.String(150), nullable=True),
        sa.Column("zipcode",                 sa.String(20),  nullable=True),
        sa.Column("budget_min",              sa.Numeric(14, 2), nullable=True),
        sa.Column("budget_max",              sa.Numeric(14, 2), nullable=True),
        sa.Column("rent_min",                sa.Numeric(14, 2), nullable=True),
        sa.Column("rent_max",                sa.Numeric(14, 2), nullable=True),
        sa.Column("bedrooms",                sa.Integer,     nullable=True),
        sa.Column("bathrooms",               sa.Integer,     nullable=True),
        sa.Column("area_sqft_min",           sa.Integer,     nullable=True),
        sa.Column("area_sqft_max",           sa.Integer,     nullable=True),
        sa.Column("furnishing",              sa.String(40),  nullable=True),
        sa.Column("possession_preference",   sa.String(40),  nullable=True),
        # customer
        sa.Column("customer_name",           sa.String(200), nullable=True),
        sa.Column("customer_phone",          sa.String(30),  nullable=True),
        sa.Column("customer_email",          sa.String(255), nullable=True),
        sa.Column("preferred_contact_time",  sa.String(100), nullable=True),
        sa.Column("notes",                   sa.Text,        nullable=True),
        # snapshots
        sa.Column("requirement_snapshot",    JSONB,          nullable=True),
        sa.Column("provider_options",        JSONB,          nullable=True),
        sa.Column("selected_provider_snapshot", JSONB,       nullable=True),
        sa.Column("lead_score_snapshot",     JSONB,          nullable=True),
        sa.Column("lead_summary",            JSONB,          nullable=True),
        sa.Column("fallback_payload",        JSONB,          nullable=True),
        # failure
        sa.Column("failure_code",            sa.String(100), nullable=True),
        sa.Column("failure_message",         sa.Text,        nullable=True),
        sa.Column("expires_at",              sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at",              sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at",              sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), onupdate=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_reld_customer",    "real_estate_lead_drafts", ["customer_id"])
    op.create_index("ix_reld_status",      "real_estate_lead_drafts", ["status"])
    op.create_index("ix_reld_intent",      "real_estate_lead_drafts", ["lead_intent"])
    op.create_index("ix_reld_city",        "real_estate_lead_drafts", ["city"])
    op.create_index("ix_reld_ai_session",  "real_estate_lead_drafts", ["ai_session_id"])
    op.create_index("ix_reld_category",    "real_estate_lead_drafts", ["category_id"])

    # ── real_estate_lead_draft_events ─────────────────────────────────────────
    op.create_table(
        "real_estate_lead_draft_events",
        sa.Column("id",         UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("draft_id",   UUID(as_uuid=True), nullable=False),
        sa.Column("actor_type", sa.String(30),      nullable=False),
        sa.Column("event_type", sa.String(60),      nullable=False),
        sa.Column("old_value",  JSONB,              nullable=True),
        sa.Column("new_value",  JSONB,              nullable=True),
        sa.Column("message",    sa.Text,            nullable=True),
        sa.Column("request_id", sa.String(80),      nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_relde_draft",  "real_estate_lead_draft_events", ["draft_id"])
    op.create_index("ix_relde_event",  "real_estate_lead_draft_events", ["event_type"])

    # ── real_estate_lead_routing_rules ────────────────────────────────────────
    op.create_table(
        "real_estate_lead_routing_rules",
        sa.Column("id",                       UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("category_id",              UUID(as_uuid=True), nullable=False),
        sa.Column("rule_key",                 sa.String(100),     nullable=False),
        sa.Column("rule_name",                sa.String(200),     nullable=False),
        sa.Column("lead_intent",              sa.String(40),      nullable=True),
        sa.Column("match_scope",              sa.String(40),      nullable=False),
        sa.Column("priority",                 sa.Integer,         default=0,    nullable=False),
        sa.Column("require_agent_available",  sa.Boolean,         default=False, nullable=False),
        sa.Column("require_provider_bookable",sa.Boolean,         default=True,  nullable=False),
        sa.Column("require_subscription_active", sa.Boolean,      default=True,  nullable=False),
        sa.Column("require_lead_credit",      sa.Boolean,         default=False, nullable=False),
        sa.Column("max_providers",            sa.Integer,         default=5,     nullable=False),
        sa.Column("is_active",                sa.Boolean,         default=True,  nullable=False),
        sa.Column("created_at",               sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at",               sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), onupdate=sa.text("now()"), nullable=False),
    )
    op.create_unique_constraint(
        "uq_relrr_cat_key", "real_estate_lead_routing_rules", ["category_id", "rule_key"]
    )
    op.create_index("ix_relrr_category", "real_estate_lead_routing_rules", ["category_id"])
    op.create_index("ix_relrr_active",   "real_estate_lead_routing_rules", ["is_active"])

    # ── real_estate_lead_scores ────────────────────────────────────────────────
    op.create_table(
        "real_estate_lead_scores",
        sa.Column("id",             UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("draft_id",       UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("score",          sa.Integer,         nullable=False, default=0),
        sa.Column("score_label",    sa.String(20),      nullable=False),
        sa.Column("score_factors",  JSONB,              nullable=True),
        sa.Column("created_at",     sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at",     sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), onupdate=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_rels_draft", "real_estate_lead_scores", ["draft_id"])


def downgrade() -> None:
    op.drop_table("real_estate_lead_scores")
    op.drop_table("real_estate_lead_routing_rules")
    op.drop_table("real_estate_lead_draft_events")
    op.drop_table("real_estate_lead_drafts")
