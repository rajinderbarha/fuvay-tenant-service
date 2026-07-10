"""Sprint 34E — Seed service option groups, service options, and issue types.

Idempotent: checks code uniqueness before inserting.
Run: python -m scripts.seed_service_options_issues
"""
from __future__ import annotations
import asyncio
import uuid
from sqlalchemy import select

from app.models.database import AsyncSessionLocal
from app.engines.admin_catalog.models import (
    ServiceOptionGroup,
    MasterServiceOption,
    MasterIssueType,
)


# ── Option Groups ─────────────────────────────────────────────────────────────

GROUPS = [
    {"code": "ac_type",            "name": "AC Type",                "vertical_type": "home_service"},
    {"code": "washer_type",        "name": "Washing Machine Type",   "vertical_type": "home_service"},
    {"code": "geyser_type",        "name": "Geyser Type",            "vertical_type": "home_service"},
    {"code": "plumbing_fixture",   "name": "Plumbing Fixture",       "vertical_type": "home_service"},
    {"code": "cleaning_package",   "name": "Cleaning Package",       "vertical_type": "home_service"},
    {"code": "vehicle_type",       "name": "Vehicle Type",           "vertical_type": "home_service"},
    {"code": "property_type",      "name": "Property Type",          "vertical_type": "real_estate"},
    {"code": "course_type",        "name": "Course / Subject Type",  "vertical_type": "coaching"},
]


# ── Service Options ───────────────────────────────────────────────────────────

OPTIONS = [
    # AC Type
    {"code": "split_ac",        "name": "Split AC",           "option_type": "equipment_type", "group_code": "ac_type"},
    {"code": "window_ac",       "name": "Window AC",          "option_type": "equipment_type", "group_code": "ac_type"},
    {"code": "inverter_ac",     "name": "Inverter AC",        "option_type": "equipment_type", "group_code": "ac_type"},
    {"code": "cassette_ac",     "name": "Cassette AC",        "option_type": "equipment_type", "group_code": "ac_type"},
    {"code": "tower_ac",        "name": "Tower AC",           "option_type": "equipment_type", "group_code": "ac_type"},
    # Washing Machine Type
    {"code": "front_load",      "name": "Front Load",         "option_type": "equipment_type", "group_code": "washer_type"},
    {"code": "top_load",        "name": "Top Load",           "option_type": "equipment_type", "group_code": "washer_type"},
    {"code": "semi_automatic",  "name": "Semi Automatic",     "option_type": "equipment_type", "group_code": "washer_type"},
    # Geyser Type
    {"code": "electric_geyser", "name": "Electric Geyser",    "option_type": "equipment_type", "group_code": "geyser_type"},
    {"code": "gas_geyser",      "name": "Gas Geyser",         "option_type": "equipment_type", "group_code": "geyser_type"},
    {"code": "instant_geyser",  "name": "Instant Geyser",     "option_type": "equipment_type", "group_code": "geyser_type"},
    {"code": "storage_geyser",  "name": "Storage Geyser",     "option_type": "equipment_type", "group_code": "geyser_type"},
    # Plumbing Fixture
    {"code": "tap",             "name": "Tap",                "option_type": "equipment_type", "group_code": "plumbing_fixture"},
    {"code": "pipe",            "name": "Pipe",               "option_type": "equipment_type", "group_code": "plumbing_fixture"},
    {"code": "sink",            "name": "Sink",               "option_type": "equipment_type", "group_code": "plumbing_fixture"},
    {"code": "toilet",          "name": "Toilet",             "option_type": "equipment_type", "group_code": "plumbing_fixture"},
    {"code": "water_tank",      "name": "Water Tank",         "option_type": "equipment_type", "group_code": "plumbing_fixture"},
    # Cleaning Package
    {"code": "basic_cleaning",  "name": "Basic Cleaning",     "option_type": "add_on",         "group_code": "cleaning_package"},
    {"code": "deep_cleaning",   "name": "Deep Cleaning",      "option_type": "add_on",         "group_code": "cleaning_package"},
    {"code": "bathroom_clean",  "name": "Bathroom Cleaning",  "option_type": "add_on",         "group_code": "cleaning_package"},
    {"code": "kitchen_clean",   "name": "Kitchen Cleaning",   "option_type": "add_on",         "group_code": "cleaning_package"},
]


# ── Issue Types ───────────────────────────────────────────────────────────────

ISSUES = [
    # AC Repair
    {"code": "not_cooling",         "name": "Not cooling",          "severity": "high",   "requires_photo": False},
    {"code": "water_leakage_ac",    "name": "Water leakage",        "severity": "medium", "requires_photo": True},
    {"code": "noise_issue_ac",      "name": "Noise issue",          "severity": "medium", "requires_photo": False},
    {"code": "gas_refill_needed",   "name": "Gas refill needed",    "severity": "high",   "requires_photo": False},
    {"code": "remote_not_working",  "name": "Remote not working",   "severity": "low",    "requires_photo": False},
    {"code": "ac_not_starting",     "name": "AC not starting",      "severity": "high",   "requires_photo": False},
    # Geyser
    {"code": "no_heating",          "name": "No heating",           "severity": "high",   "requires_photo": False},
    {"code": "leakage_geyser",      "name": "Leakage",              "severity": "high",   "requires_photo": True},
    {"code": "power_issue_geyser",  "name": "Power issue",          "severity": "high",   "requires_photo": False},
    {"code": "low_hot_water",       "name": "Low hot water",        "severity": "medium", "requires_photo": False},
    {"code": "noise_geyser",        "name": "Strange noise",        "severity": "medium", "requires_photo": False},
    # Washing Machine
    {"code": "not_spinning",        "name": "Not spinning",         "severity": "high",   "requires_photo": False},
    {"code": "water_not_draining",  "name": "Water not draining",   "severity": "high",   "requires_photo": False},
    {"code": "noise_washer",        "name": "Noise issue",          "severity": "medium", "requires_photo": False},
    {"code": "door_lock_issue",     "name": "Door lock issue",      "severity": "medium", "requires_photo": False},
    {"code": "water_leakage_washer","name": "Water leakage",        "severity": "medium", "requires_photo": True},
    # Plumbing
    {"code": "leakage_plumbing",    "name": "Leakage",              "severity": "high",   "requires_photo": True},
    {"code": "blockage",            "name": "Blockage",             "severity": "medium", "requires_photo": False},
    {"code": "low_water_pressure",  "name": "Low water pressure",   "severity": "medium", "requires_photo": False},
    {"code": "installation_req",    "name": "Installation required","severity": "medium", "requires_photo": False},
    {"code": "pipe_repair",         "name": "Pipe repair",          "severity": "high",   "requires_photo": True},
    # Electrical
    {"code": "no_power",            "name": "No power",             "severity": "high",   "requires_photo": False},
    {"code": "short_circuit",       "name": "Short circuit",        "severity": "urgent", "requires_photo": True},
    {"code": "switch_socket_issue", "name": "Switch / socket issue","severity": "medium", "requires_photo": False},
    {"code": "fan_issue",           "name": "Fan issue",            "severity": "low",    "requires_photo": False},
    {"code": "wiring_issue",        "name": "Wiring issue",         "severity": "high",   "requires_photo": True},
    # Generic
    {"code": "inspection_needed",   "name": "Inspection needed",    "severity": "low",    "requires_photo": False},
    {"code": "other_issue",         "name": "Other issue",          "severity": "medium", "requires_photo": False, "requires_description": True},
    {"code": "not_sure",            "name": "Not sure",             "severity": "low",    "requires_photo": False, "requires_description": True},
]


def _slug(name: str) -> str:
    import re
    return re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        # ── Option Groups ────────────────────────────────────────────────────
        grp_map: dict[str, uuid.UUID] = {}
        grp_created = grp_skipped = 0
        for g in GROUPS:
            existing = await db.scalar(
                select(ServiceOptionGroup).where(ServiceOptionGroup.code == g["code"]))
            if existing:
                grp_map[g["code"]] = existing.id
                grp_skipped += 1
            else:
                row = ServiceOptionGroup(
                    code=g["code"], name=g["name"],
                    vertical_type=g.get("vertical_type"), status="active",
                )
                db.add(row)
                await db.flush()
                grp_map[g["code"]] = row.id
                grp_created += 1
        await db.commit()
        print(f"Option groups: {grp_created} created, {grp_skipped} skipped")

        # ── Service Options ──────────────────────────────────────────────────
        opt_created = opt_skipped = 0
        for o in OPTIONS:
            existing = await db.scalar(
                select(MasterServiceOption).where(MasterServiceOption.code == o["code"]))
            if existing:
                opt_skipped += 1
                continue
            slug = _slug(o["name"])
            # ensure slug unique
            slug_check = await db.scalar(
                select(MasterServiceOption).where(MasterServiceOption.slug == slug))
            if slug_check:
                slug = f"{slug}_{o['code']}"
            from decimal import Decimal
            row = MasterServiceOption(
                code=o["code"],
                name=o["name"],
                slug=slug,
                option_type=o.get("option_type", "add_on"),
                unit="per_unit",
                default_price=Decimal("0"),
                is_customer_selectable=True,
                is_active=True,
                status="active",
                option_group_id=grp_map.get(o.get("group_code", "")) if o.get("group_code") else None,
                vertical_type="home_service",
            )
            db.add(row)
            opt_created += 1
        await db.commit()
        print(f"Service options: {opt_created} created, {opt_skipped} skipped")

        # ── Issue Types ──────────────────────────────────────────────────────
        iss_created = iss_skipped = 0
        for i in ISSUES:
            existing = await db.scalar(
                select(MasterIssueType).where(MasterIssueType.code == i["code"]))
            if existing:
                iss_skipped += 1
                continue
            slug = _slug(i["name"])
            slug_check = await db.scalar(
                select(MasterIssueType).where(MasterIssueType.slug == slug))
            if slug_check:
                slug = f"{slug}_{i['code']}"
            row = MasterIssueType(
                code=i["code"],
                name=i["name"],
                slug=slug,
                severity=i.get("severity", "medium"),
                is_active=True,
                status="active",
                vertical_type="home_service",
                requires_photo=i.get("requires_photo", False),
                requires_description=i.get("requires_description", False),
            )
            db.add(row)
            iss_created += 1
        await db.commit()
        print(f"Issue types: {iss_created} created, {iss_skipped} skipped")

    print("Seed complete.")


if __name__ == "__main__":
    asyncio.run(seed())
