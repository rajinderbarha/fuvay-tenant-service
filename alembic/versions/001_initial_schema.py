"""Initial schema: extensions + tenant_engines table

Revision ID: 001
Revises:
Create Date: 2024-12-22 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable extensions (idempotent)
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    # ── tenant_engines ─────────────────────────────────────────────
    op.create_table(
        "tenant_engines",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("engine_id", sa.String(50), nullable=False),
        sa.Column("is_enabled", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("config", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deactivated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("activated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
    )
    op.create_unique_constraint("uq_tenant_engine", "tenant_engines", ["tenant_id", "engine_id"])
    op.create_index("ix_tenant_engines_tenant_id", "tenant_engines", ["tenant_id"])
    op.create_index("ix_tenant_engines_engine_id", "tenant_engines", ["engine_id"])

    # ── updated_at trigger ─────────────────────────────────────────
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
        $$ language 'plpgsql';
    """)
    op.execute("""
        CREATE TRIGGER update_tenant_engines_updated_at
        BEFORE UPDATE ON tenant_engines
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS update_tenant_engines_updated_at ON tenant_engines")
    op.drop_table("tenant_engines")
