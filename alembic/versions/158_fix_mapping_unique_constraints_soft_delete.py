"""Fix: uq_sim_service_issue and uq_som_service_option were plain (not
partial) unique constraints, but both service_issue_mappings and
service_option_mappings use soft delete (deleted_at). Found live while
verifying migration 156/157: after removing a Problem mapping (DELETE sets
deleted_at, row stays), re-adding the SAME issue type to the SAME service
always failed with asyncpg.UniqueViolationError -- the app-level duplicate
check in add_service_issue_mapping/add_service_option_mapping correctly
filters deleted_at IS NULL and reports "not a duplicate", but the flat DB
constraint still blocked the insert. Net effect: any admin who removed a
Problem or Service Option from a service could never re-add it. Presumably
broken since Sprint 34E shipped, exposed now by migration 156's live test.

Fix: replace both flat UniqueConstraints with partial unique indexes scoped
to WHERE deleted_at IS NULL -- the standard pattern for unique + soft delete.

Revision ID: 158
Revises: 157
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "158"
down_revision = "157"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("uq_sim_service_issue", "service_issue_mappings", type_="unique")
    op.create_index(
        "uq_sim_service_issue_active", "service_issue_mappings",
        ["master_service_id", "issue_type_id"],
        unique=True, postgresql_where=sa.text("deleted_at IS NULL"),
    )

    op.drop_constraint("uq_som_service_option", "service_option_mappings", type_="unique")
    op.create_index(
        "uq_som_service_option_active", "service_option_mappings",
        ["master_service_id", "service_option_id"],
        unique=True, postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_som_service_option_active", table_name="service_option_mappings")
    op.create_unique_constraint("uq_som_service_option", "service_option_mappings",
                                ["master_service_id", "service_option_id"])

    op.drop_index("uq_sim_service_issue_active", table_name="service_issue_mappings")
    op.create_unique_constraint("uq_sim_service_issue", "service_issue_mappings",
                                ["master_service_id", "issue_type_id"])
