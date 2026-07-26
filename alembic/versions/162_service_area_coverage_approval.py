"""Service-area coverage approval workflow.

Replaces the platform pricing-tier / tier-location city-zipcode mapping
system as the mechanism that gates tenant service coverage. Reuses the
existing serviceability engine's TenantServiceArea / TenantServiceAreaService
tables as the canonical "approved coverage" record rather than creating a
disconnected duplicate coverage engine — only adds the columns needed to
represent approval provenance and lifecycle status on those tables, plus
two new tables for the request/decision workflow itself.

New tables:
  tenant_service_area_requests       -- one request (a "batch" of location asks)
  tenant_service_area_request_items  -- one requested city/zipcode x tenant_service

New columns on tenant_service_areas (existing table):
  category_id            -- vertical scoping (was entirely missing before;
                             a tenant operating in multiple verticals had no
                             way to distinguish which vertical a declared
                             area belonged to)
  status                  -- ACTIVE | SUSPENDED | EXPIRED | REVOKED
                             (kept alongside pre-existing is_active for
                             backward read compatibility; is_active is now
                             derived from status = ACTIVE going forward)
  approved_request_item_id, approved_by, approved_at
  suspended_at, suspended_by, suspension_reason
  effective_from, effective_until

No price column is added anywhere in this migration — coverage and price
remain fully separate per the business-rule requirement that location
approval must never calculate or modify price.

This migration does NOT touch app.engines.admin_catalog.pricing_tiers /
tier_locations at all — those rows are preserved as historical/legacy
data (see the separate reconciliation script), not migrated wholesale
into tenant coverage, because a platform tier-location mapping is not
proof that any specific tenant actually serves that area.

Revision ID: 162
Revises: 161
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision = "162"
down_revision = "161"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── tenant_service_area_requests ────────────────────────────────────
    op.create_table(
        "tenant_service_area_requests",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("category_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="DRAFT"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submitted_by", pg.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by", pg.UUID(as_uuid=True), nullable=True),
        sa.Column("tenant_notes", sa.Text, nullable=True),
        sa.Column("admin_notes", sa.Text, nullable=True),
        sa.Column("superseded_by_request_id", pg.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_tsar_tenant", "tenant_service_area_requests", ["tenant_id"])
    op.create_index("ix_tsar_tenant_category", "tenant_service_area_requests", ["tenant_id", "category_id"])
    op.create_index("ix_tsar_status", "tenant_service_area_requests", ["status"])
    op.create_index("ix_tsar_submitted_at", "tenant_service_area_requests", ["submitted_at"])

    # ── tenant_service_area_request_items ───────────────────────────────
    op.create_table(
        "tenant_service_area_request_items",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("request_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_service_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("master_service_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("job_type_id", pg.UUID(as_uuid=True), nullable=True),
        # applies_to_all_job_types must be an explicit, validated flag --
        # never an implicit "job_type_id is NULL means all" convention.
        sa.Column("applies_to_all_job_types", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("country", sa.String(50), nullable=False, server_default="India"),
        sa.Column("state", sa.String(100), nullable=False),
        sa.Column("district", sa.String(100), nullable=True),
        sa.Column("city", sa.String(100), nullable=False),
        sa.Column("zipcode", sa.String(20), nullable=True),
        sa.Column("requested_effective_date", sa.Date, nullable=True),
        sa.Column("decision_status", sa.String(30), nullable=False, server_default="PENDING"),
        sa.Column("decision_reason", sa.Text, nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by", pg.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["request_id"], ["tenant_service_area_requests.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_tsari_request", "tenant_service_area_request_items", ["request_id"])
    op.create_index("ix_tsari_tenant_service", "tenant_service_area_request_items", ["tenant_service_id"])
    op.create_index("ix_tsari_decision_status", "tenant_service_area_request_items", ["decision_status"])
    op.create_index("ix_tsari_city_zip", "tenant_service_area_request_items", ["city", "zipcode"])

    # ── tenant_service_areas: approval provenance + lifecycle status ───
    op.add_column("tenant_service_areas", sa.Column("category_id", pg.UUID(as_uuid=True), nullable=True))
    op.add_column("tenant_service_areas", sa.Column("status", sa.String(30), nullable=False, server_default="ACTIVE"))
    op.add_column("tenant_service_areas", sa.Column("approved_request_item_id", pg.UUID(as_uuid=True), nullable=True))
    op.add_column("tenant_service_areas", sa.Column("approved_by", pg.UUID(as_uuid=True), nullable=True))
    op.add_column("tenant_service_areas", sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("tenant_service_areas", sa.Column("suspended_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("tenant_service_areas", sa.Column("suspended_by", pg.UUID(as_uuid=True), nullable=True))
    op.add_column("tenant_service_areas", sa.Column("suspension_reason", sa.Text, nullable=True))
    op.add_column("tenant_service_areas", sa.Column("effective_from", sa.DateTime(timezone=True), nullable=True))
    op.add_column("tenant_service_areas", sa.Column("effective_until", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_tsa_category", "tenant_service_areas", ["category_id"])
    op.create_index("ix_tsa_status", "tenant_service_areas", ["status"])
    op.create_index("ix_tsa_tenant_category_status", "tenant_service_areas", ["tenant_id", "category_id", "status"])

    # Backfill: every pre-existing row was created via the old direct
    # self-service path with no request behind it -- mark status from the
    # existing is_active boolean (ACTIVE if active, REVOKED if not) so
    # matching queries that switch to filtering on `status` see identical
    # results to what `is_active` produced before this migration.
    op.execute("UPDATE tenant_service_areas SET status = 'ACTIVE' WHERE is_active = true")
    op.execute("UPDATE tenant_service_areas SET status = 'REVOKED' WHERE is_active = false")

    # ── tenant_service_area_services: lifecycle status only, no price change ─
    op.add_column("tenant_service_area_services", sa.Column("status", sa.String(30), nullable=False, server_default="ACTIVE"))
    op.execute("UPDATE tenant_service_area_services SET status = 'ACTIVE' WHERE is_available = true")
    op.execute("UPDATE tenant_service_area_services SET status = 'REVOKED' WHERE is_available = false")
    op.create_index("ix_tsas_status", "tenant_service_area_services", ["status"])


def downgrade() -> None:
    op.drop_index("ix_tsas_status", table_name="tenant_service_area_services")
    op.drop_column("tenant_service_area_services", "status")

    op.drop_index("ix_tsa_tenant_category_status", table_name="tenant_service_areas")
    op.drop_index("ix_tsa_status", table_name="tenant_service_areas")
    op.drop_index("ix_tsa_category", table_name="tenant_service_areas")
    op.drop_column("tenant_service_areas", "effective_until")
    op.drop_column("tenant_service_areas", "effective_from")
    op.drop_column("tenant_service_areas", "suspension_reason")
    op.drop_column("tenant_service_areas", "suspended_by")
    op.drop_column("tenant_service_areas", "suspended_at")
    op.drop_column("tenant_service_areas", "approved_at")
    op.drop_column("tenant_service_areas", "approved_by")
    op.drop_column("tenant_service_areas", "approved_request_item_id")
    op.drop_column("tenant_service_areas", "status")
    op.drop_column("tenant_service_areas", "category_id")

    op.drop_index("ix_tsari_city_zip", table_name="tenant_service_area_request_items")
    op.drop_index("ix_tsari_decision_status", table_name="tenant_service_area_request_items")
    op.drop_index("ix_tsari_tenant_service", table_name="tenant_service_area_request_items")
    op.drop_index("ix_tsari_request", table_name="tenant_service_area_request_items")
    op.drop_table("tenant_service_area_request_items")

    op.drop_index("ix_tsar_submitted_at", table_name="tenant_service_area_requests")
    op.drop_index("ix_tsar_status", table_name="tenant_service_area_requests")
    op.drop_index("ix_tsar_tenant_category", table_name="tenant_service_area_requests")
    op.drop_index("ix_tsar_tenant", table_name="tenant_service_area_requests")
    op.drop_table("tenant_service_area_requests")
