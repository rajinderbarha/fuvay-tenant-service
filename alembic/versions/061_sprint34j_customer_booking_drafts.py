"""Sprint 34J — Customer Booking Drafts: unified cross-flow draft table.

Revision ID: 061
Revises: 060
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "061"
down_revision = "060"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "customer_booking_drafts",
        sa.Column("id",               UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at",       sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at",       sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"), onupdate=sa.text("now()")),

        # Identity
        sa.Column("customer_id",      UUID(as_uuid=True), nullable=True),
        sa.Column("guest_session_id", sa.String(100), nullable=True),
        sa.Column("ai_session_id",    UUID(as_uuid=True), nullable=True),

        # Flow
        sa.Column("flow_type",        sa.String(50), nullable=False, server_default="service_booking"),

        # Catalog selections (validated against active catalog)
        sa.Column("category_id",      UUID(as_uuid=True), nullable=True),
        sa.Column("service_id",       UUID(as_uuid=True), nullable=True),
        sa.Column("brand_id",         UUID(as_uuid=True), nullable=True),
        sa.Column("issue_type_id",    UUID(as_uuid=True), nullable=True),
        sa.Column("service_option_ids", JSONB, nullable=True),   # list of UUID strings

        # Customer identity
        sa.Column("customer_name",    sa.String(150), nullable=True),
        sa.Column("customer_phone",   sa.String(30),  nullable=True),
        sa.Column("customer_email",   sa.String(200), nullable=True),

        # Location
        sa.Column("city",             sa.String(100), nullable=True),
        sa.Column("zipcode",          sa.String(20),  nullable=True),
        sa.Column("address_text",     sa.Text,        nullable=True),

        # Issue description
        sa.Column("issue_summary",    sa.Text,        nullable=True),
        sa.Column("issue_details",    JSONB,          nullable=True),

        # Scheduling (appointment_booking flow)
        sa.Column("preferred_date",   sa.Date,        nullable=True),
        sa.Column("preferred_time_slot", sa.String(50), nullable=True),

        # Lead capture
        sa.Column("lead_notes",       sa.Text,        nullable=True),
        sa.Column("lead_details",     JSONB,          nullable=True),

        # Estimate
        sa.Column("estimate_min",     sa.Numeric(12, 2), nullable=True),
        sa.Column("estimate_max",     sa.Numeric(12, 2), nullable=True),
        sa.Column("estimate_currency", sa.String(10), nullable=True, server_default="INR"),

        # Provider selection
        sa.Column("selected_tenant_id", UUID(as_uuid=True), nullable=True),

        # Status: draft → estimated → confirmed → cancelled
        sa.Column("status",           sa.String(50), nullable=False, server_default="draft"),

        # Final record references (set after confirmation)
        sa.Column("final_job_id",         UUID(as_uuid=True), nullable=True),
        sa.Column("final_appointment_id", UUID(as_uuid=True), nullable=True),
        sa.Column("final_lead_id",        UUID(as_uuid=True), nullable=True),

        # Extra
        sa.Column("extra_fields",     JSONB, nullable=True),
    )

    op.create_index("ix_cbd_customer_id",     "customer_booking_drafts", ["customer_id"])
    op.create_index("ix_cbd_ai_session_id",   "customer_booking_drafts", ["ai_session_id"])
    op.create_index("ix_cbd_status",          "customer_booking_drafts", ["status"])
    op.create_index("ix_cbd_flow_type",       "customer_booking_drafts", ["flow_type"])
    op.create_index("ix_cbd_category_service","customer_booking_drafts", ["category_id", "service_id"])


def downgrade() -> None:
    op.drop_index("ix_cbd_category_service", "customer_booking_drafts")
    op.drop_index("ix_cbd_flow_type",       "customer_booking_drafts")
    op.drop_index("ix_cbd_status",          "customer_booking_drafts")
    op.drop_index("ix_cbd_ai_session_id",   "customer_booking_drafts")
    op.drop_index("ix_cbd_customer_id",     "customer_booking_drafts")
    op.drop_table("customer_booking_drafts")
