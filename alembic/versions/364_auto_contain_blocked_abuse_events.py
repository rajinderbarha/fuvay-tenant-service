"""Classify successfully blocked abuse events as contained.

Revision ID: 364
Revises: 363
"""
from alembic import op


revision = "364"
down_revision = "363"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # These records document requests that the abuse guard already denied.
    # Preserve every immutable signal while correcting its incident lifecycle:
    # it is contained automatically, not waiting for administrator action.
    op.execute("""
        UPDATE suspicious_activity_logs
        SET status = 'contained',
            context = COALESCE(context, '{}'::jsonb) || jsonb_build_object(
                'enforcement_result', 'blocked',
                'containment', 'automatic'
            )
        WHERE status = 'open'
          AND auto_actioned = true
          AND source = 'abuse_guard'
          AND description LIKE '% was blocked by an abuse-control threshold'
    """)


def downgrade() -> None:
    op.execute("""
        UPDATE suspicious_activity_logs
        SET status = 'open',
            context = COALESCE(context, '{}'::jsonb)
                - 'enforcement_result' - 'containment'
        WHERE status = 'contained'
          AND auto_actioned = true
          AND source = 'abuse_guard'
          AND context->>'enforcement_result' = 'blocked'
          AND context->>'containment' = 'automatic'
    """)
