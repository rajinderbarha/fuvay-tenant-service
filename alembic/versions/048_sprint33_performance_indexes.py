"""Sprint 33 — Performance indexes for high-query tables.

Revision: 048
Down revision: 047

Adds missing composite indexes on:
  customer_reviews           — tenant_id, customer_id, status, created_at
  customer_complaints        — tenant_id, customer_id, status, created_at
  service_invoices           — tenant_id+status composite (covers sorted admin list)
  service_payment_records    — created_at, tenant_id+status composite
  svc_commission_records     — created_at, tenant_id+created_at composite
"""
from __future__ import annotations

from alembic import op

revision = "048"
down_revision = "047"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # customer_reviews — composite indexes (simple ones already added in migration 042)
    op.create_index("ix_cr_created_at",      "customer_reviews", ["created_at"])
    op.create_index("ix_cr_tenant_status",   "customer_reviews", ["tenant_id", "status"])
    op.create_index("ix_cr_tenant_created",  "customer_reviews", ["tenant_id", "created_at"])

    # customer_complaints — composite indexes (simple ones already added in migration 043)
    op.create_index("ix_cc_created_at",      "customer_complaints", ["created_at"])
    op.create_index("ix_cc_tenant_status",   "customer_complaints", ["tenant_id", "status"])
    op.create_index("ix_cc_tenant_created",  "customer_complaints", ["tenant_id", "created_at"])

    # service_invoices — composite for admin sorted list
    op.create_index("ix_si_tenant_status",   "service_invoices",  ["tenant_id", "status"])
    op.create_index("ix_si_created_at",      "service_invoices",  ["created_at"])

    # service_payment_records — created_at + composite
    op.create_index("ix_spr_created_at",         "service_payment_records", ["created_at"])
    op.create_index("ix_spr_tenant_created",     "service_payment_records", ["tenant_id", "created_at"])

    # svc_commission_records — created_at + composite
    op.create_index("ix_svccom_created_at",      "svc_commission_records", ["created_at"])
    op.create_index("ix_svccom_tenant_created",  "svc_commission_records", ["tenant_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_svccom_tenant_created",  "svc_commission_records")
    op.drop_index("ix_svccom_created_at",      "svc_commission_records")
    op.drop_index("ix_spr_tenant_created",     "service_payment_records")
    op.drop_index("ix_spr_created_at",         "service_payment_records")
    op.drop_index("ix_si_created_at",          "service_invoices")
    op.drop_index("ix_si_tenant_status",       "service_invoices")
    op.drop_index("ix_cc_tenant_created",      "customer_complaints")
    op.drop_index("ix_cc_tenant_status",       "customer_complaints")
    op.drop_index("ix_cc_created_at",          "customer_complaints")
    op.drop_index("ix_cr_tenant_created",      "customer_reviews")
    op.drop_index("ix_cr_tenant_status",       "customer_reviews")
    op.drop_index("ix_cr_created_at",          "customer_reviews")
