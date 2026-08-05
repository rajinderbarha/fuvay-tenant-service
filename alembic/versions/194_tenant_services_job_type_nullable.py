"""TENANT-SERVICES-JOB-TYPE-NULLABLE: master_services moved to a multi
job-type model (master_service_job_types M:N + job_type_id) and modern rows
carry job_type=NULL (is_type_required=True, no single scalar job type).
tenant_services.job_type is still NOT NULL, so TenantCatalogService.enable_service
(app/engines/admin_catalog/tenant_service.py) 500s on every master service that
uses the newer model -- a genuine, universally-blocking bug for Services &
Pricing onboarding. Column becomes nullable; job_type_id (already nullable)
is the canonical field for these services.

Revision ID: 194
Revises: 193
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "194"
down_revision = "193"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("tenant_services", "job_type", existing_type=sa.String(length=20), nullable=True)


def downgrade() -> None:
    op.execute("UPDATE tenant_services SET job_type = '' WHERE job_type IS NULL")
    op.alter_column("tenant_services", "job_type", existing_type=sa.String(length=20), nullable=False)
