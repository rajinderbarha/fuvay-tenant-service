"""Sprint 34D — Seed 25 starter brands for Home Services vertical.

Run: python -m scripts.seed_brands
Idempotent — skips existing brands by normalized name.
"""
from __future__ import annotations

import asyncio
import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def normalize_brand_name(name: str) -> str:
    n = name.strip().lower()
    n = re.sub(r"(?<=[a-z])\.(?=[a-z])", "", n)
    n = re.sub(r"[^\w\s]", "", n)
    n = re.sub(r"\s+", " ", n).strip()
    for suffix in (" india", " global", " international", " ltd", " pvt", " llc", " inc"):
        if n.endswith(suffix):
            n = n[: -len(suffix)].strip()
    return n


def _slugify(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    return re.sub(r"-+", "-", s).strip("-")


STARTER_BRANDS = [
    # Home Appliances / Electronics
    {"name": "Samsung",    "code": "SAMSUNG",   "country_of_origin": "South Korea", "display_order": 1},
    {"name": "LG",         "code": "LG",        "country_of_origin": "South Korea", "display_order": 2},
    {"name": "Whirlpool",  "code": "WHIRLPOOL", "country_of_origin": "USA",         "display_order": 3},
    {"name": "Haier",      "code": "HAIER",     "country_of_origin": "China",       "display_order": 4},
    {"name": "Godrej",     "code": "GODREJ",    "country_of_origin": "India",       "display_order": 5},
    {"name": "Bosch",      "code": "BOSCH",     "country_of_origin": "Germany",     "display_order": 6},
    {"name": "IFB",        "code": "IFB",       "country_of_origin": "India",       "display_order": 7},
    # AC Brands
    {"name": "Voltas",     "code": "VOLTAS",    "country_of_origin": "India",       "display_order": 8},
    {"name": "Blue Star",  "code": "BLUESTAR",  "country_of_origin": "India",       "display_order": 9,
     "alias_names_json": ["Bluestar"]},
    {"name": "Daikin",     "code": "DAIKIN",    "country_of_origin": "Japan",       "display_order": 10},
    {"name": "Hitachi",    "code": "HITACHI",   "country_of_origin": "Japan",       "display_order": 11},
    {"name": "Carrier",    "code": "CARRIER",   "country_of_origin": "USA",         "display_order": 12},
    {"name": "Lloyd",      "code": "LLOYD",     "country_of_origin": "India",       "display_order": 13},
    {"name": "O General",  "code": "OGENERAL",  "country_of_origin": "Japan",       "display_order": 14,
     "alias_names_json": ["OGeneral", "O-General"]},
    {"name": "Panasonic",  "code": "PANASONIC", "country_of_origin": "Japan",       "display_order": 15},
    {"name": "Sony",       "code": "SONY",      "country_of_origin": "Japan",       "display_order": 16},
    # Electronics / Appliances
    {"name": "Philips",    "code": "PHILIPS",   "country_of_origin": "Netherlands", "display_order": 17},
    {"name": "Bajaj",      "code": "BAJAJ",     "country_of_origin": "India",       "display_order": 18},
    {"name": "Havells",    "code": "HAVELLS",   "country_of_origin": "India",       "display_order": 19},
    {"name": "Crompton",   "code": "CROMPTON",  "country_of_origin": "India",       "display_order": 20},
    {"name": "Usha",       "code": "USHA",      "country_of_origin": "India",       "display_order": 21},
    {"name": "V-Guard",    "code": "VGUARD",    "country_of_origin": "India",       "display_order": 22},
    # Water Heater / Purifier
    {"name": "AO Smith",   "code": "AOSMITH",   "country_of_origin": "USA",         "display_order": 23,
     "alias_names_json": ["A.O. Smith", "A O Smith"]},
    {"name": "Kent",       "code": "KENT",      "country_of_origin": "India",       "display_order": 24},
    {"name": "Aquaguard",  "code": "AQUAGUARD", "country_of_origin": "India",       "display_order": 25},
]


async def seed():
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from app.engines.admin_catalog.models import Brand

    database_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://serviceos:serviceos@localhost:5432/serviceos")
    engine = create_async_engine(database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    created = []
    skipped = []

    async with async_session() as db:
        for bdata in STARTER_BRANDS:
            norm = normalize_brand_name(bdata["name"])
            # Check by normalized name
            res = await db.execute(
                select(Brand).where(Brand.normalized_name == norm, Brand.deleted_at.is_(None))
            )
            existing = res.scalar_one_or_none()
            if existing:
                skipped.append(bdata["name"])
                continue
            # Check by code
            if bdata.get("code"):
                code_res = await db.execute(
                    select(Brand).where(Brand.code == bdata["code"], Brand.deleted_at.is_(None))
                )
                if code_res.scalar_one_or_none():
                    skipped.append(bdata["name"])
                    continue

            slug = _slugify(bdata["name"])
            # Ensure unique slug
            slug_res = await db.execute(
                select(Brand).where(Brand.slug == slug, Brand.deleted_at.is_(None))
            )
            if slug_res.scalar_one_or_none():
                import uuid as _uuid
                slug = f"{slug}-{str(_uuid.uuid4())[:6]}"

            brand = Brand(
                name=bdata["name"],
                slug=slug,
                code=bdata.get("code"),
                status="active",
                is_active=True,
                is_global=True,
                normalized_name=norm,
                alias_names_json=bdata.get("alias_names_json"),
                country_of_origin=bdata.get("country_of_origin"),
                display_order=bdata.get("display_order", 0),
            )
            db.add(brand)
            created.append(bdata["name"])

        await db.commit()

    print(f"\nBrand seeding complete.")
    print(f"  Created : {len(created)} — {created}")
    print(f"  Skipped : {len(skipped)} — {skipped}")
    return {"created": created, "skipped": skipped}


if __name__ == "__main__":
    asyncio.run(seed())
