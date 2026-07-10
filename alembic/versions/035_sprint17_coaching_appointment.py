"""Sprint 17 — Coaching / IELTS Chatbot Appointment Flow.

3 new tables:
- coaching_appointment_drafts
- coaching_appointment_draft_events
- coaching_appointment_slot_holds

Revision ID: 035
Revises: 034
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "035"
down_revision = "034"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── coaching_appointment_drafts ───────────────────────────────────────────
    op.create_table(
        "coaching_appointment_drafts",
        sa.Column("id",                          postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("customer_id",                 postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("guest_session_id",            sa.String(200), nullable=True),
        sa.Column("ai_session_id",               postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("category_id",                 postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("offering_id",                 postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("selected_tenant_id",          postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("selected_staff_member_id",    postgresql.UUID(as_uuid=True), nullable=True),
        # Draft lifecycle
        sa.Column("status",                      sa.String(40), nullable=False, server_default="draft"),
        # Student details
        sa.Column("student_name",                sa.String(200), nullable=True),
        sa.Column("student_phone",               sa.String(30), nullable=True),
        sa.Column("student_email",               sa.String(255), nullable=True),
        sa.Column("student_age",                 sa.Integer(), nullable=True),
        sa.Column("current_education",           sa.String(200), nullable=True),
        sa.Column("target_exam",                 sa.String(100), nullable=True),
        sa.Column("target_band",                 sa.String(20), nullable=True),
        # Appointment preferences
        sa.Column("preferred_mode",              sa.String(20), nullable=True),
        sa.Column("city",                        sa.String(100), nullable=True),
        sa.Column("zipcode",                     sa.String(20), nullable=True),
        sa.Column("selected_date",               sa.Date(), nullable=True),
        sa.Column("selected_time_start",         sa.Time(), nullable=True),
        sa.Column("selected_time_end",           sa.Time(), nullable=True),
        # Snapshots (JSONB)
        sa.Column("slot_snapshot",               postgresql.JSONB(), nullable=True),
        sa.Column("center_location_snapshot",    postgresql.JSONB(), nullable=True),
        sa.Column("appointment_fee_snapshot",    postgresql.JSONB(), nullable=True),
        sa.Column("provider_options",            postgresql.JSONB(), nullable=True),
        sa.Column("next_available_slots",        postgresql.JSONB(), nullable=True),
        sa.Column("recommended_slot_snapshot",   postgresql.JSONB(), nullable=True),
        sa.Column("selected_provider_snapshot",  postgresql.JSONB(), nullable=True),
        sa.Column("fallback_inquiry_payload",    postgresql.JSONB(), nullable=True),
        sa.Column("appointment_summary",         postgresql.JSONB(), nullable=True),
        # Sub-statuses
        sa.Column("location_status",             sa.String(30), nullable=True, server_default="pending"),
        sa.Column("slot_status",                 sa.String(30), nullable=True, server_default="pending"),
        sa.Column("fee_status",                  sa.String(30), nullable=True, server_default="pending"),
        # Failure info
        sa.Column("failure_code",                sa.String(100), nullable=True),
        sa.Column("failure_message",             sa.Text(), nullable=True),
        sa.Column("notes",                       sa.Text(), nullable=True),
        # Timestamps
        sa.Column("expires_at",                  sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at",                  sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at",                  sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"), onupdate=sa.text("now()")),
    )
    op.create_index("ix_cad_customer", "coaching_appointment_drafts", ["customer_id"])
    op.create_index("ix_cad_status",   "coaching_appointment_drafts", ["status"])
    op.create_index("ix_cad_offering", "coaching_appointment_drafts", ["offering_id"])
    op.create_index("ix_cad_city",     "coaching_appointment_drafts", ["city"])

    # ── coaching_appointment_draft_events ─────────────────────────────────────
    op.create_table(
        "coaching_appointment_draft_events",
        sa.Column("id",         postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("draft_id",   postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_type", sa.String(30), nullable=False),
        sa.Column("event_type", sa.String(60), nullable=False),
        sa.Column("old_value",  postgresql.JSONB(), nullable=True),
        sa.Column("new_value",  postgresql.JSONB(), nullable=True),
        sa.Column("message",    sa.Text(), nullable=True),
        sa.Column("request_id", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_cade_draft", "coaching_appointment_draft_events", ["draft_id"])

    # ── coaching_appointment_slot_holds ───────────────────────────────────────
    op.create_table(
        "coaching_appointment_slot_holds",
        sa.Column("id",               postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("draft_id",         postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id",        postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("staff_member_id",  postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("offering_id",      postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("slot_date",        sa.Date(), nullable=False),
        sa.Column("start_time",       sa.Time(), nullable=False),
        sa.Column("end_time",         sa.Time(), nullable=False),
        sa.Column("hold_status",      sa.String(20), nullable=False, server_default="held"),
        sa.Column("expires_at",       sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at",       sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at",       sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"), onupdate=sa.text("now()")),
    )
    op.create_index("ix_cash_draft",   "coaching_appointment_slot_holds", ["draft_id"])
    op.create_index("ix_cash_tenant",  "coaching_appointment_slot_holds", ["tenant_id"])
    op.create_index("ix_cash_slot",    "coaching_appointment_slot_holds", ["slot_date", "start_time", "tenant_id"])
    op.create_index("ix_cash_status",  "coaching_appointment_slot_holds", ["hold_status"])


def downgrade() -> None:
    op.drop_table("coaching_appointment_slot_holds")
    op.drop_table("coaching_appointment_draft_events")
    op.drop_table("coaching_appointment_drafts")
