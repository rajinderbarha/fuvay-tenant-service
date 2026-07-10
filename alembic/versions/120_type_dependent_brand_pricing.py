"""Type-Dependent Brand Pricing — scope tenant brand pricing to service type.

Root cause fix: TenantServiceBrand was keyed only by
(tenant_service_id, brand_id) — one price range per brand per service,
shared across every service type. Setting "LG" pricing for Window AC and
then again for Split AC silently overwrote the same row (the API already
threaded service_type_id through to read the admin-approved floor/ceiling
via ServicePricingRule, but had nowhere to store the tenant's own
type-scoped range).

Adds a nullable service_type_id column and widens the unique constraint
to (tenant_service_id, service_type_id, brand_id). NULL service_type_id
is preserved for fixed (non-type-based) services, where brand pricing is
legitimately service-scoped only.

Existing rows (pre-fix, effectively "global brand price across all
types" for type-based services) are NOT migrated/copied per-type
automatically — see scripts/migrate_type_dependent_brand_pricing.py,
which finds and reports them for manual review rather than guessing a
mapping (copying one price to every type would be wrong exactly as often
as it's right).

Revision ID: 120
Revises: 119
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "120"
down_revision = "119"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    tsb_columns = {c["name"] for c in inspector.get_columns("tenant_service_brands")}
    if "service_type_id" not in tsb_columns:
        op.add_column("tenant_service_brands", sa.Column("service_type_id", postgresql.UUID(as_uuid=True), nullable=True))
        op.create_index("ix_tsb_service_type", "tenant_service_brands", ["service_type_id"])

    existing_uniques = {uc["name"] for uc in inspector.get_unique_constraints("tenant_service_brands")}
    if "uq_tsb_service_brand" in existing_uniques:
        op.drop_constraint("uq_tsb_service_brand", "tenant_service_brands", type_="unique")
    if "uq_tsb_service_type_brand" not in existing_uniques:
        op.create_unique_constraint(
            "uq_tsb_service_type_brand", "tenant_service_brands",
            ["tenant_service_id", "service_type_id", "brand_id"],
        )

    # Same gap on the admin side's rule model: ServicePricingRule already
    # has service_type_id + brand_id columns (added in an earlier sprint)
    # but never had a uniqueness guarantee preventing duplicate
    # service+type+brand+tier rules. Add it now.
    spr_uniques = {uc["name"] for uc in inspector.get_unique_constraints("service_pricing_rules")}
    if "uq_spr_service_type_brand_tier" not in spr_uniques:
        op.create_unique_constraint(
            "uq_spr_service_type_brand_tier", "service_pricing_rules",
            ["master_service_id", "service_type_id", "brand_id", "tier_id"],
        )


def downgrade() -> None:
    op.drop_constraint("uq_spr_service_type_brand_tier", "service_pricing_rules", type_="unique")
    op.drop_constraint("uq_tsb_service_type_brand", "tenant_service_brands", type_="unique")
    op.create_unique_constraint("uq_tsb_service_brand", "tenant_service_brands", ["tenant_service_id", "brand_id"])
    op.drop_index("ix_tsb_service_type", "tenant_service_brands")
    op.drop_column("tenant_service_brands", "service_type_id")
