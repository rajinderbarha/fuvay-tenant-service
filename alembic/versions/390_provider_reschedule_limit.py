"""Govern provider-initiated reschedules independently from customers.

Revision ID: 390
Revises: 389
"""
from alembic import op
import sqlalchemy as sa


revision = "390"
down_revision = "389"
branch_labels = None
depends_on = None


def upgrade() -> None:
    table = "vertical_monetization_policies"
    op.add_column(
        table,
        sa.Column(
            "provider_reschedule_limit",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("3"),
        ),
    )
    op.create_check_constraint(
        "ck_vmp_provider_reschedule_limit",
        table,
        "provider_reschedule_limit BETWEEN 0 AND 20",
    )


def downgrade() -> None:
    table = "vertical_monetization_policies"
    op.drop_constraint(
        "ck_vmp_provider_reschedule_limit", table, type_="check",
    )
    op.drop_column(table, "provider_reschedule_limit")
