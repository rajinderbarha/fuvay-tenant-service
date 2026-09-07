"""Persist supported brands per tenant service type without altering old prices."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "348"
down_revision = "347"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("tenant_service_types", sa.Column("brand_coverage", JSONB(), nullable=True))


def downgrade():
    op.drop_column("tenant_service_types", "brand_coverage")
