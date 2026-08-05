"""TENANT-SIGNUP-V2: pending self-serve registration + draft_setup enrollment status.

Replaces the payment-first /v1/public/register/* flow with a 5-step,
no-payment flow (Owner Account -> Verify Contact -> Business Identity ->
Select Vertical -> Review & Consent -> Create Workspace). This migration
adds the working table for steps 1-4 (`pending_tenant_registrations`) --
the real User/Tenant/TenantBusinessProfile/TenantVerticalEnrollment rows
are only created atomically at step 5, so an abandoned signup never
leaves an orphan login-capable account behind.

`TenantVerticalEnrollment.status` is a free-text String(20) column with
app-level validation only (see ENROLLMENT_STATUSES in
vertical_catalog/service.py) -- no DB-level enum/check constraint exists
for it today, so adding the new `draft_setup` value requires no schema
change, only the app-level constant update made alongside this migration.

Revision ID: 188
Revises: 187
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "188"
down_revision = "187"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pending_tenant_registrations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),

        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("mobile", sa.String(20), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("authorized_declaration", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("tos_privacy_accepted", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("marketing_consent", sa.Boolean, nullable=False, server_default=sa.false()),

        sa.Column("mobile_verified", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("email_verified", sa.Boolean, nullable=False, server_default=sa.false()),

        sa.Column("legal_name", sa.String(255), nullable=True),
        sa.Column("business_name", sa.String(255), nullable=True),
        sa.Column("gstin", sa.String(20), nullable=True),
        sa.Column("pan", sa.String(10), nullable=True),
        sa.Column("cin", sa.String(25), nullable=True),
        sa.Column("business_type", sa.String(50), nullable=True),
        sa.Column("year_established", sa.Integer, nullable=True),
        sa.Column("employee_count", sa.Integer, nullable=True),
        sa.Column("website_url", sa.String(255), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("registered_address", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),

        sa.Column("selected_vertical_key", sa.String(80), nullable=True),

        sa.Column("status", sa.String(20), nullable=False, server_default="in_progress"),
        sa.Column("idempotency_key", sa.String(100), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_user_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_ptr_email", "pending_tenant_registrations", ["email"])
    op.create_index("ix_ptr_mobile", "pending_tenant_registrations", ["mobile"])
    op.create_index("ix_ptr_status", "pending_tenant_registrations", ["status"])


def downgrade() -> None:
    op.drop_index("ix_ptr_status", table_name="pending_tenant_registrations")
    op.drop_index("ix_ptr_mobile", table_name="pending_tenant_registrations")
    op.drop_index("ix_ptr_email", table_name="pending_tenant_registrations")
    op.drop_table("pending_tenant_registrations")
