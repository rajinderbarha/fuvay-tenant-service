"""TENANT-HS-FINANCE-HUB-01: security-deposit refund request workflow.

The Home Services Finance Hub spec requires a real, auditable deposit
refund workflow (Draft -> Submitted -> Eligibility Review -> Liability/Hold
Review -> Admin Decision -> Processing -> Refunded/Rejected). No table for
this existed anywhere in the codebase (audited: platform_commerce
SecurityDeposit tracks the HELD deposit only; complaints.RefundRequest is a
CUSTOMER job refund, a completely different domain). This is the one
genuinely new table this feature needs -- wallet, ledger, deposit-held,
policy and top-up-order storage all already exist and are reused.

Tenant can create/submit and view. Only an admin holding
finance:deposits:refund may approve/reject/process (enforced in the
router, never only in the UI).

Revision ID: 201
Revises: 200
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "201"
down_revision = "200"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "hs_deposit_refund_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vertical_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("vertical_key", sa.String(50), nullable=False, server_default="home_services"),
        sa.Column("request_ref", sa.String(40), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="draft"),
        # Money: Numeric only, never float.
        sa.Column("requested_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("approved_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("eligible_amount_snapshot", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("deposit_held_snapshot", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("deposit_required_snapshot", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("qualifying_technicians_snapshot", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("policy_version", sa.Integer(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        # Bank details: account number is stored MASKED only. ServiceOS does
        # not need (and deliberately does not keep) the full number here --
        # payout execution is an admin/offline process against the tenant's
        # verified business record.
        sa.Column("bank_account_name", sa.String(160), nullable=True),
        sa.Column("bank_account_number_masked", sa.String(40), nullable=True),
        sa.Column("bank_ifsc", sa.String(20), nullable=True),
        sa.Column("eligibility_checks", postgresql.JSONB(), nullable=True),
        sa.Column("blockers", postgresql.JSONB(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decision_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("decision_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decision_note", sa.Text(), nullable=True),
        sa.Column("info_requested_note", sa.Text(), nullable=True),
        sa.Column("tenant_response", sa.Text(), nullable=True),
        sa.Column("processing_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("refunded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payout_reference", sa.String(80), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("request_ref", name="uq_hsdrr_request_ref"),
    )
    op.create_index("ix_hsdrr_tenant_id", "hs_deposit_refund_requests", ["tenant_id"])
    op.create_index("ix_hsdrr_status", "hs_deposit_refund_requests", ["status"])
    # At most ONE open (non-terminal) refund request per tenant -- prevents a
    # tenant from queueing several overlapping claims against the same held
    # deposit. Enforced at the DB, not only in the service.
    op.create_index(
        "uq_hsdrr_one_open_per_tenant", "hs_deposit_refund_requests", ["tenant_id"],
        unique=True,
        postgresql_where=sa.text("status NOT IN ('refunded','rejected','withdrawn')"),
    )


def downgrade() -> None:
    op.drop_index("uq_hsdrr_one_open_per_tenant", table_name="hs_deposit_refund_requests")
    op.drop_index("ix_hsdrr_status", table_name="hs_deposit_refund_requests")
    op.drop_index("ix_hsdrr_tenant_id", table_name="hs_deposit_refund_requests")
    op.drop_table("hs_deposit_refund_requests")
