"""Generic catalog dimension engine -- the largest gap found in the Admin
Catalog page's preflight audit. Today Type and Brand are hardcoded tables
(service_types / brands) with no way to add a future dimension (Capacity,
Size, Model, Delivery Mode, Property Type) through configuration. This adds
a generic, admin-configurable dimension model:

  - catalog_dimensions: a dimension DEFINITION (key/name/data_type). Seeded
    with the two that exist implicitly today ("type", "brand") so the new
    generic UI can render them uniformly alongside future dimensions.
  - catalog_dimension_values: allowed values for a dimension (code/label/
    metadata/display_order). NOT backfilled from service_types/brands --
    those remain the canonical source for Type/Brand values for now (this
    engine's values table is for NEW generic dimensions); the two seeded
    definitions carry a `legacy_source` marker so the UI knows to read
    Type/Brand values from their existing endpoints.
  - service_job_dimensions: the per-(master_service, job_type) structural
    blueprint config for a dimension -- enabled/required/ask_customer/
    show_during_tenant_setup/use_for_matching/affects_price/allow_tenant_
    override + the three coverage-mode allow flags + display_order. This is
    exactly the "Dimensions tab" grid from the approved mockup. NO monetary
    columns (structure only, per the admin-never-sets-price rule).

Purely additive. Existing service_types/brands/mappings and all tenant
pricing are untouched.

Revision ID: 154
Revises: 153
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "154"
down_revision = "153"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "catalog_dimensions",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("key", sa.String(40), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        # single_select / multi_select / boolean / number / text
        sa.Column("data_type", sa.String(20), nullable=False, server_default="single_select"),
        # For "type"/"brand", values live in the existing service_types/brands
        # tables -- this marks that so the UI reads them from there.
        sa.Column("legacy_source", sa.String(30), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("key", name="uq_catalog_dimensions_key"),
    )
    op.create_index("ix_catalog_dimensions_active", "catalog_dimensions", ["is_active"])

    op.create_table(
        "catalog_dimension_values",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("dimension_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(60), nullable=False),
        sa.Column("label", sa.String(160), nullable=False),
        sa.Column("metadata", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("dimension_id", "code", name="uq_cdv_dimension_code"),
    )
    op.create_index("ix_cdv_dimension", "catalog_dimension_values", ["dimension_id"])

    op.create_table(
        "service_job_dimensions",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("master_service_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_type_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("dimension_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("ask_customer", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("show_during_tenant_setup", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("use_for_matching", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("affects_price", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("allow_tenant_override", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("allow_all_coverage", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("allow_selected_coverage", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("allow_exclusion_coverage", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("master_service_id", "job_type_id", "dimension_id", name="uq_sjd_service_job_dim"),
    )
    op.create_index("ix_sjd_master_service", "service_job_dimensions", ["master_service_id"])
    op.create_index("ix_sjd_job_type", "service_job_dimensions", ["job_type_id"])

    # Seed the two dimensions that exist implicitly today.
    conn = op.get_bind()
    for key, name, order, legacy in [("type", "Type", 1, "service_types"), ("brand", "Brand", 2, "brands")]:
        conn.execute(sa.text("""
            INSERT INTO catalog_dimensions (key, name, data_type, legacy_source, display_order)
            VALUES (:key, :name, 'single_select', :legacy, :order)
        """), {"key": key, "name": name, "legacy": legacy, "order": order})


def downgrade() -> None:
    op.drop_index("ix_sjd_job_type", table_name="service_job_dimensions")
    op.drop_index("ix_sjd_master_service", table_name="service_job_dimensions")
    op.drop_table("service_job_dimensions")
    op.drop_index("ix_cdv_dimension", table_name="catalog_dimension_values")
    op.drop_table("catalog_dimension_values")
    op.drop_index("ix_catalog_dimensions_active", table_name="catalog_dimensions")
    op.drop_table("catalog_dimensions")
