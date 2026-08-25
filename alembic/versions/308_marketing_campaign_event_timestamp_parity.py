"""Align marketing campaign event timestamps with the shared ORM base.

Revision ID: 308
Revises: 307
"""
from alembic import op
import sqlalchemy as sa

revision = "308"
down_revision = "307"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # MarketingCampaignEvent inherits ServiceOSBase/TimestampMixin. Migration
    # 047 created created_at but omitted updated_at, so every ORM insert tried
    # to write a column PostgreSQL did not have and campaign analytics failed.
    op.add_column(
        "marketing_campaign_events",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )


def downgrade() -> None:
    op.drop_column("marketing_campaign_events", "updated_at")
