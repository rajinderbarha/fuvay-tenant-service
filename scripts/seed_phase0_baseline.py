"""Phase 0 — Deterministic Home Services baseline seed.

Idempotent — safe to re-run. Seeds:
  - pricing tier "Mid" + Ludhiana/141001 location
  - AC Repair x Split AC x LG x Not Cooling pricing rule (Rs 800)
  - "Starter Home Services" package
  - Demo AC Services tenant (pending, not bookable)
  - tenant_package_assignment (pending, not yet approved/active)
  - Demo Customer address (Ludhiana, 141001)
  - Demo Technician (linked to Demo AC Services tenant)

Run: python scripts/seed_phase0_baseline.py
"""
import asyncio
import os
import sys
import uuid
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://serviceos:serviceos@localhost:5432/serviceos")

NEW_TENANT_SLUG = "demo-ac-services"


async def run():
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        # ── 1. Pricing tier "Mid" ──────────────────────────────────────────
        tier = (await db.execute(text(
            "SELECT id FROM pricing_tiers WHERE code = 'mid'"))).scalar_one_or_none()
        if not tier:
            tier = (await db.execute(text("""
                INSERT INTO pricing_tiers (name, code, tier_type, is_active)
                VALUES ('Mid', 'mid', 'standard', true) RETURNING id
            """))).scalar_one()
            print("[CREATE] pricing_tier: Mid")
        else:
            print("[SKIP]   pricing_tier: Mid (already exists)")

        # ── 2. Location: Ludhiana / 141001 ─────────────────────────────────
        loc = (await db.execute(text(
            "SELECT id FROM tier_locations WHERE zipcode = '141001' AND tier_id = :tid"),
            {"tid": str(tier)})).scalar_one_or_none()
        if not loc:
            await db.execute(text("""
                INSERT INTO tier_locations (tier_id, country, state, district, city, zipcode, is_active)
                VALUES (:tid, 'India', 'Punjab', 'Ludhiana', 'Ludhiana', '141001', true)
            """), {"tid": str(tier)})
            print("[CREATE] tier_location: Ludhiana 141001")
        else:
            print("[SKIP]   tier_location: Ludhiana 141001 (already exists)")

        # ── 3. Resolve AC Repair / Split AC / LG / Not Cooling ─────────────
        ac_repair_id = (await db.execute(text(
            "SELECT id FROM master_services WHERE slug = 'ac_repair'"))).scalar_one_or_none()
        split_ac_id = (await db.execute(text(
            "SELECT id FROM service_types WHERE slug = 'split_ac'"))).scalar_one_or_none()
        lg_id = (await db.execute(text(
            "SELECT id FROM brands WHERE slug = 'lg'"))).scalar_one_or_none()
        if not (ac_repair_id and split_ac_id and lg_id):
            print("[FAIL] AC Repair / Split AC / LG not found — run seed_master_services.py, "
                  "seed_brands.py, seed_ac_repair_baseline_mappings.py first")
            await engine.dispose()
            return

        # ── 4. Pricing rule: AC Repair x Split AC x LG @ Ludhiana 141001 = 800 ──
        existing_rule = (await db.execute(text("""
            SELECT id FROM service_pricing_rules
            WHERE master_service_id = :svc AND service_type_id = :typ AND brand_id = :brand
              AND zipcode = '141001' AND deleted_at IS NULL
        """), {"svc": str(ac_repair_id), "typ": str(split_ac_id), "brand": str(lg_id)})).scalar_one_or_none()
        if not existing_rule:
            await db.execute(text("""
                INSERT INTO service_pricing_rules
                    (master_service_id, service_type_id, brand_id, tier_id, job_type,
                     city, district, state, zipcode, pricing_model,
                     base_price, min_price, max_price, bargain_floor,
                     rule_name, rule_code, priority, is_active, source)
                VALUES
                    (:svc, :typ, :brand, :tier, 'repair',
                     'Ludhiana', 'Ludhiana', 'Punjab', '141001', 'fixed',
                     800, 600, 1200, 650,
                     'AC Repair - Split AC - LG - Ludhiana 141001', 'ac_repair_split_ac_lg_ldh_141001',
                     10, true, 'phase0_baseline_seed')
            """), {"svc": str(ac_repair_id), "typ": str(split_ac_id), "brand": str(lg_id), "tier": str(tier)})
            print("[CREATE] pricing_rule: AC Repair + Split AC + LG @ Ludhiana 141001 = Rs 800")
        else:
            print("[SKIP]   pricing_rule: AC Repair + Split AC + LG @ Ludhiana 141001 (already exists)")

        # ── 5. Package: Starter Home Services ──────────────────────────────
        pkg = (await db.execute(text(
            "SELECT id FROM service_packages WHERE slug = 'starter_home_services'"))).scalar_one_or_none()
        if not pkg:
            pkg = (await db.execute(text("""
                INSERT INTO service_packages
                    (name, slug, package_type, vertical_type, package_price,
                     security_deposit_amount, included_credit_amount, is_active, display_order)
                VALUES
                    ('Starter Home Services', 'starter_home_services', 'subscription', 'home_services',
                     0, 5000, 1000, true, 1)
                RETURNING id
            """))).scalar_one()
            print("[CREATE] package: Starter Home Services (1000 included credits)")
        else:
            print("[SKIP]   package: Starter Home Services (already exists)")

        # ── 6. Demo tenant owner user (reuse existing provider@serviceos.in) ──
        owner = (await db.execute(text(
            "SELECT id FROM users WHERE email = 'provider@serviceos.in'"))).scalar_one_or_none()

        # ── 7. Demo AC Services tenant (pending, not bookable) ─────────────
        tenant = (await db.execute(text(
            "SELECT id, verification_status, status FROM tenants WHERE slug = :slug"),
            {"slug": NEW_TENANT_SLUG})).first()
        if not tenant:
            tenant_id = (await db.execute(text("""
                INSERT INTO tenants
                    (tenant_name, business_name, slug, vertical, status, verification_status,
                     owner_user_id, city, state, country, zipcode, is_discoverable)
                VALUES
                    ('Demo AC Services', 'Demo AC Services', :slug, 'home_services', 'pending_setup',
                     'pending', :owner, 'Ludhiana', 'Punjab', 'India', '141001', false)
                RETURNING id
            """), {"slug": NEW_TENANT_SLUG, "owner": str(owner) if owner else None})).scalar_one()
            print(f"[CREATE] tenant: Demo AC Services (status=pending_setup, verification_status=pending, not bookable)")
        else:
            tenant_id = tenant[0]
            print(f"[SKIP]   tenant: Demo AC Services (already exists, verification_status={tenant[1]})")

        # ── 8. Package assignment — pending, not yet approved/active ───────
        assignment = (await db.execute(text(
            "SELECT id FROM tenant_package_assignments WHERE tenant_id = :tid AND package_id = :pid"),
            {"tid": str(tenant_id), "pid": str(pkg)})).scalar_one_or_none()
        if not assignment:
            await db.execute(text("""
                INSERT INTO tenant_package_assignments
                    (tenant_id, package_id, package_type, status, selected_at,
                     included_spendable_credits, security_deposit_amount)
                VALUES
                    (:tid, :pid, 'subscription', 'pending_approval', now(), 0, 5000)
            """), {"tid": str(tenant_id), "pid": str(pkg)})
            print("[CREATE] tenant_package_assignment: Demo AC Services -> Starter Home Services (pending_approval, 0 credits until approved)")
        else:
            print("[SKIP]   tenant_package_assignment (already exists)")

        # ── 9. Demo customer address (Ludhiana, 141001) ─────────────────────
        customer = (await db.execute(text(
            "SELECT id FROM users WHERE email = 'customer@serviceos.in'"))).scalar_one_or_none()
        if customer:
            addr = (await db.execute(text(
                "SELECT id FROM customer_addresses WHERE customer_id = :cid AND zipcode = '141001'"),
                {"cid": str(customer)})).scalar_one_or_none()
            if not addr:
                await db.execute(text("""
                    INSERT INTO customer_addresses
                        (customer_id, name, address_line_1, city, district, state, country, zipcode, is_default, is_active)
                    VALUES
                        (:cid, 'Demo Customer', 'H.No. 123, Model Town', 'Ludhiana', 'Ludhiana', 'Punjab', 'India', '141001', true, true)
                """), {"cid": str(customer)})
                print("[CREATE] customer_address: Demo Customer @ Ludhiana 141001")
            else:
                print("[SKIP]   customer_address: Demo Customer @ Ludhiana 141001 (already exists)")
        else:
            print("[WARN]   customer@serviceos.in not found — cannot seed address")

        # ── 10. Demo technician — link staff@serviceos.in to Demo AC Services ──
        technician = (await db.execute(text(
            "SELECT id, tenant_id FROM users WHERE email = 'staff@serviceos.in'"))).first()
        if technician:
            if technician[1] != tenant_id:
                await db.execute(text(
                    "UPDATE users SET tenant_id = :tid WHERE id = :uid"),
                    {"tid": str(tenant_id), "uid": str(technician[0])})
                print("[UPDATE] technician staff@serviceos.in linked to Demo AC Services tenant")
            else:
                print("[SKIP]   technician staff@serviceos.in already linked to Demo AC Services")
        else:
            print("[WARN]   staff@serviceos.in not found — cannot link technician")

        await db.commit()
        print("\n[DONE] Phase 0 baseline seed complete.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run())
