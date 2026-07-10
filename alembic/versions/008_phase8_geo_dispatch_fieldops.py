"""Phase 8 — Geo + Dispatch + Field Ops (9 tables)
Revision ID: 008
Revises: 007
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID, ARRAY

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Geo (3 tables) ────────────────────────────────────────────────────────
    op.create_table("service_zones",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("zone_name", sa.String(100), nullable=False),
        sa.Column("zone_type", sa.String(20), nullable=False),
        sa.Column("identifiers", JSONB, nullable=False, server_default="[]"),
        sa.Column("center_lat", sa.Float, nullable=True),
        sa.Column("center_lng", sa.Float, nullable=True),
        sa.Column("radius_km", sa.Float, nullable=True),
        sa.Column("surcharge_pct", sa.Float, nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("valid_from", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("set_by", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_sz_tenant_active","service_zones",["tenant_id","is_active"])

    op.create_table("staff_locations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("staff_id", UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("latitude", sa.Float, nullable=False),
        sa.Column("longitude", sa.Float, nullable=False),
        sa.Column("accuracy_m", sa.Float, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="available"),
        sa.Column("last_ping_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("active_job_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("meta", JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("staff_id","tenant_id", name="uq_sl_staff_tenant"),
    )
    op.create_index("ix_sl_tenant","staff_locations",["tenant_id"])

    op.create_table("zone_analytic_snapshots",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("zone_id", UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("snapshot_date", sa.String(10), nullable=False),
        sa.Column("job_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("avg_response_min", sa.Float, nullable=False, server_default="0"),
        sa.Column("completion_rate", sa.Float, nullable=False, server_default="100"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_zan_zone_date","zone_analytic_snapshots",["zone_id","snapshot_date"])

    # ── Dispatch (2 tables) ───────────────────────────────────────────────────
    op.create_table("dispatch_records",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("job_id", sa.String(100), nullable=False, unique=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("dispatch_mode", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("assigned_staff_id", UUID(as_uuid=True), nullable=True),
        sa.Column("candidates_scored", JSONB, nullable=False, server_default="[]"),
        sa.Column("score_weights", JSONB, nullable=False, server_default="{}"),
        sa.Column("rejection_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("escalation_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dispatched_by", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("job_id", name="uq_dr_job"),
    )
    op.create_index("ix_dr_tenant","dispatch_records",["tenant_id"])
    op.create_index("ix_dr_staff","dispatch_records",["assigned_staff_id"])

    op.create_table("dispatch_escalation_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("job_id", sa.String(100), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("staff_id", UUID(as_uuid=True), nullable=False),
        sa.Column("attempt_no", sa.Integer, nullable=False),
        sa.Column("outcome", sa.String(20), nullable=False),
        sa.Column("reason", sa.String(255), nullable=True),
        sa.Column("score", sa.Float, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_del_job_id","dispatch_escalation_logs",["job_id"])

    # ── Field Ops (4 tables) ──────────────────────────────────────────────────
    op.create_table("jobs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("booking_id", sa.String(100), nullable=True),
        sa.Column("customer_id", UUID(as_uuid=True), nullable=True),
        sa.Column("assigned_staff_id", UUID(as_uuid=True), nullable=True),
        sa.Column("service_type_id", sa.String(100), nullable=False),
        sa.Column("service_category", sa.String(100), nullable=False),
        sa.Column("status", sa.String(40), nullable=False, server_default="draft"),
        sa.Column("job_number", sa.String(30), nullable=False, unique=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("address", JSONB, nullable=False, server_default="{}"),
        sa.Column("pincode", sa.String(20), nullable=True),
        sa.Column("latitude", sa.Float, nullable=True),
        sa.Column("longitude", sa.Float, nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("quoted_price", sa.Numeric(10,2), nullable=True),
        sa.Column("final_price", sa.Numeric(10,2), nullable=True),
        sa.Column("commission_deducted", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("commission_amount", sa.Numeric(10,4), nullable=True),
        sa.Column("sla_breach", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("customer_token", sa.String(64), nullable=False),
        sa.Column("customer_rating", sa.Float, nullable=True),
        sa.Column("meta", JSONB, nullable=False, server_default="{}"),
        sa.Column("tags", JSONB, nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_job_tenant_status","jobs",["tenant_id","status"])
    op.create_index("ix_job_staff","jobs",["assigned_staff_id"])
    op.create_index("ix_job_customer","jobs",["customer_id"])
    op.create_index("ix_job_booking","jobs",["booking_id"])

    op.create_table("job_status_history",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("job_id", UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("from_status", sa.String(40), nullable=True),
        sa.Column("to_status", sa.String(40), nullable=False),
        sa.Column("changed_by", UUID(as_uuid=True), nullable=True),
        sa.Column("changed_by_role", sa.String(30), nullable=True),
        sa.Column("reason", sa.String(500), nullable=True),
        sa.Column("lat", sa.Float, nullable=True),
        sa.Column("lng", sa.Float, nullable=True),
        sa.Column("meta", JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_jsh_job_id","job_status_history",["job_id"])
    op.create_index("ix_jsh_tenant","job_status_history",["tenant_id"])

    op.create_table("job_notes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("job_id", UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("author_id", UUID(as_uuid=True), nullable=True),
        sa.Column("author_role", sa.String(30), nullable=True),
        sa.Column("note_type", sa.String(30), nullable=False, server_default="staff_note"),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("status_at", sa.String(40), nullable=True),
        sa.Column("is_internal", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_jn_job_id","job_notes",["job_id"])

    op.create_table("job_media",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("job_id", UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("media_id", UUID(as_uuid=True), nullable=True),
        sa.Column("uploaded_by", UUID(as_uuid=True), nullable=True),
        sa.Column("status_at", sa.String(40), nullable=True),
        sa.Column("media_type", sa.String(30), nullable=False, server_default="photo"),
        sa.Column("caption", sa.String(255), nullable=True),
        sa.Column("storage_key", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_jm_job_id","job_media",["job_id"])


def downgrade() -> None:
    for t in ["job_media","job_notes","job_status_history","jobs",
              "dispatch_escalation_logs","dispatch_records",
              "zone_analytic_snapshots","staff_locations","service_zones"]:
        op.drop_table(t)
