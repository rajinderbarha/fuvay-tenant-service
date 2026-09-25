"""Make Instagram arrival and stall escalation controls configurable.

Revision ID: 379
Revises: 378
"""
from alembic import op
import sqlalchemy as sa


revision = "379"
down_revision = "378"
branch_labels = None
depends_on = None


def upgrade() -> None:
    table = "vertical_monetization_policies"
    op.add_column(table, sa.Column(
        "arrival_customer_confirmation_enabled", sa.Boolean(), nullable=False,
        server_default=sa.text("true"),
    ))
    op.add_column(table, sa.Column(
        "arrival_challenge_ttl_minutes", sa.Integer(), nullable=False,
        server_default=sa.text("10"),
    ))
    op.add_column(table, sa.Column(
        "arrival_code_max_attempts", sa.Integer(), nullable=False,
        server_default=sa.text("5"),
    ))
    op.add_column(table, sa.Column(
        "arrival_denial_limit", sa.Integer(), nullable=False,
        server_default=sa.text("2"),
    ))
    op.add_column(table, sa.Column(
        "job_stall_critical_multiplier", sa.Integer(), nullable=False,
        server_default=sa.text("2"),
    ))
    op.create_check_constraint(
        "ck_vmp_arrival_challenge_ttl", table,
        "arrival_challenge_ttl_minutes BETWEEN 1 AND 60",
    )
    op.create_check_constraint(
        "ck_vmp_arrival_code_attempts", table,
        "arrival_code_max_attempts BETWEEN 1 AND 20",
    )
    op.create_check_constraint(
        "ck_vmp_arrival_denial_limit", table,
        "arrival_denial_limit BETWEEN 1 AND 10",
    )
    op.create_check_constraint(
        "ck_vmp_stall_critical_multiplier", table,
        "job_stall_critical_multiplier BETWEEN 1 AND 10",
    )


def downgrade() -> None:
    table = "vertical_monetization_policies"
    for constraint in (
        "ck_vmp_stall_critical_multiplier",
        "ck_vmp_arrival_denial_limit",
        "ck_vmp_arrival_code_attempts",
        "ck_vmp_arrival_challenge_ttl",
    ):
        op.drop_constraint(constraint, table, type_="check")
    for column in (
        "job_stall_critical_multiplier",
        "arrival_denial_limit",
        "arrival_code_max_attempts",
        "arrival_challenge_ttl_minutes",
        "arrival_customer_confirmation_enabled",
    ):
        op.drop_column(table, column)
