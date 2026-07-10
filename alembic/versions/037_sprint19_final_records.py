"""Sprint 19 — Booking Confirmation → Final Record Creation.

Creates:
  service_bookings
  service_jobs
  coaching_appointments
  real_estate_leads
  customer_booking_confirmations
  final_creation_audit_logs

Revision: 037
Down: 036
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision      = "037"
down_revision = "036"
branch_labels = None
depends_on    = None


def upgrade() -> None:
    # ── service_bookings ──────────────────────────────────────────────────────
    op.create_table(
        "service_bookings",
        sa.Column("id",                     UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("booking_number",         sa.String(30),  nullable=False),
        sa.Column("draft_id",               UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id",            UUID(as_uuid=True), nullable=True),
        sa.Column("tenant_id",              UUID(as_uuid=True), nullable=True),
        sa.Column("category_id",            UUID(as_uuid=True), nullable=False),
        sa.Column("offering_id",            UUID(as_uuid=True), nullable=False),
        sa.Column("ai_session_id",          UUID(as_uuid=True), nullable=True),
        # customer snapshot
        sa.Column("customer_name",          sa.String(200), nullable=True),
        sa.Column("customer_phone",         sa.String(30),  nullable=True),
        sa.Column("city",                   sa.String(100), nullable=True),
        sa.Column("zipcode",                sa.String(20),  nullable=True),
        sa.Column("address_snapshot",       JSONB,          nullable=True),
        # scheduling
        sa.Column("preferred_date",         sa.Date(),      nullable=True),
        sa.Column("preferred_time_window",  sa.String(50),  nullable=True),
        # pricing
        sa.Column("price_snapshot",         JSONB,          nullable=True),
        # provider
        sa.Column("provider_snapshot",      JSONB,          nullable=True),
        # issue
        sa.Column("issue_summary",          sa.Text(),      nullable=True),
        sa.Column("issue_details",          JSONB,          nullable=True),
        # status: pending_assignment → assigned → in_progress → completed | cancelled
        sa.Column("status",                 sa.String(40),  nullable=False, server_default="pending_assignment"),
        sa.Column("failure_reason",         sa.Text(),      nullable=True),
        # timestamps
        sa.Column("created_at",             sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at",             sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_sb_booking_number", "service_bookings", ["booking_number"], unique=True)
    op.create_index("ix_sb_draft_id",       "service_bookings", ["draft_id"], unique=True)
    op.create_index("ix_sb_customer_id",    "service_bookings", ["customer_id"])
    op.create_index("ix_sb_tenant_id",      "service_bookings", ["tenant_id"])
    op.create_index("ix_sb_status",         "service_bookings", ["status"])

    # ── service_jobs ──────────────────────────────────────────────────────────
    op.create_table(
        "service_jobs",
        sa.Column("id",                     UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("job_number",             sa.String(30),  nullable=False),
        sa.Column("booking_id",             UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id",            UUID(as_uuid=True), nullable=True),
        sa.Column("tenant_id",              UUID(as_uuid=True), nullable=True),
        sa.Column("category_id",            UUID(as_uuid=True), nullable=False),
        sa.Column("offering_id",            UUID(as_uuid=True), nullable=False),
        # assigned technician — Sprint 20+
        sa.Column("assigned_staff_id",      UUID(as_uuid=True), nullable=True),
        # schedule
        sa.Column("scheduled_date",         sa.Date(),      nullable=True),
        sa.Column("scheduled_time_window",  sa.String(50),  nullable=True),
        sa.Column("city",                   sa.String(100), nullable=True),
        sa.Column("zipcode",                sa.String(20),  nullable=True),
        sa.Column("address_snapshot",       JSONB,          nullable=True),
        # status: pending_assignment → assigned → dispatched → in_progress → completed | cancelled
        sa.Column("status",                 sa.String(40),  nullable=False, server_default="pending_assignment"),
        sa.Column("failure_reason",         sa.Text(),      nullable=True),
        # timestamps
        sa.Column("created_at",             sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at",             sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_sj_job_number",  "service_jobs", ["job_number"], unique=True)
    op.create_index("ix_sj_booking_id",  "service_jobs", ["booking_id"])
    op.create_index("ix_sj_customer_id", "service_jobs", ["customer_id"])
    op.create_index("ix_sj_tenant_id",   "service_jobs", ["tenant_id"])
    op.create_index("ix_sj_status",      "service_jobs", ["status"])

    # ── coaching_appointments ─────────────────────────────────────────────────
    op.create_table(
        "coaching_appointments",
        sa.Column("id",                     UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("appointment_number",     sa.String(30),  nullable=False),
        sa.Column("draft_id",               UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id",            UUID(as_uuid=True), nullable=True),
        sa.Column("tenant_id",              UUID(as_uuid=True), nullable=True),
        sa.Column("category_id",            UUID(as_uuid=True), nullable=False),
        sa.Column("offering_id",            UUID(as_uuid=True), nullable=False),
        sa.Column("ai_session_id",          UUID(as_uuid=True), nullable=True),
        # staff
        sa.Column("staff_member_id",        UUID(as_uuid=True), nullable=True),
        # student details
        sa.Column("student_name",           sa.String(200), nullable=True),
        sa.Column("student_phone",          sa.String(30),  nullable=True),
        sa.Column("student_email",          sa.String(255), nullable=True),
        sa.Column("target_exam",            sa.String(100), nullable=True),
        sa.Column("target_band",            sa.String(20),  nullable=True),
        # scheduling
        sa.Column("preferred_mode",         sa.String(20),  nullable=True),
        sa.Column("selected_date",          sa.Date(),      nullable=True),
        sa.Column("selected_time_start",    sa.Time(),      nullable=True),
        sa.Column("selected_time_end",      sa.Time(),      nullable=True),
        sa.Column("city",                   sa.String(100), nullable=True),
        # fee
        sa.Column("appointment_fee_snapshot", JSONB,        nullable=True),
        # provider
        sa.Column("provider_snapshot",      JSONB,          nullable=True),
        # status: confirmed → completed | cancelled | no_show
        sa.Column("status",                 sa.String(40),  nullable=False, server_default="confirmed"),
        sa.Column("failure_reason",         sa.Text(),      nullable=True),
        # timestamps
        sa.Column("created_at",             sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at",             sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_ca_appointment_number", "coaching_appointments", ["appointment_number"], unique=True)
    op.create_index("ix_ca_draft_id",           "coaching_appointments", ["draft_id"], unique=True)
    op.create_index("ix_ca_customer_id",        "coaching_appointments", ["customer_id"])
    op.create_index("ix_ca_tenant_id",          "coaching_appointments", ["tenant_id"])
    op.create_index("ix_ca_status",             "coaching_appointments", ["status"])

    # ── real_estate_leads ─────────────────────────────────────────────────────
    op.create_table(
        "real_estate_leads",
        sa.Column("id",                     UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("lead_number",            sa.String(30),  nullable=False),
        sa.Column("draft_id",               UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id",            UUID(as_uuid=True), nullable=True),
        sa.Column("tenant_id",              UUID(as_uuid=True), nullable=True),
        sa.Column("agent_id",               UUID(as_uuid=True), nullable=True),
        sa.Column("category_id",            UUID(as_uuid=True), nullable=False),
        sa.Column("offering_id",            UUID(as_uuid=True), nullable=False),
        sa.Column("ai_session_id",          UUID(as_uuid=True), nullable=True),
        # intent + property
        sa.Column("lead_intent",            sa.String(40),  nullable=True),
        sa.Column("property_type",          sa.String(40),  nullable=True),
        # location
        sa.Column("city",                   sa.String(100), nullable=True),
        sa.Column("locality",               sa.String(150), nullable=True),
        sa.Column("zipcode",                sa.String(20),  nullable=True),
        # budget
        sa.Column("budget_min",             sa.Numeric(14, 2), nullable=True),
        sa.Column("budget_max",             sa.Numeric(14, 2), nullable=True),
        sa.Column("rent_min",               sa.Numeric(14, 2), nullable=True),
        sa.Column("rent_max",               sa.Numeric(14, 2), nullable=True),
        # snapshots
        sa.Column("customer_snapshot",      JSONB,          nullable=True),
        sa.Column("requirement_snapshot",   JSONB,          nullable=True),
        sa.Column("lead_score_snapshot",    JSONB,          nullable=True),
        sa.Column("provider_snapshot",      JSONB,          nullable=True),
        sa.Column("fallback_payload",       JSONB,          nullable=True),
        # status: new → contacted → qualified → converted | rejected
        sa.Column("status",                 sa.String(40),  nullable=False, server_default="new"),
        sa.Column("failure_reason",         sa.Text(),      nullable=True),
        # timestamps
        sa.Column("created_at",             sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at",             sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_rel_lead_number",  "real_estate_leads", ["lead_number"], unique=True)
    op.create_index("ix_rel_draft_id",     "real_estate_leads", ["draft_id"], unique=True)
    op.create_index("ix_rel_customer_id",  "real_estate_leads", ["customer_id"])
    op.create_index("ix_rel_tenant_id",    "real_estate_leads", ["tenant_id"])
    op.create_index("ix_rel_status",       "real_estate_leads", ["status"])
    op.create_index("ix_rel_city_intent",  "real_estate_leads", ["city", "lead_intent"])

    # ── customer_booking_confirmations ────────────────────────────────────────
    op.create_table(
        "customer_booking_confirmations",
        sa.Column("id",                     UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("customer_id",            UUID(as_uuid=True), nullable=True),
        # draft_type: home_service | coaching | real_estate
        sa.Column("draft_type",             sa.String(30),  nullable=False),
        sa.Column("draft_id",               UUID(as_uuid=True), nullable=False),
        sa.Column("idempotency_key",        sa.String(200), nullable=True),
        # result
        # result_type: service_booking | coaching_appointment | real_estate_lead
        sa.Column("result_type",            sa.String(40),  nullable=True),
        sa.Column("result_id",              UUID(as_uuid=True), nullable=True),
        sa.Column("result_number",          sa.String(30),  nullable=True),
        # status: created | failed
        sa.Column("status",                 sa.String(20),  nullable=False, server_default="created"),
        sa.Column("failure_reason",         sa.Text(),      nullable=True),
        sa.Column("created_at",             sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    # Core idempotency constraint: one final record per draft
    op.create_unique_constraint(
        "uq_cbc_draft_type_draft_id",
        "customer_booking_confirmations",
        ["draft_type", "draft_id"],
    )
    op.create_index("ix_cbc_customer_id",      "customer_booking_confirmations", ["customer_id"])
    op.create_index("ix_cbc_idempotency_key",  "customer_booking_confirmations", ["idempotency_key"])
    op.create_index("ix_cbc_draft_id",         "customer_booking_confirmations", ["draft_id"])

    # ── final_creation_audit_logs ─────────────────────────────────────────────
    op.create_table(
        "final_creation_audit_logs",
        sa.Column("id",                     UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        # action: booking_created | appointment_created | lead_created
        #         | confirmation_duplicate | confirmation_failed
        sa.Column("action",                 sa.String(60),  nullable=False),
        sa.Column("draft_type",             sa.String(30),  nullable=True),
        sa.Column("draft_id",               UUID(as_uuid=True), nullable=True),
        sa.Column("result_type",            sa.String(40),  nullable=True),
        sa.Column("result_id",              UUID(as_uuid=True), nullable=True),
        sa.Column("result_number",          sa.String(30),  nullable=True),
        sa.Column("customer_id",            UUID(as_uuid=True), nullable=True),
        sa.Column("tenant_id",              UUID(as_uuid=True), nullable=True),
        sa.Column("request_id",             sa.String(100), nullable=True),
        sa.Column("details",                JSONB,          nullable=True),
        sa.Column("created_at",             sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_fcal_draft_id",    "final_creation_audit_logs", ["draft_id"])
    op.create_index("ix_fcal_customer_id", "final_creation_audit_logs", ["customer_id"])
    op.create_index("ix_fcal_action",      "final_creation_audit_logs", ["action"])
    op.create_index("ix_fcal_created_at",  "final_creation_audit_logs", ["created_at"])


def downgrade() -> None:
    op.drop_table("final_creation_audit_logs")
    op.drop_table("customer_booking_confirmations")
    op.drop_table("real_estate_leads")
    op.drop_table("coaching_appointments")
    op.drop_table("service_jobs")
    op.drop_table("service_bookings")
