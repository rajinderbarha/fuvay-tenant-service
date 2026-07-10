"""Add missing updated_at to service_setup_template_versions and service_setup_template_usage."""
import sqlalchemy as sa
from alembic import op

revision = "101"
down_revision = "100"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "service_setup_template_versions",
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=True),
    )
    op.add_column(
        "service_setup_template_usage",
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("service_setup_template_versions", "updated_at")
    op.drop_column("service_setup_template_usage", "updated_at")
