"""Frontend-wizard backend contract, batch 1: coverage modes + minimal
draft-resume pointer on tenant_services. Closes 2 of the 4 missing contracts
found in the frontend wizard's preflight audit (coverage modes ALL/SELECTED/
ALL_EXCEPT, and draft save/resume). Blueprint versioning remains deferred
(existing services aren't versioned today either -- a bigger, separate
decision). Publish-field-level-validation is added in the same phase via
service-layer code only (no schema change needed).

Purely additive: two new coverage-mode columns default to "selected", which
is byte-for-byte the existing behavior (tenant explicitly enables each
TenantServiceType/TenantServiceBrand row) -- no existing tenant's setup
changes meaning.

Revision ID: 152
Revises: 151
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "152"
down_revision = "151"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tenant_services", sa.Column(
        "type_coverage_mode", sa.String(20), nullable=False, server_default="selected"))
    op.add_column("tenant_services", sa.Column(
        "brand_coverage_mode", sa.String(20), nullable=False, server_default="selected"))
    op.add_column("tenant_services", sa.Column(
        "last_active_step", sa.String(30), nullable=True))


def downgrade() -> None:
    op.drop_column("tenant_services", "last_active_step")
    op.drop_column("tenant_services", "brand_coverage_mode")
    op.drop_column("tenant_services", "type_coverage_mode")
