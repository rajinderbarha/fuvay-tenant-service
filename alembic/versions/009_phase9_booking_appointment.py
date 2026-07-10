"""Phase 9 — Booking + Appointment (8 tables)
Revision ID: 009
Revises: 008
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Booking (4 tables) ────────────────────────────────────────────────────
    op.create_table("bookings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", UUID(as_uuid=True), nullable=False),
        sa.Column("service_type_id", sa.String(100), nullable=False),
        sa.Column("service_category", sa.String(100), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="draft"),
        sa.Column("booking_number", sa.String(30), nullable=False, unique=True),
        sa.Column("quoted_price", sa.Numeric(10,2), nullable=True),
        sa.Column("price_snapshot_id", UUID(as_uuid=True), nullable=True),
        sa.Column("preferred_date", sa.String(10), nullable=True),
        sa.Column("preferred_slot", sa.String(30), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("address", JSONB, nullable=False, server_default="{}"),
        sa.Column("pincode", sa.String(20), nullable=True),
        sa.Column("preflight_passed", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("preflight_result", JSONB, nullable=False, server_default="{}"),
        sa.Column("blocking_reason", sa.String(500), nullable=True),
        sa.Column("job_id", UUID(as_uuid=True), nullable=True),
        sa.Column("converted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancellation_reason", sa.String(500), nullable=True),
        sa.Column("cancellation_policy", sa.String(20), nullable=False, server_default="standard"),
        sa.Column("within_cancel_window", sa.Boolean, nullable=True),
        sa.Column("reschedule_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("idempotency_key", sa.String(64), nullable=True, unique=True),
        sa.Column("reservation_id", UUID(as_uuid=True), nullable=True),
        sa.Column("customer_notes", sa.Text, nullable=True),
        sa.Column("internal_notes", sa.Text, nullable=True),
        sa.Column("tags", JSONB, nullable=False, server_default="[]"),
        sa.Column("meta", JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_bk_tenant_status", "bookings", ["tenant_id","status"])
    op.create_index("ix_bk_customer", "bookings", ["customer_id"])
    op.create_index("ix_bk_idem_key", "bookings", ["idempotency_key"])

    op.create_table("booking_status_history",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("booking_id", UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("from_status", sa.String(30), nullable=True),
        sa.Column("to_status", sa.String(30), nullable=False),
        sa.Column("changed_by", UUID(as_uuid=True), nullable=True),
        sa.Column("changed_by_role", sa.String(30), nullable=True),
        sa.Column("reason", sa.String(500), nullable=True),
        sa.Column("meta", JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_bsh_booking_id", "booking_status_history", ["booking_id"])

    op.create_table("booking_notes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("booking_id", UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("author_id", UUID(as_uuid=True), nullable=True),
        sa.Column("author_role", sa.String(30), nullable=True),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("is_internal", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_bn_booking_id", "booking_notes", ["booking_id"])

    op.create_table("booking_reschedule_requests",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("booking_id", UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("requested_by", UUID(as_uuid=True), nullable=True),
        sa.Column("original_slot", sa.String(50), nullable=True),
        sa.Column("requested_slot", sa.String(50), nullable=True),
        sa.Column("requested_date", sa.String(10), nullable=True),
        sa.Column("reason", sa.String(500), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_brr_booking_id", "booking_reschedule_requests", ["booking_id"])

    # ── Appointment (4 tables) ────────────────────────────────────────────────
    op.create_table("appointments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("staff_id", UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", UUID(as_uuid=True), nullable=False),
        sa.Column("booking_id", UUID(as_uuid=True), nullable=True),
        sa.Column("service_type_id", sa.String(100), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="hold"),
        sa.Column("appointment_number", sa.String(30), nullable=False, unique=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_minutes", sa.Integer, nullable=False, server_default="60"),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("hold_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancellation_reason", sa.String(500), nullable=True),
        sa.Column("no_show_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reminder_24h_sent", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("reminder_2h_sent", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("customer_notes", sa.Text, nullable=True),
        sa.Column("meta", JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        # DB-level double-booking prevention
        sa.UniqueConstraint("staff_id","scheduled_at","tenant_id", name="uq_appt_staff_slot"),
    )
    op.create_index("ix_appt_tenant_status", "appointments", ["tenant_id","status"])
    op.create_index("ix_appt_staff", "appointments", ["staff_id"])
    op.create_index("ix_appt_customer", "appointments", ["customer_id"])
    op.create_index("ix_appt_scheduled", "appointments", ["scheduled_at"])

    op.create_table("appointment_status_history",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("appointment_id", UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("from_status", sa.String(20), nullable=True),
        sa.Column("to_status", sa.String(20), nullable=False),
        sa.Column("changed_by", UUID(as_uuid=True), nullable=True),
        sa.Column("changed_by_role", sa.String(30), nullable=True),
        sa.Column("reason", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_ash_appt_id", "appointment_status_history", ["appointment_id"])

    op.create_table("staff_calendar_blocks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("staff_id", UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("block_date", sa.String(10), nullable=False),
        sa.Column("start_time", sa.String(8), nullable=False),
        sa.Column("end_time", sa.String(8), nullable=False),
        sa.Column("block_type", sa.String(30), nullable=False, server_default="leave"),
        sa.Column("reason", sa.String(255), nullable=True),
        sa.Column("is_full_day", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_by", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_scb_staff_date", "staff_calendar_blocks", ["staff_id","block_date"])
    op.create_index("ix_scb_tenant", "staff_calendar_blocks", ["tenant_id"])

    op.create_table("staff_working_hours",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("staff_id", UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("day_of_week", sa.Integer, nullable=False),
        sa.Column("start_time", sa.String(8), nullable=False),
        sa.Column("end_time", sa.String(8), nullable=False),
        sa.Column("slot_duration", sa.Integer, nullable=False, server_default="60"),
        sa.Column("buffer_minutes", sa.Integer, nullable=False, server_default="15"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("staff_id","tenant_id","day_of_week", name="uq_swh_staff_day"),
    )
    op.create_index("ix_swh_staff", "staff_working_hours", ["staff_id"])


def downgrade() -> None:
    for t in ["staff_working_hours","staff_calendar_blocks","appointment_status_history",
              "appointments","booking_reschedule_requests","booking_notes",
              "booking_status_history","bookings"]:
        op.drop_table(t)
