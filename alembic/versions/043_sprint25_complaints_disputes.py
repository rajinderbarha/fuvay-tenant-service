"""Sprint 25 — Complaints / Disputes / Refund / Rework

Revision ID: 043
Revises: 042
Create Date: 2026-07-02
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "043"
down_revision = "042"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. customer_complaints ─────────────────────────────────────────────────
    op.create_table(
        "customer_complaints",
        sa.Column("id",                           postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("complaint_number",             sa.String(40),  nullable=False),
        sa.Column("customer_id",                  postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id",                    postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("category_id",                  postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("offering_id",                  postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("record_type",                  sa.String(40),  nullable=False),
        sa.Column("record_id",                    postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("booking_id",                   postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("job_id",                       postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("invoice_id",                   postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("appointment_id",               postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("lead_id",                      postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("review_id",                    postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("assigned_admin_user_id",       postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("complaint_type",               sa.String(40),  nullable=False),
        sa.Column("requested_resolution",         sa.String(40),  nullable=True),
        sa.Column("priority",                     sa.String(20),  nullable=False, server_default="normal"),
        sa.Column("status",                       sa.String(40),  nullable=False, server_default="open"),
        sa.Column("title",                        sa.String(300), nullable=True),
        sa.Column("description",                  sa.Text(),      nullable=False),
        sa.Column("customer_visible_summary",     sa.Text(),      nullable=True),
        sa.Column("internal_admin_notes",         sa.Text(),      nullable=True),
        sa.Column("provider_response_required",   sa.Boolean(),   nullable=False, server_default="true"),
        sa.Column("provider_responded_at",        sa.DateTime(timezone=True), nullable=True),
        sa.Column("customer_accepted_resolution_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at",                  sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at",                    sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at",                   sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at",                   sa.DateTime(timezone=True), nullable=True),
    )
    op.create_unique_constraint("uq_cc_number", "customer_complaints", ["complaint_number"])
    op.create_index("ix_cc_customer_id",   "customer_complaints", ["customer_id"])
    op.create_index("ix_cc_tenant_id",     "customer_complaints", ["tenant_id"])
    op.create_index("ix_cc_status",        "customer_complaints", ["status"])
    op.create_index("ix_cc_record",        "customer_complaints", ["record_type", "record_id"])
    op.create_index("ix_cc_priority",      "customer_complaints", ["priority"])

    # ── 2. complaint_messages ─────────────────────────────────────────────────
    op.create_table(
        "complaint_messages",
        sa.Column("id",              postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("complaint_id",    postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id",       postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("sender_type",     sa.String(20), nullable=False),
        sa.Column("sender_user_id",  postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("message_text",    sa.Text(),     nullable=False),
        sa.Column("visibility",      sa.String(30), nullable=False, server_default="public_to_case"),
        sa.Column("created_at",      sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at",      sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_cm_complaint_id", "complaint_messages", ["complaint_id"])
    op.create_index("ix_cm_sender_type",  "complaint_messages", ["sender_type"])

    # ── 3. complaint_media ────────────────────────────────────────────────────
    op.create_table(
        "complaint_media",
        sa.Column("id",                  postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("complaint_id",        postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("uploaded_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("uploaded_by_type",    sa.String(20), nullable=False),
        sa.Column("media_type",          sa.String(20), nullable=False),
        sa.Column("file_url",            sa.String(500), nullable=False),
        sa.Column("file_name",           sa.String(300), nullable=True),
        sa.Column("mime_type",           sa.String(100), nullable=True),
        sa.Column("file_size",           sa.Integer(),   nullable=True),
        sa.Column("caption",             sa.Text(),      nullable=True),
        sa.Column("visibility",          sa.String(30),  nullable=False, server_default="public_to_case"),
        sa.Column("created_at",          sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_cmed_complaint_id", "complaint_media", ["complaint_id"])

    # ── 4. complaint_events ───────────────────────────────────────────────────
    op.create_table(
        "complaint_events",
        sa.Column("id",            postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("complaint_id",  postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id",     postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_type",    sa.String(20),  nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type",    sa.String(60),  nullable=False),
        sa.Column("old_status",    sa.String(40),  nullable=True),
        sa.Column("new_status",    sa.String(40),  nullable=True),
        sa.Column("old_value",     postgresql.JSONB(), nullable=True),
        sa.Column("new_value",     postgresql.JSONB(), nullable=True),
        sa.Column("reason",        sa.Text(),      nullable=True),
        sa.Column("request_id",    sa.String(100), nullable=True),
        sa.Column("created_at",    sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_ce_complaint_id", "complaint_events", ["complaint_id"])
    op.create_index("ix_ce_event_type",   "complaint_events", ["event_type"])
    op.create_index("ix_ce_tenant_id",    "complaint_events", ["tenant_id"])

    # ── 5. complaint_resolutions ──────────────────────────────────────────────
    op.create_table(
        "complaint_resolutions",
        sa.Column("id",                     postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("complaint_id",           postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id",              postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("resolution_type",        sa.String(40), nullable=False),
        sa.Column("status",                 sa.String(30), nullable=False, server_default="proposed"),
        sa.Column("proposed_by_type",       sa.String(20), nullable=False),
        sa.Column("proposed_by_user_id",    postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("description",            sa.Text(),     nullable=False),
        sa.Column("customer_visible_notes", sa.Text(),     nullable=True),
        sa.Column("internal_notes",         sa.Text(),     nullable=True),
        sa.Column("due_date",               sa.Date(),     nullable=True),
        sa.Column("created_at",             sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at",             sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_compres_complaint_id", "complaint_resolutions", ["complaint_id"])
    op.create_index("ix_compres_status",       "complaint_resolutions", ["status"])

    # ── 6. service_rework_requests ────────────────────────────────────────────
    op.create_table(
        "service_rework_requests",
        sa.Column("id",                      postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("rework_number",           sa.String(40),  nullable=False),
        sa.Column("complaint_id",            postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("booking_id",              postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("job_id",                  postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tenant_id",               postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id",             postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("original_job_id",         postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("assigned_staff_member_id",postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status",                  sa.String(30),  nullable=False, server_default="requested"),
        sa.Column("rework_reason",           sa.Text(),      nullable=False),
        sa.Column("admin_notes",             sa.Text(),      nullable=True),
        sa.Column("customer_visible_notes",  sa.Text(),      nullable=True),
        sa.Column("scheduled_date",          sa.Date(),      nullable=True),
        sa.Column("scheduled_time_window",   sa.String(80),  nullable=True),
        sa.Column("completed_at",            sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at",              sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at",              sa.DateTime(timezone=True), nullable=True),
    )
    op.create_unique_constraint("uq_srr_number", "service_rework_requests", ["rework_number"])
    op.create_index("ix_srr_complaint_id", "service_rework_requests", ["complaint_id"])
    op.create_index("ix_srr_tenant_id",    "service_rework_requests", ["tenant_id"])
    op.create_index("ix_srr_status",       "service_rework_requests", ["status"])

    # ── 7. refund_requests ────────────────────────────────────────────────────
    op.create_table(
        "refund_requests",
        sa.Column("id",                  postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("refund_number",       sa.String(40),  nullable=False),
        sa.Column("complaint_id",        postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id",         postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id",           postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("invoice_id",          postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("booking_id",          postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("job_id",              postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("appointment_id",      postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("lead_id",             postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status",              sa.String(30),  nullable=False, server_default="requested"),
        sa.Column("refund_type",         sa.String(40),  nullable=False),
        sa.Column("requested_amount",    sa.Numeric(12,2), nullable=True),
        sa.Column("approved_amount",     sa.Numeric(12,2), nullable=True),
        sa.Column("recorded_amount",     sa.Numeric(12,2), nullable=True),
        sa.Column("currency",            sa.String(10),  nullable=False, server_default="INR"),
        sa.Column("refund_method",       sa.String(40),  nullable=True),
        sa.Column("reason",              sa.Text(),      nullable=False),
        sa.Column("rejection_reason",    sa.Text(),      nullable=True),
        sa.Column("proof_media_url",     sa.String(500), nullable=True),
        sa.Column("approved_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("recorded_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("verified_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("approved_at",         sa.DateTime(timezone=True), nullable=True),
        sa.Column("recorded_at",         sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_at",         sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at",          sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at",          sa.DateTime(timezone=True), nullable=True),
    )
    op.create_unique_constraint("uq_rr_number", "refund_requests", ["refund_number"])
    op.create_index("ix_rfndreq_complaint_id", "refund_requests", ["complaint_id"])
    op.create_index("ix_rfndreq_customer_id",  "refund_requests", ["customer_id"])
    op.create_index("ix_rfndreq_status",       "refund_requests", ["status"])

    # ── 8. complaint_policies ─────────────────────────────────────────────────
    op.create_table(
        "complaint_policies",
        sa.Column("id",                           postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("category_id",                  postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tenant_id",                    postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("policy_key",                   sa.String(80),  nullable=False),
        sa.Column("policy_name",                  sa.String(200), nullable=False),
        sa.Column("allow_customer_complaints",    sa.Boolean(),   nullable=False, server_default="true"),
        sa.Column("complaint_window_hours",       sa.Integer(),   nullable=False, server_default="168"),
        sa.Column("allow_duplicate_open_complaints", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("allow_rework",                 sa.Boolean(),   nullable=False, server_default="true"),
        sa.Column("allow_refund_request",         sa.Boolean(),   nullable=False, server_default="true"),
        sa.Column("require_admin_review",         sa.Boolean(),   nullable=False, server_default="true"),
        sa.Column("require_provider_response",    sa.Boolean(),   nullable=False, server_default="true"),
        sa.Column("default_provider_response_hours", sa.Integer(), nullable=False, server_default="24"),
        sa.Column("default_resolution_hours",     sa.Integer(),   nullable=False, server_default="72"),
        sa.Column("is_active",                    sa.Boolean(),   nullable=False, server_default="true"),
        sa.Column("created_at",                   sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at",                   sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_cp_category_id", "complaint_policies", ["category_id"])
    op.create_index("ix_cp_is_active",   "complaint_policies", ["is_active"])

    # Seed default policy
    op.execute("""
        INSERT INTO complaint_policies (
            id, policy_key, policy_name,
            allow_customer_complaints, complaint_window_hours,
            allow_duplicate_open_complaints, allow_rework, allow_refund_request,
            require_admin_review, require_provider_response,
            default_provider_response_hours, default_resolution_hours,
            is_active, created_at, updated_at
        ) VALUES (
            gen_random_uuid(), 'default', 'Default Complaint Policy',
            true, 168, false, true, true, true, true, 24, 72,
            true, NOW(), NOW()
        )
    """)


def downgrade() -> None:
    op.drop_table("complaint_policies")
    op.drop_table("refund_requests")
    op.drop_table("service_rework_requests")
    op.drop_table("complaint_resolutions")
    op.drop_table("complaint_events")
    op.drop_table("complaint_media")
    op.drop_table("complaint_messages")
    op.drop_table("customer_complaints")
