"""Type-Dependent Brand Pricing — old global-brand-rule detection script.

Finds old admin ServicePricingRule rows and tenant TenantServiceBrand rows
that priced a brand globally across all types for a type-based service
(exactly the wrong-scope pattern this fix corrects). Does NOT blindly copy
the global price to every type — that would be wrong exactly as often as
right — it reports affected rows for manual review instead.

Usage:
    python scripts/migrate_type_dependent_brand_pricing.py --dry-run
    python scripts/migrate_type_dependent_brand_pricing.py --apply

--apply marks affected rows as deprecated (is_active=False for admin
rules; a manual_review flag is not a real column on TenantServiceBrand,
so tenant-side rows are only reported, never auto-modified — the tenant
must re-set brand pricing per type via the setup wizard).
"""
import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text
from app.database import create_engine as get_engine


async def run(apply: bool) -> None:
    engine = get_engine()

    # 1. Admin-side: ServicePricingRule rows with brand_id set, service_type_id
    #    NULL, for a master_service that IS type-based (has other rules with
    #    service_type_id set) — i.e. genuinely type-based services with a
    #    leftover global brand rule.
    async with engine.begin() as conn:
        result = await conn.execute(text("""
            SELECT spr.id, spr.master_service_id, spr.brand_id, spr.min_price, spr.max_price
            FROM service_pricing_rules spr
            WHERE spr.brand_id IS NOT NULL
              AND spr.service_type_id IS NULL
              AND spr.deleted_at IS NULL
              AND spr.is_active = true
              AND EXISTS (
                  SELECT 1 FROM service_pricing_rules spr2
                  WHERE spr2.master_service_id = spr.master_service_id
                    AND spr2.service_type_id IS NOT NULL
              )
        """))
        old_admin_rules = result.fetchall()

        print(f"[{'APPLY' if apply else 'DRY-RUN'}] old global admin brand rules found: {len(old_admin_rules)}")
        affected_services = set()
        affected_brands = set()
        for row in old_admin_rules:
            affected_services.add(str(row.master_service_id))
            affected_brands.add(str(row.brand_id))
            print(f"  - rule {row.id}: master_service={row.master_service_id} brand={row.brand_id} "
                  f"range=Rs.{row.min_price}-{row.max_price} -> recommend: deprecate, "
                  f"admin must create per-type replacements")

        print(f"  affected services: {len(affected_services)}")
        print(f"  affected brands: {len(affected_brands)}")

        if apply and old_admin_rules:
            ids = [str(r.id) for r in old_admin_rules]
            await conn.execute(
                text("UPDATE service_pricing_rules SET is_active = false WHERE id = ANY(:ids)"),
                {"ids": ids},
            )
            print(f"  -> marked {len(ids)} admin rule(s) inactive (manual_review — admin must recreate per-type)")

    # 2. Tenant-side: TenantServiceBrand rows with service_type_id NULL and a
    #    non-null price, for a tenant_service that requires_type=true.
    async with engine.begin() as conn:
        result = await conn.execute(text("""
            SELECT tsb.id, tsb.tenant_service_id, tsb.brand_id, tsb.tenant_min_price, tsb.tenant_max_price
            FROM tenant_service_brands tsb
            JOIN tenant_services ts ON ts.id = tsb.tenant_service_id
            WHERE tsb.service_type_id IS NULL
              AND tsb.tenant_min_price IS NOT NULL
              AND ts.requires_type = true
        """))
        old_tenant_rows = result.fetchall()

        print(f"\n[{'APPLY' if apply else 'DRY-RUN'}] old global tenant brand price rows found: {len(old_tenant_rows)}")
        for row in old_tenant_rows:
            print(f"  - tenant_service_brand {row.id}: tenant_service={row.tenant_service_id} "
                  f"brand={row.brand_id} range=Rs.{row.tenant_min_price}-{row.tenant_max_price} "
                  f"-> recommend: manual_review, provider must re-set price per type via the setup wizard")

        if apply and old_tenant_rows:
            # Clear the price (not the row/enablement flag) so the setup
            # wizard shows this brand as "needs pricing" per type again,
            # rather than silently deleting the tenant's brand selection.
            ids = [str(r.id) for r in old_tenant_rows]
            await conn.execute(
                text("UPDATE tenant_service_brands SET tenant_min_price = NULL, tenant_max_price = NULL WHERE id = ANY(:ids)"),
                {"ids": ids},
            )
            print(f"  -> cleared price on {len(ids)} row(s); provider must re-set price per type")

    if not apply:
        print("\nDry run only — no changes made. Re-run with --apply to mark/clear affected rows.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--dry-run", action="store_true", help="Report only (default)")
    group.add_argument("--apply", action="store_true", help="Deprecate/clear affected rows")
    args = parser.parse_args()

    asyncio.run(run(apply=args.apply))


if __name__ == "__main__":
    main()
