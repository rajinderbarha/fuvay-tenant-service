"""TENANT-ONBOARDING-DECLARATIONS: mandatory Review & Submit declarations
(accuracy confirmation, submitter authorization, Terms/Privacy agreement)
for the Home Services onboarding "Review & submit" step (step 8 of 8).

One row per (tenant, vertical, declaration_key, document_version) so a later
Terms/Privacy version bump requires a fresh acceptance rather than silently
reusing consent given to a materially different policy version.

Revision ID: 192
Revises: 191
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "192"
down_revision = "191"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tenant_onboarding_declarations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vertical_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("declaration_key", sa.String(60), nullable=False),
        sa.Column("document_version", sa.String(40), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.UniqueConstraint("tenant_id", "vertical_id", "declaration_key", "document_version",
                             name="uq_tod_tenant_vertical_key_version"),
    )
    op.create_index("ix_tod_tenant_vertical", "tenant_onboarding_declarations", ["tenant_id", "vertical_id"])


def downgrade() -> None:
    op.drop_index("ix_tod_tenant_vertical", table_name="tenant_onboarding_declarations")
    op.drop_table("tenant_onboarding_declarations")
