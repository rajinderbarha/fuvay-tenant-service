"""Service Blueprint Versions -- the last of the 4 backend contracts
identified missing in the frontend wizard's preflight audit (blueprint
versioning). Purely additive:

  - New `service_blueprint_versions` table: DRAFT/PUBLISHED/SUPERSEDED/
    ARCHIVED lifecycle, a structural snapshot (job_type/requires_type/
    requires_brand/pricing_model/is_active -- no monetary fields), and a
    change_summary for the impact-preview UI.
  - Backfill: one PUBLISHED v1 blueprint version per existing active
    master_service, snapshotting its CURRENT structural config -- this
    establishes a real baseline so future admin edits have something to
    diff against, without guessing at history that was never recorded.
  - Nullable `blueprint_version_id` added to tenant_services and backfilled
    to each tenant's master_service's v1 baseline -- existing tenant setups
    are marked "up to date" against the version that reflects their service's
    actual current structure (safe, since nothing about the structure has
    changed since v1 by construction).

Revision ID: 153
Revises: 152
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "153"
down_revision = "152"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "service_blueprint_versions",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("master_service_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="published"),
        sa.Column("snapshot", sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column("change_summary", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_by_user_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("master_service_id", "version_number", name="uq_sbv_service_version"),
    )
    op.create_index("ix_sbv_master_service", "service_blueprint_versions", ["master_service_id"])
    op.create_index("ix_sbv_status", "service_blueprint_versions", ["status"])

    op.add_column("tenant_services", sa.Column(
        "blueprint_version_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True))

    conn = op.get_bind()
    conn.execute(sa.text("""
        INSERT INTO service_blueprint_versions
            (master_service_id, version_number, status, snapshot, change_summary, published_at)
        SELECT
            id, 1, 'published',
            jsonb_build_object(
                'job_type', job_type, 'requires_type', is_type_required,
                'requires_brand', is_brand_required, 'pricing_model', pricing_model,
                'is_active', is_active
            ),
            'Baseline version, backfilled from current structure at migration time.',
            now()
        FROM master_services
        WHERE deleted_at IS NULL
    """))

    conn.execute(sa.text("""
        UPDATE tenant_services ts SET blueprint_version_id = sbv.id
        FROM service_blueprint_versions sbv
        WHERE sbv.master_service_id = ts.master_service_id AND sbv.version_number = 1
    """))

    op.create_index("ix_ts_blueprint_version", "tenant_services", ["blueprint_version_id"])


def downgrade() -> None:
    op.drop_index("ix_ts_blueprint_version", table_name="tenant_services")
    op.drop_column("tenant_services", "blueprint_version_id")
    op.drop_index("ix_sbv_status", table_name="service_blueprint_versions")
    op.drop_index("ix_sbv_master_service", table_name="service_blueprint_versions")
    op.drop_table("service_blueprint_versions")
