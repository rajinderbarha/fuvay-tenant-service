"""070 — Add signup/public fields to service_packages.

Adds: vertical_type, is_public_signup_visible, is_popular, billing_cycle
to the service_packages table so the public signup API can filter
and display packages per vertical without hardcoded data.

Revision ID: 070
Revises: 069
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "070"
down_revision = "069"
branch_labels = None
depends_on = None


def _col_exists(table: str, column: str) -> bool:
    from alembic import op as _op
    bind = _op.get_bind()
    res = bind.execute(sa.text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name=:t AND column_name=:c"
    ), {"t": table, "c": column})
    return res.fetchone() is not None


def upgrade() -> None:
    if not _col_exists("service_packages", "vertical_type"):
        op.add_column("service_packages",
            sa.Column("vertical_type", sa.String(50), nullable=True))

    if not _col_exists("service_packages", "is_public_signup_visible"):
        op.add_column("service_packages",
            sa.Column("is_public_signup_visible", sa.Boolean(),
                      nullable=False, server_default="false"))

    if not _col_exists("service_packages", "is_popular"):
        op.add_column("service_packages",
            sa.Column("is_popular", sa.Boolean(),
                      nullable=False, server_default="false"))

    if not _col_exists("service_packages", "billing_cycle"):
        op.add_column("service_packages",
            sa.Column("billing_cycle", sa.String(30), nullable=True))

    if not _col_exists("service_packages", "currency"):
        op.add_column("service_packages",
            sa.Column("currency", sa.String(10),
                      nullable=False, server_default="INR"))

    # Index for fast signup package lookup
    try:
        op.create_index(
            "ix_spkg_vertical_type", "service_packages", ["vertical_type"]
        )
    except Exception:
        pass
    try:
        op.create_index(
            "ix_spkg_public_signup", "service_packages",
            ["is_public_signup_visible", "is_active"]
        )
    except Exception:
        pass


def downgrade() -> None:
    for col in ["currency", "billing_cycle", "is_popular",
                "is_public_signup_visible", "vertical_type"]:
        try:
            op.drop_column("service_packages", col)
        except Exception:
            pass
