"""Add admin-controlled provider departure-warning window.

Revision ID: 381
Revises: 380
"""
from alembic import op
import sqlalchemy as sa


revision = "381"
down_revision = "380"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "vertical_monetization_policies",
        sa.Column(
            "provider_departure_warning_minutes", sa.Integer(),
            nullable=False, server_default=sa.text("15"),
        ),
    )
    op.create_check_constraint(
        "ck_vmp_provider_departure_warning_minutes",
        "vertical_monetization_policies",
        "provider_departure_warning_minutes BETWEEN 5 AND 120",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_vmp_provider_departure_warning_minutes",
        "vertical_monetization_policies", type_="check",
    )
    op.drop_column(
        "vertical_monetization_policies", "provider_departure_warning_minutes",
    )
