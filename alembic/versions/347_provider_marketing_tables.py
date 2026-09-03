"""Create the provider marketing campaign/asset tables the router has always assumed.

/v1/provider/marketing/{status,campaigns,assets} (Sprint 13/29) query
provider_marketing_campaigns and provider_marketing_assets by raw SQL, but no
migration ever created either table -- so every one of those endpoints raised
UndefinedTableError and returned 500, which surfaced in the tenant portal as a
CORS failure on /provider/marketing (the error response carries no CORS
headers). Columns here match exactly what the router selects, inserts and
updates.

Revision ID: 347
Revises: 346
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = "347"
down_revision = "346"
branch_labels = None
depends_on = None


def upgrade() -> None:
    existing = set(sa.inspect(op.get_bind()).get_table_names())

    if "provider_marketing_campaigns" not in existing:
        op.create_table(
            "provider_marketing_campaigns",
            sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
            sa.Column("campaign_key", sa.String(120), nullable=False),
            sa.Column("campaign_name", sa.String(200), nullable=False),
            sa.Column("campaign_type", sa.String(60), nullable=False, server_default="launch"),
            sa.Column("status", sa.String(40), nullable=False, server_default="draft"),
            sa.Column("marketing_ready", sa.Boolean, nullable=False, server_default=sa.text("false")),
            sa.Column("provider_review_status", sa.String(40), nullable=True),
            sa.Column("admin_review_status", sa.String(40), nullable=True),
            sa.Column("rejection_reason", sa.Text, nullable=True),
            sa.Column("requested_changes", sa.Text, nullable=True),
            sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            # generate-launch inserts ON CONFLICT DO NOTHING keyed on the
            # per-tenant campaign_key it builds, so that pair must be unique.
            sa.UniqueConstraint("tenant_id", "campaign_key", name="uq_pmc_tenant_key"),
        )
        op.create_index("ix_pmc_tenant", "provider_marketing_campaigns", ["tenant_id"])
        op.create_index("ix_pmc_status", "provider_marketing_campaigns", ["status"])
        op.create_index("ix_pmc_created", "provider_marketing_campaigns", ["created_at"])

    if "provider_marketing_assets" not in existing:
        op.create_table(
            "provider_marketing_assets",
            sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
            sa.Column("campaign_id", UUID(as_uuid=True),
                      sa.ForeignKey("provider_marketing_campaigns.id", ondelete="CASCADE"), nullable=True),
            sa.Column("asset_type", sa.String(60), nullable=False),
            sa.Column("channel", sa.String(60), nullable=True),
            sa.Column("language", sa.String(10), nullable=False, server_default="en"),
            sa.Column("title", sa.String(300), nullable=True),
            sa.Column("body", sa.Text, nullable=True),
            sa.Column("image_url", sa.Text, nullable=True),
            sa.Column("generation_source", sa.String(40), nullable=False, server_default="template"),
            sa.Column("status", sa.String(40), nullable=False, server_default="draft"),
            sa.Column("provider_notes", sa.Text, nullable=True),
            sa.Column("admin_notes", sa.Text, nullable=True),
            sa.Column("rejection_reason", sa.Text, nullable=True),
            sa.Column("publish_url", sa.Text, nullable=True),
            sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        )
        op.create_index("ix_pma_tenant", "provider_marketing_assets", ["tenant_id"])
        op.create_index("ix_pma_campaign", "provider_marketing_assets", ["campaign_id"])
        op.create_index("ix_pma_created", "provider_marketing_assets", ["created_at"])


def downgrade() -> None:
    existing = set(sa.inspect(op.get_bind()).get_table_names())
    for table in ("provider_marketing_assets", "provider_marketing_campaigns"):
        if table in existing:
            op.drop_table(table)
