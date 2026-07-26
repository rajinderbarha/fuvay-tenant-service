"""Fix: master_data_audit_log.action was VARCHAR(30) but several action
strings already written by service_option_service.py exceed 30 chars
("issue_type.unmapped_from_service" = 33, "service_option.unmapped_from_service"
= 37). Found live while verifying migration 156 (job-type scoping on
service-issue mappings): DELETE /v1/admin/master-services/{id}/issues/{mapping_id}
500'd with asyncpg.StringDataRightTruncationError on every call, because the
audit-log insert inside remove_service_issue_mapping() failed before the
delete could commit. The identical bug hits remove_service_option_mapping()
via "service_option.unmapped_from_service". This has presumably been broken
since Sprint 34E shipped, not introduced by 156.

Widened to VARCHAR(60) to match entity_type's existing width and give
headroom for future dotted action names.

Revision ID: 157
Revises: 156
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "157"
down_revision = "156"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("master_data_audit_log", "action",
                     type_=sa.String(60), existing_type=sa.String(30), nullable=False)


def downgrade() -> None:
    op.alter_column("master_data_audit_log", "action",
                     type_=sa.String(30), existing_type=sa.String(60), nullable=False)
