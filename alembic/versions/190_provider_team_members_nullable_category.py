"""TEAM-MEMBERS: category_id nullable — staff addable before catalog linkage exists.

`provider_team_members.category_id` was NOT NULL, but nothing populates
`Tenant.category_id` for tenants created through the real self-serve signup
flow, and there is no seeded ServiceCategory row keyed by `Vertical.key`
(e.g. "home_services") to resolve it from either — confirmed live: a fresh
signed-up tenant has no path to a non-null category_id at all. The Staff &
Technicians onboarding step must let a tenant add team members before their
service catalog/category linkage is finalized, so this constraint blocks a
real, intended flow rather than protecting data integrity.

Revision ID: 190
Revises: 189
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "190"
down_revision = "189"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("provider_team_members", "category_id", nullable=True)


def downgrade() -> None:
    op.alter_column("provider_team_members", "category_id", nullable=False)
