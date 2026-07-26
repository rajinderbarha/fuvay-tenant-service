"""Fix: uq_som_service_option_active (migration 158) did not include the new
job_type_id column added in migration 169, so mapping the SAME option to two
different Job Types under the same service (e.g. Installation AND Repair --
the whole point of this ownership correction) hit
asyncpg.UniqueViolationError. Found live while testing migration 169's
job-type-isolation behavior.

Fix: replace the partial unique index with one scoped to
(master_service_id, service_option_id, job_type_id) WHERE deleted_at IS NULL.
Postgres treats NULL as distinct in a unique index, so this also still allows
at most one NULL-job_type_id (legacy/unscoped) mapping per service+option,
matching the existing app-level duplicate check.

Revision ID: 170
Revises: 169
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "170"
down_revision = "169"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("uq_som_service_option_active", table_name="service_option_mappings")
    op.create_index(
        "uq_som_service_option_job_type_active", "service_option_mappings",
        ["master_service_id", "service_option_id", "job_type_id"],
        unique=True, postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_som_service_option_job_type_active", table_name="service_option_mappings")
    op.create_index(
        "uq_som_service_option_active", "service_option_mappings",
        ["master_service_id", "service_option_id"],
        unique=True, postgresql_where=sa.text("deleted_at IS NULL"),
    )
