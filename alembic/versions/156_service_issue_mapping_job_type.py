"""Job-type scoping for service-issue mappings -- closes the last real gap
found in the Admin Catalog page's Problems & Questions preflight audit.

MasterIssueType/ServiceIssueMapping (Sprint 34C/34E) already provide a full,
real admin CRUD surface (create/list/get/update/activate/deactivate/archive
+ mapping CRUD with photo/description requirements, display order, audit
trail) -- confirmed live, not rebuilt here. The one thing missing versus the
approved mockup is that Problems are shown scoped to a job-type tab ("Repair"
/ "Installation" / ...), and the mapping had no job_type_id to scope by.

This mirrors the identical nullable job_type_id pattern already used on
catalog_questions (migration 155): NULL means "applies to all job types for
this service" (backward compatible with every existing row), a concrete FK
scopes the problem to one job type only.

Purely additive.

Revision ID: 156
Revises: 155
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "156"
down_revision = "155"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "service_issue_mappings",
        sa.Column("job_type_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_sim_job_type", "service_issue_mappings", ["job_type_id"])


def downgrade() -> None:
    op.drop_index("ix_sim_job_type", table_name="service_issue_mappings")
    op.drop_column("service_issue_mappings", "job_type_id")
