"""CONFIGURATION-REGISTRY-REBUILD: versioned, scoped configuration values.

Phase 1 audit found `PlatformSetting`/`PlanSetting`/`TenantSetting` already
exist but have no version history or approval workflow -- editing mutates
the row in place. This table adds the draft -> pending_approval ->
scheduled -> active -> superseded/rolled_back lifecycle
(ConfigurationDefinition in registry.py is the code-side definition;
this table is the admin-side value history) without duplicating the
existing PlatformSetting table -- `activate()` writes through to it so the
two already-real consumers (booking_cancellation_window_hours,
dispatch_score_weights) see new values without any change to their own
code.

Revision ID: 187
Revises: 186
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "187"
down_revision = "186"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "configuration_value_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("setting_key", sa.String(200), nullable=False),
        sa.Column("scope_type", sa.String(20), nullable=False, server_default="global"),
        # Never NULL -- Postgres treats every NULL as distinct in a unique
        # index, which would silently defeat ix_cvv_current's "one active
        # row per key+scope" guarantee for global settings. "GLOBAL" is the
        # sentinel for global scope; vertical/environment scope stores the
        # real vertical key / environment name here.
        sa.Column("scope_id", sa.String(80), nullable=False, server_default="GLOBAL"),
        sa.Column("version_number", sa.Integer, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("value", postgresql.JSONB, nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("supersedes_value_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("approved_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("activated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("rolled_back_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("change_reason", sa.Text, nullable=True),
        sa.Column("rollback_reason", sa.Text, nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("setting_key", "scope_type", "scope_id", "version_number", name="uq_cvv_version"),
    )
    op.create_index("ix_cvv_key", "configuration_value_versions", ["setting_key"])
    op.create_index("ix_cvv_scope", "configuration_value_versions", ["scope_type", "scope_id"])
    # One active version per key+scope (NULL scope_id is a valid distinct
    # value for the partial index's purposes since Postgres treats each
    # NULL as distinct in a normal unique index, but this is a *filtered*
    # index keyed on status, so global (scope_id NULL) settings still get
    # correctly enforced to at most one active row).
    op.create_index("ix_cvv_current", "configuration_value_versions",
                     ["setting_key", "scope_type", "scope_id"],
                     unique=True, postgresql_where=sa.text("status = 'active'"))


def downgrade() -> None:
    op.drop_index("ix_cvv_current", table_name="configuration_value_versions")
    op.drop_index("ix_cvv_scope", table_name="configuration_value_versions")
    op.drop_index("ix_cvv_key", table_name="configuration_value_versions")
    op.drop_table("configuration_value_versions")
