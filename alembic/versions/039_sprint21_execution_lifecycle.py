"""Sprint 21 — Repair / Service / Consultation Execution Flow.

Creates execution event and note tables for all three domain types.
Also creates Sprint 21 service_job_media table (separate from legacy job_media).

Revision ID: 039
Revises: 038
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "039"
down_revision = "038"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. service_job_execution_events
    op.create_table(
        "service_job_execution_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("booking_id",       UUID(as_uuid=True), nullable=False),
        sa.Column("job_id",           UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id",        UUID(as_uuid=True), nullable=False),
        sa.Column("staff_member_id",  UUID(as_uuid=True), nullable=True),
        sa.Column("actor_user_id",    UUID(as_uuid=True), nullable=True),
        sa.Column("actor_role",       sa.String(50),  nullable=True),
        sa.Column("event_type",       sa.String(60),  nullable=False),
        sa.Column("old_status",       sa.String(50),  nullable=True),
        sa.Column("new_status",       sa.String(50),  nullable=True),
        sa.Column("notes",            sa.Text(),      nullable=True),
        sa.Column("metadata",         JSONB,          nullable=True),
        sa.Column("request_id",       sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_sjee_job_id",    "service_job_execution_events", ["job_id"])
    op.create_index("ix_sjee_tenant_id", "service_job_execution_events", ["tenant_id"])
    op.create_index("ix_sjee_event_type","service_job_execution_events", ["event_type"])

    # 2. service_job_execution_notes
    op.create_table(
        "service_job_execution_notes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("booking_id",          UUID(as_uuid=True), nullable=False),
        sa.Column("job_id",              UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id",           UUID(as_uuid=True), nullable=False),
        sa.Column("staff_member_id",     UUID(as_uuid=True), nullable=True),
        sa.Column("note_type",           sa.String(40),  nullable=False),
        sa.Column("note_text",           sa.Text(),      nullable=False),
        sa.Column("is_customer_visible", sa.Boolean(),   nullable=False, server_default="false"),
        sa.Column("created_by_user_id",  UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_sjen_job_id",    "service_job_execution_notes", ["job_id"])
    op.create_index("ix_sjen_tenant_id", "service_job_execution_notes", ["tenant_id"])

    # 3. service_job_media (Sprint 21 — distinct from legacy job_media)
    op.create_table(
        "service_job_media_uploads",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("booking_id",          UUID(as_uuid=True), nullable=False),
        sa.Column("job_id",              UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id",           UUID(as_uuid=True), nullable=False),
        sa.Column("staff_member_id",     UUID(as_uuid=True), nullable=True),
        sa.Column("media_type",          sa.String(40),  nullable=False),
        sa.Column("file_url",            sa.String(1000),nullable=False),
        sa.Column("file_name",           sa.String(255), nullable=True),
        sa.Column("mime_type",           sa.String(100), nullable=True),
        sa.Column("file_size",           sa.Integer(),   nullable=True),
        sa.Column("caption",             sa.Text(),      nullable=True),
        sa.Column("is_customer_visible", sa.Boolean(),   nullable=False, server_default="false"),
        sa.Column("uploaded_by_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_sjmu_job_id",    "service_job_media_uploads", ["job_id"])
    op.create_index("ix_sjmu_tenant_id", "service_job_media_uploads", ["tenant_id"])

    # 4. coaching_appointment_execution_events
    op.create_table(
        "coaching_appointment_execution_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("appointment_id",  UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id",       UUID(as_uuid=True), nullable=False),
        sa.Column("staff_member_id", UUID(as_uuid=True), nullable=True),
        sa.Column("actor_user_id",   UUID(as_uuid=True), nullable=True),
        sa.Column("actor_role",      sa.String(50),  nullable=True),
        sa.Column("event_type",      sa.String(60),  nullable=False),
        sa.Column("old_status",      sa.String(50),  nullable=True),
        sa.Column("new_status",      sa.String(50),  nullable=True),
        sa.Column("notes",           sa.Text(),      nullable=True),
        sa.Column("metadata",        JSONB,          nullable=True),
        sa.Column("request_id",      sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_caee_appt_id",   "coaching_appointment_execution_events", ["appointment_id"])
    op.create_index("ix_caee_tenant_id", "coaching_appointment_execution_events", ["tenant_id"])

    # 5. coaching_appointment_notes
    op.create_table(
        "coaching_appointment_notes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("appointment_id",      UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id",           UUID(as_uuid=True), nullable=False),
        sa.Column("staff_member_id",     UUID(as_uuid=True), nullable=True),
        sa.Column("note_type",           sa.String(40),  nullable=False),
        sa.Column("note_text",           sa.Text(),      nullable=False),
        sa.Column("is_customer_visible", sa.Boolean(),   nullable=False, server_default="false"),
        sa.Column("created_by_user_id",  UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_can_appt_id",   "coaching_appointment_notes", ["appointment_id"])
    op.create_index("ix_can_tenant_id", "coaching_appointment_notes", ["tenant_id"])

    # 6. real_estate_lead_execution_events
    op.create_table(
        "real_estate_lead_execution_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("lead_id",          UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id",        UUID(as_uuid=True), nullable=True),
        sa.Column("assigned_agent_id",UUID(as_uuid=True), nullable=True),
        sa.Column("actor_user_id",    UUID(as_uuid=True), nullable=True),
        sa.Column("actor_role",       sa.String(50),  nullable=True),
        sa.Column("event_type",       sa.String(60),  nullable=False),
        sa.Column("old_status",       sa.String(50),  nullable=True),
        sa.Column("new_status",       sa.String(50),  nullable=True),
        sa.Column("notes",            sa.Text(),      nullable=True),
        sa.Column("metadata",         JSONB,          nullable=True),
        sa.Column("request_id",       sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_relee_lead_id",   "real_estate_lead_execution_events", ["lead_id"])
    op.create_index("ix_relee_tenant_id", "real_estate_lead_execution_events", ["tenant_id"])

    # 7. real_estate_lead_notes
    op.create_table(
        "real_estate_lead_notes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("lead_id",             UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id",           UUID(as_uuid=True), nullable=True),
        sa.Column("assigned_agent_id",   UUID(as_uuid=True), nullable=True),
        sa.Column("note_type",           sa.String(40),  nullable=False),
        sa.Column("note_text",           sa.Text(),      nullable=False),
        sa.Column("is_customer_visible", sa.Boolean(),   nullable=False, server_default="false"),
        sa.Column("created_by_user_id",  UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_reln_lead_id",   "real_estate_lead_notes", ["lead_id"])
    op.create_index("ix_reln_tenant_id", "real_estate_lead_notes", ["tenant_id"])


def downgrade() -> None:
    op.drop_table("real_estate_lead_notes")
    op.drop_table("real_estate_lead_execution_events")
    op.drop_table("coaching_appointment_notes")
    op.drop_table("coaching_appointment_execution_events")
    op.drop_table("service_job_media_uploads")
    op.drop_table("service_job_execution_notes")
    op.drop_table("service_job_execution_events")
