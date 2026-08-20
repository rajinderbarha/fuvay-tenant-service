"""Provider-owned warranties and canonical customer-credit remedies.

Revision ID: 268
Revises: 267
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "268"
down_revision = "267"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tenant_services",
        sa.Column("warranty_days", sa.Integer(), nullable=False, server_default="5"),
    )
    op.create_check_constraint(
        "ck_tenant_services_warranty_days_minimum",
        "tenant_services",
        "warranty_days >= 5",
    )

    op.add_column("service_jobs", sa.Column("warranty_days_snapshot", sa.Integer(), nullable=True))
    op.add_column("service_jobs", sa.Column("warranty_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(
        "ix_sj_customer_warranty_expiry",
        "service_jobs",
        ["customer_id", "warranty_expires_at"],
        postgresql_where="warranty_expires_at IS NOT NULL",
    )
    # Existing completed work receives the policy minimum. Future jobs snapshot
    # the provider's service-level value at completion.
    op.execute("""
        UPDATE service_jobs
           SET warranty_days_snapshot = 5,
               warranty_expires_at = COALESCE(
                   (completion_data->>'completed_at')::timestamptz,
                   updated_at,
                   created_at
               ) + INTERVAL '5 days'
         WHERE status IN ('completed', 'work_done', 'invoice_issued', 'paid')
           AND warranty_expires_at IS NULL
    """)

    for name, column in (
        ("provider_response_due_at", sa.DateTime(timezone=True)),
        ("provider_responded_at", sa.DateTime(timezone=True)),
        ("provider_resolution", sa.Text()),
        ("provider_resolved_at", sa.DateTime(timezone=True)),
        ("escalated_at", sa.DateTime(timezone=True)),
        ("escalation_reason", sa.Text()),
        ("warranty_expires_at", sa.DateTime(timezone=True)),
        ("warranty_days_snapshot", sa.Integer()),
        ("provider_credit_deducted", sa.Numeric(12, 2)),
        ("security_deposit_deducted", sa.Numeric(12, 2)),
        ("customer_credit_id", postgresql.UUID(as_uuid=True)),
    ):
        op.add_column("warranty_claims", sa.Column(name, column, nullable=True))
    op.alter_column(
        "warranty_claims",
        "status",
        existing_type=sa.String(length=20),
        type_=sa.String(length=40),
        existing_nullable=False,
    )
    op.execute("UPDATE warranty_claims SET status='provider_action_required' WHERE status='pending'")
    op.create_index(
        "ix_wc_provider_queue",
        "warranty_claims",
        ["tenant_id", "status", "provider_response_due_at"],
    )
    op.create_index(
        "ix_wc_admin_attention",
        "warranty_claims",
        ["status", "escalated_at", "created_at"],
    )

    for name, column in (
        ("provider_response_due_at", sa.DateTime(timezone=True)),
        ("escalated_at", sa.DateTime(timezone=True)),
        ("escalation_reason", sa.Text()),
        ("resolution_method", sa.String(length=40)),
        ("customer_credit_id", postgresql.UUID(as_uuid=True)),
        ("provider_credit_deducted", sa.Numeric(12, 2)),
        ("security_deposit_deducted", sa.Numeric(12, 2)),
    ):
        op.add_column("refund_requests", sa.Column(name, column, nullable=True))
    op.create_index(
        "ix_refund_provider_queue",
        "refund_requests",
        ["tenant_id", "status", "provider_response_due_at"],
    )

    # Exactly-once provider usage-credit movements for all future recovery
    # paths. Existing data was audited before this migration and has no dupes.
    op.create_index(
        "uq_ucl_tenant_idempotency_key",
        "usage_credit_ledger",
        ["tenant_id", "idempotency_key"],
        unique=True,
        postgresql_where="idempotency_key IS NOT NULL",
    )


def downgrade() -> None:
    op.drop_index("uq_ucl_tenant_idempotency_key", table_name="usage_credit_ledger")
    op.drop_index("ix_refund_provider_queue", table_name="refund_requests")
    for name in (
        "security_deposit_deducted", "provider_credit_deducted", "customer_credit_id",
        "resolution_method", "escalation_reason", "escalated_at", "provider_response_due_at",
    ):
        op.drop_column("refund_requests", name)
    op.drop_index("ix_wc_admin_attention", table_name="warranty_claims")
    op.drop_index("ix_wc_provider_queue", table_name="warranty_claims")
    op.execute("UPDATE warranty_claims SET status='pending' WHERE status='provider_action_required'")
    op.alter_column(
        "warranty_claims",
        "status",
        existing_type=sa.String(length=40),
        type_=sa.String(length=20),
        existing_nullable=False,
    )
    for name in (
        "customer_credit_id", "security_deposit_deducted", "provider_credit_deducted",
        "warranty_days_snapshot", "warranty_expires_at", "escalation_reason", "escalated_at",
        "provider_resolved_at", "provider_resolution", "provider_responded_at", "provider_response_due_at",
    ):
        op.drop_column("warranty_claims", name)
    op.drop_index("ix_sj_customer_warranty_expiry", table_name="service_jobs")
    op.drop_column("service_jobs", "warranty_expires_at")
    op.drop_column("service_jobs", "warranty_days_snapshot")
    op.drop_constraint("ck_tenant_services_warranty_days_minimum", "tenant_services", type_="check")
    op.drop_column("tenant_services", "warranty_days")
