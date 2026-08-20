"""Scope tenant offerings by master service and job type.

Revision ID: 260
Revises: 259
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "260"
down_revision = "259"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # A small number of old drafts were created after MasterService became
    # multi-job-type but before enablement accepted job_type_id. If another
    # tenant already has exactly one canonical job type for the same master,
    # use that observed offering scope (not name/label guessing).
    op.execute("""
        UPDATE tenant_services target SET job_type_id = resolved.job_type_id,
            job_type = resolved.job_type_key
        FROM (
            SELECT existing.master_service_id, min(existing.job_type_id::text)::uuid AS job_type_id,
                   min(jt.key) AS job_type_key
            FROM tenant_services existing
            JOIN job_types jt ON jt.id = existing.job_type_id
            WHERE existing.job_type_id IS NOT NULL
            GROUP BY existing.master_service_id
            HAVING count(DISTINCT existing.job_type_id) = 1
        ) resolved
        WHERE target.job_type_id IS NULL
          AND target.master_service_id = resolved.master_service_id
    """)
    # Otherwise a single active child is itself unambiguous.
    op.execute("""
        UPDATE tenant_services target SET job_type_id = resolved.job_type_id,
            job_type = resolved.job_type_key
        FROM (
            SELECT msjt.master_service_id, min(msjt.job_type_id::text)::uuid AS job_type_id,
                   min(jt.key) AS job_type_key
            FROM master_service_job_types msjt
            JOIN job_types jt ON jt.id = msjt.job_type_id
            WHERE msjt.is_active AND jt.is_active
            GROUP BY msjt.master_service_id
            HAVING count(*) = 1
        ) resolved
        WHERE target.job_type_id IS NULL
          AND target.master_service_id = resolved.master_service_id
    """)
    unresolved = op.get_bind().execute(sa.text(
        "SELECT count(*) FROM tenant_services WHERE job_type_id IS NULL"
    )).scalar() or 0
    if unresolved:
        raise RuntimeError(
            f"Cannot normalize tenant offerings: {unresolved} rows have no canonical job_type_id."
        )
    op.drop_constraint("uq_ts_tenant_service", "tenant_services", type_="unique")
    op.alter_column(
        "tenant_services", "job_type_id",
        existing_type=sa.dialects.postgresql.UUID(as_uuid=True), nullable=False,
    )
    op.create_unique_constraint(
        "uq_ts_tenant_service_job_type", "tenant_services",
        ["tenant_id", "master_service_id", "job_type_id"],
    )


def downgrade() -> None:
    duplicates = op.get_bind().execute(sa.text("""
        SELECT count(*) FROM (
            SELECT tenant_id, master_service_id FROM tenant_services
            GROUP BY tenant_id, master_service_id HAVING count(*) > 1
        ) duplicated
    """)).scalar() or 0
    if duplicates:
        raise RuntimeError("Cannot restore service-only uniqueness while per-job-type tenant offerings exist.")
    op.drop_constraint("uq_ts_tenant_service_job_type", "tenant_services", type_="unique")
    op.alter_column(
        "tenant_services", "job_type_id",
        existing_type=sa.dialects.postgresql.UUID(as_uuid=True), nullable=True,
    )
    op.create_unique_constraint(
        "uq_ts_tenant_service", "tenant_services", ["tenant_id", "master_service_id"],
    )
