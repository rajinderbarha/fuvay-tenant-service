"""Sprint 16 — Home Service Chatbot Booking Flow.

Creates 2 tables:
  - home_service_booking_drafts: pre-booking chatbot draft record
  - home_service_booking_draft_events: event log per draft

Note: customer_addresses already exists from serviceability engine (Phase 9).

Revision ID: 034
Revises: 033
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "034"
down_revision = "033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. home_service_booking_drafts ───────────────────────────────────────
    op.create_table(
        "home_service_booking_drafts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        # Customer / session linkage
        sa.Column("customer_id",      UUID(as_uuid=True), nullable=True),
        sa.Column("guest_session_id", sa.String(100),     nullable=True),
        sa.Column("ai_session_id",    UUID(as_uuid=True), nullable=True),
        # Catalog linkage
        sa.Column("category_id",  UUID(as_uuid=True), nullable=False),
        sa.Column("offering_id",  UUID(as_uuid=True), nullable=False),
        # Selected provider (set after provider matching)
        sa.Column("selected_tenant_id", UUID(as_uuid=True), nullable=True),
        # Lifecycle status
        sa.Column("status", sa.String(50), nullable=False,
                  server_default=sa.text("'draft'")),
        # Customer identity (collected via chat)
        sa.Column("customer_name",  sa.String(150), nullable=True),
        sa.Column("customer_phone", sa.String(30),  nullable=True),
        # Address
        sa.Column("address_id",       UUID(as_uuid=True), nullable=True),
        sa.Column("address_snapshot", JSONB,              nullable=True),
        sa.Column("city",    sa.String(100), nullable=True),
        sa.Column("zipcode", sa.String(20),  nullable=True),
        # Issue / problem description
        sa.Column("issue_summary", sa.Text, nullable=True),
        sa.Column("issue_details", JSONB,   nullable=True),
        # Offering variant fields
        sa.Column("offering_type_id", UUID(as_uuid=True), nullable=True),
        sa.Column("brand_id",         UUID(as_uuid=True), nullable=True),
        # Media
        sa.Column("photo_urls", JSONB, nullable=True),
        # Scheduling preference
        sa.Column("preferred_date",        sa.Date,        nullable=True),
        sa.Column("preferred_time_window", sa.String(50),  nullable=True),
        # Serviceability result
        sa.Column("serviceability_status", sa.String(30), nullable=True),   # pending|serviceable|not_serviceable
        # Price estimation result
        sa.Column("price_status",   sa.String(30), nullable=True),           # pending|estimated|failed
        # Provider matching result
        sa.Column("provider_match_status", sa.String(30), nullable=True),    # pending|matched|no_provider
        # Price resolution details
        sa.Column("pricing_rule_id",        UUID(as_uuid=True), nullable=True),
        sa.Column("provider_override_id",   UUID(as_uuid=True), nullable=True),
        sa.Column("price_snapshot",         JSONB, nullable=True),
        # Provider matching results
        sa.Column("provider_options",             JSONB, nullable=True),
        sa.Column("selected_provider_snapshot",   JSONB, nullable=True),
        # Booking summary for customer display
        sa.Column("booking_summary", JSONB, nullable=True),
        # Failure tracking
        sa.Column("failure_code",    sa.String(100), nullable=True),
        sa.Column("failure_message", sa.Text,        nullable=True),
        # Expiry
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_hsbd_customer_id",       "home_service_booking_drafts", ["customer_id"])
    op.create_index("ix_hsbd_ai_session_id",     "home_service_booking_drafts", ["ai_session_id"])
    op.create_index("ix_hsbd_status",            "home_service_booking_drafts", ["status"])
    op.create_index("ix_hsbd_offering_id",       "home_service_booking_drafts", ["offering_id"])
    op.create_index("ix_hsbd_category_offering", "home_service_booking_drafts", ["category_id", "offering_id"])
    op.create_index("ix_hsbd_city_zipcode",      "home_service_booking_drafts", ["city", "zipcode"])
    op.create_index("ix_hsbd_selected_tenant",   "home_service_booking_drafts", ["selected_tenant_id"])

    # ── 2. home_service_booking_draft_events ─────────────────────────────────
    op.create_table(
        "home_service_booking_draft_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("draft_id",   UUID(as_uuid=True), nullable=False),
        sa.Column("actor_type", sa.String(30),      nullable=False),   # customer|ai|backend|system
        sa.Column("event_type", sa.String(60),      nullable=False),
        sa.Column("old_value",  JSONB, nullable=True),
        sa.Column("new_value",  JSONB, nullable=True),
        sa.Column("message",    sa.Text, nullable=True),
        sa.Column("request_id", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_hsbde_draft_id",   "home_service_booking_draft_events", ["draft_id"])
    op.create_index("ix_hsbde_event_type", "home_service_booking_draft_events", ["event_type"])
    op.create_index("ix_hsbde_created_at", "home_service_booking_draft_events", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_hsbde_created_at",  table_name="home_service_booking_draft_events")
    op.drop_index("ix_hsbde_event_type",  table_name="home_service_booking_draft_events")
    op.drop_index("ix_hsbde_draft_id",    table_name="home_service_booking_draft_events")
    op.drop_table("home_service_booking_draft_events")

    op.drop_index("ix_hsbd_selected_tenant",   table_name="home_service_booking_drafts")
    op.drop_index("ix_hsbd_city_zipcode",      table_name="home_service_booking_drafts")
    op.drop_index("ix_hsbd_category_offering", table_name="home_service_booking_drafts")
    op.drop_index("ix_hsbd_offering_id",       table_name="home_service_booking_drafts")
    op.drop_index("ix_hsbd_status",            table_name="home_service_booking_drafts")
    op.drop_index("ix_hsbd_ai_session_id",     table_name="home_service_booking_drafts")
    op.drop_index("ix_hsbd_customer_id",       table_name="home_service_booking_drafts")
    op.drop_table("home_service_booking_drafts")
