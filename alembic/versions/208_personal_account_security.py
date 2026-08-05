"""PERSONAL-ACCOUNT-SECURITY: add recovery-contact fields to users.

Everything else the Account & Security page needs already exists on User/
UserSession/AuthAuditLog/LoginEvent/MFASecret/MFABackupCode/OTPRecord --
this only adds the one genuinely missing field: a recovery contact,
separate from the login email/mobile, used only for account-recovery
purposes (spec section 6B/13).

Revision ID: 208
Revises: 207
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "208"
down_revision = "207"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("recovery_email", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("recovery_phone", sa.String(20), nullable=True))
    op.add_column("users", sa.Column("recovery_contact_verified_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "recovery_contact_verified_at")
    op.drop_column("users", "recovery_phone")
    op.drop_column("users", "recovery_email")
