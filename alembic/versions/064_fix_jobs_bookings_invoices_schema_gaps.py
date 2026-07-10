"""Fix jobs, bookings, invoice_records schema gaps — missing columns added in sprints 6-9

Revision ID: 064
Revises: 063
Create Date: 2026-07-04
"""
from __future__ import annotations
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "064"
down_revision = "063"
branch_labels = None
depends_on = None


def _col_exists(conn, table: str, column: str) -> bool:
    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_schema='public' AND table_name=:t AND column_name=:c"
    ), {"t": table, "c": column})
    return result.fetchone() is not None


def _index_exists(conn, index_name: str) -> bool:
    result = conn.execute(sa.text(
        "SELECT 1 FROM pg_indexes WHERE schemaname='public' AND indexname=:i"
    ), {"i": index_name})
    return result.fetchone() is not None


def _add_if_missing(conn, table, col_name, col_def):
    if not _col_exists(conn, table, col_name):
        op.add_column(table, col_def)


def upgrade() -> None:
    conn = op.get_bind()

    # ── jobs ──────────────────────────────────────────────────────────────────
    uuid_ = postgresql.UUID(as_uuid=True)
    nullable_uuid_cols = [
        "address_id", "service_id", "matched_service_area_id",
        "matched_service_area_service_id", "invoice_id", "payment_id",
        "commission_id", "closed_by_user_id", "assigned_by_user_id",
        "parent_job_id", "quote_id",
    ]
    for col in nullable_uuid_cols:
        _add_if_missing(conn, "jobs", col, sa.Column(col, uuid_, nullable=True))

    nullable_str_cols = [
        ("city",                    sa.String(100)),
        ("zipcode",                 sa.String(20)),
        ("coverage_match_level",    sa.String(20)),
        ("staff_rejection_reason",  sa.String(500)),
        ("cancellation_reason",     sa.String(500)),
        ("sla_breach_level",        sa.String(20)),
        ("quote_rejection_reason",  sa.String(500)),
        ("closing_notes",           sa.Text()),
        ("closure_notes",           sa.Text()),
        ("findings",                sa.Text()),
        ("recommendation",          sa.Text()),
        ("assessment_findings",     sa.Text()),
        ("recommended_work",        sa.Text()),
    ]
    for col_name, col_type in nullable_str_cols:
        _add_if_missing(conn, "jobs", col_name, sa.Column(col_name, col_type, nullable=True))

    nullable_num_cols = [
        ("estimated_price",     sa.Numeric(10, 2)),
        ("final_payable_amount",sa.Numeric(10, 2)),
        ("pre_approval_limit",  sa.Numeric(10, 2)),
        ("sla_minutes",         sa.Integer()),
        ("duration_estimate_minutes", sa.Integer()),
        ("minutes_in_status",   sa.Integer()),
    ]
    for col_name, col_type in nullable_num_cols:
        _add_if_missing(conn, "jobs", col_name, sa.Column(col_name, col_type, nullable=True))

    nullable_ts_cols = [
        "invoice_generated_at", "payment_pending_at", "paid_at",
        "assigned_at", "accepted_at", "rejected_at", "en_route_at",
        "arrived_at", "work_started_at", "work_completed_at",
        "cancelled_at", "status_updated_at", "current_status_started_at",
        "assessment_completed_at", "quote_sent_at", "quote_approved_at",
        "quote_rejected_at", "checklist_started_at", "checklist_completed_at",
    ]
    for col in nullable_ts_cols:
        _add_if_missing(conn, "jobs", col, sa.Column(col, sa.DateTime(timezone=True), nullable=True))

    notnull_cols = [
        ("source",                  sa.String(30),     "direct"),
        ("job_type",                sa.String(20),     "repair"),
        ("sla_breached",            sa.Boolean(),      "false"),
        ("quote_required",          sa.Boolean(),      "false"),
        ("checklist_required",      sa.Boolean(),      "false"),
        ("converted_from_consultation", sa.Boolean(),  "false"),
    ]
    for col_name, col_type, default in notnull_cols:
        if not _col_exists(conn, "jobs", col_name):
            op.add_column("jobs", sa.Column(col_name, col_type, nullable=False, server_default=default))

    jsonb_notnull_cols = [
        ("checklist",       "[]"),
        ("estimated_parts", "[]"),
    ]
    for col_name, default in jsonb_notnull_cols:
        if not _col_exists(conn, "jobs", col_name):
            op.add_column("jobs", sa.Column(col_name, postgresql.JSONB(), nullable=False, server_default=default))

    for idx_name, cols in [
        ("ix_job_type",       ["job_type"]),
        ("ix_job_city",       ["city"]),
        ("ix_job_invoice_id", ["invoice_id"]),
    ]:
        if not _index_exists(conn, idx_name):
            op.create_index(idx_name, "jobs", cols)

    # ── bookings ──────────────────────────────────────────────────────────────
    bookings_nullable_uuid = [
        "matched_service_area_service_id", "confirmed_by_user_id",
        "rejected_by_user_id", "cancelled_by_user_id", "converted_job_id",
    ]
    for col in bookings_nullable_uuid:
        _add_if_missing(conn, "bookings", col, sa.Column(col, uuid_, nullable=True))

    bookings_nullable_other = [
        ("city",              sa.String(100)),
        ("rejection_reason",  sa.String(500)),
        ("estimated_price",   sa.Numeric(10, 2)),
        ("final_price",       sa.Numeric(10, 2)),
        ("sla_minutes",       sa.Integer()),
        ("matching_snapshot", postgresql.JSONB()),
    ]
    for col_name, col_type in bookings_nullable_other:
        _add_if_missing(conn, "bookings", col_name, sa.Column(col_name, col_type, nullable=True))

    bookings_ts = [
        "confirmed_at", "rejected_at", "converted_to_job_at", "status_updated_at",
    ]
    for col in bookings_ts:
        _add_if_missing(conn, "bookings", col, sa.Column(col, sa.DateTime(timezone=True), nullable=True))

    # ── invoice_records ───────────────────────────────────────────────────────
    invoice_nullable_uuid = ["job_id", "customer_id", "service_id"]
    for col in invoice_nullable_uuid:
        _add_if_missing(conn, "invoice_records", col, sa.Column(col, uuid_, nullable=True))

    invoice_nullable_other = [
        ("job_type",       sa.String(20)),
        ("subtotal_amount",sa.Numeric(10, 2)),
        ("parts_amount",   sa.Numeric(10, 2)),
        ("labour_amount",  sa.Numeric(10, 2)),
        ("visit_fee",      sa.Numeric(10, 2)),
        ("discount_amount",sa.Numeric(10, 2)),
        ("pdf_url",        sa.String(500)),
    ]
    for col_name, col_type in invoice_nullable_other:
        _add_if_missing(conn, "invoice_records", col_name, sa.Column(col_name, col_type, nullable=True))

    if not _col_exists(conn, "invoice_records", "paid_at"):
        op.add_column("invoice_records", sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True))
    if not _col_exists(conn, "invoice_records", "meta"):
        op.add_column("invoice_records", sa.Column("meta", postgresql.JSONB(), nullable=False, server_default="{}"))

    if not _index_exists(conn, "ix_inv_job_id"):
        op.create_index("ix_inv_job_id", "invoice_records", ["job_id"])
    if not _index_exists(conn, "ix_inv_customer_id"):
        op.create_index("ix_inv_customer_id", "invoice_records", ["customer_id"])


def downgrade() -> None:
    op.drop_index("ix_inv_customer_id", "invoice_records")
    op.drop_index("ix_inv_job_id",      "invoice_records")
    for col in ["meta", "pdf_url", "paid_at", "discount_amount", "visit_fee",
                "labour_amount", "parts_amount", "subtotal_amount", "job_type",
                "service_id", "customer_id", "job_id"]:
        op.drop_column("invoice_records", col)

    for col in ["status_updated_at", "converted_job_id", "converted_to_job_at",
                "cancelled_by_user_id", "rejection_reason", "rejected_by_user_id",
                "rejected_at", "confirmed_by_user_id", "confirmed_at", "matching_snapshot",
                "sla_minutes", "final_price", "estimated_price",
                "matched_service_area_service_id", "city"]:
        op.drop_column("bookings", col)

    op.drop_index("ix_job_sla_breach", "jobs")
    op.drop_index("ix_job_invoice_id", "jobs")
    op.drop_index("ix_job_city",       "jobs")
    op.drop_index("ix_job_type",       "jobs")
    for col in ["converted_from_consultation", "checklist_completed_at", "checklist_started_at",
                "checklist_required", "quote_rejection_reason", "quote_rejected_at",
                "quote_approved_at", "quote_sent_at", "assessment_completed_at", "estimated_parts",
                "recommended_work", "assessment_findings", "pre_approval_limit", "quote_id",
                "quote_required", "closing_notes", "current_status_started_at", "sla_breach_level",
                "sla_breached", "minutes_in_status", "status_updated_at", "cancellation_reason",
                "cancelled_at", "work_completed_at", "work_started_at", "arrived_at",
                "en_route_at", "staff_rejection_reason", "rejected_at", "accepted_at",
                "assigned_by_user_id", "assigned_at", "final_payable_amount", "closure_notes",
                "closed_by_user_id", "paid_at", "payment_pending_at", "invoice_generated_at",
                "commission_id", "payment_id", "invoice_id", "duration_estimate_minutes",
                "checklist", "recommendation", "findings", "parent_job_id", "job_type",
                "source", "sla_minutes", "estimated_price", "coverage_match_level",
                "matched_service_area_service_id", "matched_service_area_id", "zipcode",
                "city", "service_id", "address_id"]:
        op.drop_column("jobs", col)
