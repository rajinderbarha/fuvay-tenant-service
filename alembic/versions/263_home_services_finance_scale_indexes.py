"""Home Services finance directory scale indexes.

Revision ID: 263
Revises: 262
"""
from __future__ import annotations

from alembic import op

revision = "263"
down_revision = "262"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_ucl_tenant_created_at", "usage_credit_ledger", ["tenant_id", "created_at"])
    op.create_index("ix_ucl_event_created_at", "usage_credit_ledger", ["event_type", "created_at"])
    op.create_index("ix_cto_tenant_created_at", "credit_topup_orders", ["tenant_id", "created_at"])
    op.create_index("ix_cto_status_created_at", "credit_topup_orders", ["payment_status", "created_at"])
    op.create_index("ix_si_tenant_created_at", "service_invoices", ["tenant_id", "created_at"])
    op.create_index("ix_svccom_tenant_created_at", "svc_commission_records", ["tenant_id", "created_at"])
    op.create_index("ix_fev_created_at", "financial_events", ["created_at"])
    op.create_index("ix_fev_tenant_created_at", "financial_events", ["tenant_id", "created_at"])
    op.create_index("ix_security_deposit_status_created_at", "security_deposits", ["status", "created_at"])
    op.create_index("ix_wc_status_created_at", "warranty_claims", ["status", "created_at"])
    op.create_index("ix_refund_tenant_created_at", "refund_requests", ["tenant_id", "created_at"])
    op.create_index("ix_refund_status_created_at", "refund_requests", ["status", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_refund_status_created_at", table_name="refund_requests")
    op.drop_index("ix_refund_tenant_created_at", table_name="refund_requests")
    op.drop_index("ix_wc_status_created_at", table_name="warranty_claims")
    op.drop_index("ix_security_deposit_status_created_at", table_name="security_deposits")
    op.drop_index("ix_fev_tenant_created_at", table_name="financial_events")
    op.drop_index("ix_fev_created_at", table_name="financial_events")
    op.drop_index("ix_svccom_tenant_created_at", table_name="svc_commission_records")
    op.drop_index("ix_si_tenant_created_at", table_name="service_invoices")
    op.drop_index("ix_cto_status_created_at", table_name="credit_topup_orders")
    op.drop_index("ix_cto_tenant_created_at", table_name="credit_topup_orders")
    op.drop_index("ix_ucl_event_created_at", table_name="usage_credit_ledger")
    op.drop_index("ix_ucl_tenant_created_at", table_name="usage_credit_ledger")
