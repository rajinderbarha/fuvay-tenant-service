"""Seed AC type + brand catalog data and switch both dimensions on.

The Job-Type Blueprint already models "ask the customer for a type, then a
brand" — `catalog_dimensions` ships with `type` (order 1) and `brand`
(order 2). Nothing was ever configured behind them, so the chat flow had
nothing to ask and went straight to the problem question.

Both dimensions are `legacy_source`-backed, so their values live in the
`service_types` / `brands` libraries rather than `catalog_dimension_values`
(`DimensionService.add_value` refuses to write those). Per-service usability
comes from the `master_service_types` / `master_service_brands` mappings, and
`service_job_dimensions` decides whether the customer is asked at all.

Idempotent — safe to re-run. Values are ordinary catalog rows: edit or
deactivate them in the admin console afterwards.

    python scripts/seed_ac_dimensions.py
    python scripts/seed_ac_dimensions.py --off   # unask, leaving data intact
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text

CATEGORY_SLUG = "air-conditioning"

#: Window/Split lead because they are the overwhelming majority of Indian
#: households; the rest are ordered by how often they actually come up.
AC_TYPES = [
    ("window-ac", "Window AC"),
    ("split-ac", "Split AC"),
    ("cassette-ac", "Cassette AC"),
    ("tower-ac", "Tower AC"),
    ("portable-ac", "Portable AC"),
]

AC_BRANDS = [
    ("voltas", "Voltas"),
    ("lg", "LG"),
    ("samsung", "Samsung"),
    ("daikin", "Daikin"),
    ("blue-star", "Blue Star"),
    ("hitachi", "Hitachi"),
    ("carrier", "Carrier"),
    ("whirlpool", "Whirlpool"),
]


async def run(turn_off: bool) -> int:
    from app.database import init_db, close_db, get_db_session

    await init_db()
    try:
        async with get_db_session() as db:
            category = (await db.execute(
                text("SELECT id FROM service_categories WHERE slug = :s"),
                {"s": CATEGORY_SLUG},
            )).scalar_one_or_none()
            if not category:
                print(f"No '{CATEGORY_SLUG}' category — nothing to seed.")
                return 1

            services = (await db.execute(text(
                "SELECT ms.id, ms.slug, msjt.job_type_id "
                "FROM master_services ms "
                "JOIN master_service_job_types msjt "
                "  ON msjt.master_service_id = ms.id AND msjt.is_active IS TRUE "
                "WHERE ms.category_id = :c"
            ), {"c": category})).all()
            if not services:
                print("No AC master services with an active job type.")
                return 1

            dimensions = dict((await db.execute(text(
                "SELECT key, id FROM catalog_dimensions WHERE key IN ('type','brand')"
            ))).all())

            if turn_off:
                await db.execute(text(
                    "UPDATE service_job_dimensions SET ask_customer = FALSE, required = FALSE "
                    "WHERE master_service_id = ANY(:ids) AND dimension_id = ANY(:dims)"
                ), {"ids": [s.id for s in services], "dims": list(dimensions.values())})
                print(f"type/brand no longer asked for {len(services)} AC service(s)")
                return 0

            # 1. The global value libraries.
            for order, (slug, name) in enumerate(AC_TYPES, start=1):
                await db.execute(text(
                    "INSERT INTO service_types "
                    "  (category_id, name, slug, code, is_active, customer_visible, "
                    "   status, display_order) "
                    "VALUES (:c, :n, :s, :code, TRUE, TRUE, 'active', :o) "
                    "ON CONFLICT DO NOTHING"
                ), {"c": category, "n": name, "s": slug, "code": slug.upper(), "o": order})
            for order, (slug, name) in enumerate(AC_BRANDS, start=1):
                await db.execute(text(
                    "INSERT INTO brands "
                    "  (category_id, name, slug, code, display_name, normalized_name, "
                    "   is_active, status) "
                    "VALUES (:c, :n, :s, :code, :n, :norm, TRUE, 'active') "
                    "ON CONFLICT DO NOTHING"
                ), {"c": category, "n": name, "s": slug, "code": slug.upper(),
                    "norm": name.lower()})

            type_ids = [r[0] for r in (await db.execute(text(
                "SELECT id FROM service_types WHERE category_id = :c AND is_active IS TRUE "
                "AND deleted_at IS NULL ORDER BY display_order"
            ), {"c": category})).all()]
            brand_ids = [r[0] for r in (await db.execute(text(
                "SELECT id FROM brands WHERE category_id = :c AND is_active IS TRUE "
                "ORDER BY name"
            ), {"c": category})).all()]

            # 2. Make every value usable by every AC service, and 3. ask for it.
            for service in services:
                for type_id in type_ids:
                    await db.execute(text(
                        "INSERT INTO master_service_types "
                        "  (master_service_id, service_type_id, is_active) "
                        "VALUES (:m, :t, TRUE) ON CONFLICT DO NOTHING"
                    ), {"m": service.id, "t": type_id})
                for order, brand_id in enumerate(brand_ids, start=1):
                    await db.execute(text(
                        "INSERT INTO master_service_brands "
                        "  (master_service_id, brand_id, is_active, status, display_order) "
                        "VALUES (:m, :b, TRUE, 'active', :o) ON CONFLICT DO NOTHING"
                    ), {"m": service.id, "b": brand_id, "o": order})

                for order, key in enumerate(("type", "brand"), start=1):
                    dimension_id = dimensions.get(key)
                    if not dimension_id:
                        continue
                    existing = (await db.execute(text(
                        "SELECT id FROM service_job_dimensions "
                        "WHERE master_service_id = :m AND dimension_id = :d "
                        "  AND job_type_id IS NOT DISTINCT FROM :j"
                    ), {"m": service.id, "d": dimension_id, "j": service.job_type_id})).scalar_one_or_none()
                    if existing:
                        await db.execute(text(
                            "UPDATE service_job_dimensions SET enabled = TRUE, required = TRUE, "
                            "  ask_customer = TRUE, display_order = :o WHERE id = :id"
                        ), {"o": order, "id": existing})
                    else:
                        await db.execute(text(
                            "INSERT INTO service_job_dimensions "
                            "  (master_service_id, job_type_id, dimension_id, enabled, required, "
                            "   ask_customer, affects_price, display_order) "
                            "VALUES (:m, :j, :d, TRUE, TRUE, TRUE, TRUE, :o)"
                        ), {"m": service.id, "j": service.job_type_id,
                            "d": dimension_id, "o": order})

            print(f"seeded {len(type_ids)} types + {len(brand_ids)} brands")
            print(f"type & brand now asked for {len(services)} AC service(s): "
                  f"{', '.join(sorted(s.slug for s in services))}")
        return 0
    finally:
        await close_db()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--off", action="store_true",
                        help="stop asking, without deleting the seeded values")
    raise SystemExit(asyncio.run(run(parser.parse_args().off)))
