"""Restore the Home Services activation finance policy on the live vertical.

Revision ID: 295
Revises: 294

The Home Services vertical was recreated during catalog cleanup, leaving the
published finance-policy history attached to the retired vertical UUID.  The
activation engine correctly fails closed when no policy exists, but that made
the provider finance step impossible to fund.  Seed a current policy only when
the live Home Services vertical has none; never overwrite a real admin policy.
"""
from __future__ import annotations

import uuid

from alembic import op


revision = "295"
down_revision = "294"
branch_labels = None
depends_on = None

_MARKER = "Restored for live Home Services vertical (migration 295)."


def upgrade() -> None:
    policy_id = str(uuid.uuid4())
    op.execute(
        f"""
        INSERT INTO home_services_activation_finance_policies (
            id, vertical_id, version_number, status, is_current,
            deposit_required, deposit_calculation_mode,
            deposit_amount_per_technician, minimum_deposit,
            technician_count_policy, initial_credit_purchase_required,
            credit_package_base_amount, credit_package_gst_percent,
            credited_wallet_amount, completion_deduction_policy, currency,
            effective_from, change_summary, published_at, created_at, updated_at
        )
        SELECT
            '{policy_id}'::uuid, v.id,
            COALESCE((SELECT MAX(p.version_number) + 1
                      FROM home_services_activation_finance_policies p
                      WHERE p.vertical_id = v.id), 1),
            'published', TRUE,
            TRUE, 'per_technician', 2000.00, 2000.00,
            'home_services_active_technicians_only', TRUE,
            1000.00, 18.000, 1000.00,
            'usage_credit_per_completed_job', 'INR',
            NOW(), '{_MARKER}', NOW(), NOW(), NOW()
        FROM verticals v
        WHERE v.key = 'home_services'
          AND NOT EXISTS (
              SELECT 1 FROM home_services_activation_finance_policies p
              WHERE p.vertical_id = v.id
                AND p.status = 'published'
                AND p.is_current = TRUE
          )
        """
    )


def downgrade() -> None:
    op.execute(
        f"DELETE FROM home_services_activation_finance_policies "
        f"WHERE change_summary = '{_MARKER}'"
    )
