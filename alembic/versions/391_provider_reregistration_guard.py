"""Prevent provider history evasion through repeat registration.

Revision ID: 391
Revises: 390
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "391"
down_revision = "390"
branch_labels = None
depends_on = None


POLICY_KEYS = (
    "provider_reregistration_guard_enabled",
    "provider_reregistration_composite_match_enabled",
)


def upgrade() -> None:
    op.create_table(
        "provider_identity_review_cases",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("registration_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("matched_tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=30), server_default="open", nullable=False),
        sa.Column("match_strength", sa.String(length=20), nullable=False),
        sa.Column("match_signals", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("risk_snapshot", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("decision", sa.String(length=40), nullable=True),
        sa.Column("resolution_note", sa.Text(), nullable=True),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "registration_id", "matched_tenant_id",
            name="uq_provider_identity_review_registration_tenant",
        ),
    )
    op.create_index(
        "ix_pirc_status_created", "provider_identity_review_cases",
        ["status", "created_at"], unique=False,
    )
    op.create_index(
        "ix_pirc_matched_tenant", "provider_identity_review_cases",
        ["matched_tenant_id"], unique=False,
    )
    op.create_index(
        "ix_pirc_registration", "provider_identity_review_cases",
        ["registration_id"], unique=False,
    )

    op.execute("""
        INSERT INTO security_policies
            (id, policy_key, policy_value_json, description, created_at, updated_at)
        VALUES
            (gen_random_uuid(), 'provider_reregistration_guard_enabled', 'true'::jsonb,
             'Pause a provider signup when its legal identity matches an existing provider', now(), now()),
            (gen_random_uuid(), 'provider_reregistration_composite_match_enabled', 'true'::jsonb,
             'Review exact business-name and registered-postcode matches when no tax identifier is available', now(), now())
        ON CONFLICT (policy_key) DO NOTHING
    """)


def downgrade() -> None:
    quoted = ", ".join(f"'{key}'" for key in POLICY_KEYS)
    op.execute(f"DELETE FROM security_policies WHERE policy_key IN ({quoted})")
    op.drop_index("ix_pirc_registration", table_name="provider_identity_review_cases")
    op.drop_index("ix_pirc_matched_tenant", table_name="provider_identity_review_cases")
    op.drop_index("ix_pirc_status_created", table_name="provider_identity_review_cases")
    op.drop_table("provider_identity_review_cases")
