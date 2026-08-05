"""Seed master issue types and their service mappings.
Idempotent by slug — skips existing rows. Maps issues to services by service slug.
Run: python scripts/seed_issue_types.py
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.engines.admin_catalog.models import MasterIssueType, MasterService, ServiceIssueMapping

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+asyncpg://serviceos:serviceos@127.0.0.1:5432/serviceos"
)

# ── Issue type definitions ────────────────────────────────────────────────────
# Keyed by slug
ISSUES: list[dict] = [
    # AC Repair
    {"code": "AC_NOT_COOLING",     "name": "AC Not Cooling",      "slug": "ac_not_cooling",      "severity": "high",   "requires_description": True},
    {"code": "AC_WATER_LEAKAGE",   "name": "Water Leakage",       "slug": "ac_water_leakage",    "severity": "medium", "requires_photo": True},
    {"code": "AC_NOISE_ISSUE",     "name": "Noise Issue",         "slug": "ac_noise_issue",      "severity": "medium"},
    {"code": "AC_GAS_REFILL",      "name": "Gas Refill Needed",   "slug": "ac_gas_refill_needed","severity": "high"},
    {"code": "AC_NOT_STARTING",    "name": "AC Not Starting",     "slug": "ac_not_starting",     "severity": "critical"},
    {"code": "AC_BAD_SMELL",       "name": "Bad Smell",           "slug": "ac_bad_smell",        "severity": "low",    "requires_description": True},
    {"code": "AC_REMOTE_NOT_WORK", "name": "Remote Not Working",  "slug": "ac_remote_not_working","severity": "low"},
    {"code": "AC_COOLING_LOW",     "name": "Cooling Low",         "slug": "ac_cooling_low",      "severity": "medium", "requires_description": True},

    # Plumbing
    {"code": "PLUMB_LEAKAGE",      "name": "Pipe Leakage",        "slug": "plumb_leakage",       "severity": "high",   "requires_photo": True},
    {"code": "PLUMB_BLOCKAGE",     "name": "Drain Blockage",      "slug": "plumb_blockage",      "severity": "medium"},
    {"code": "PLUMB_LOW_PRESSURE", "name": "Low Water Pressure",  "slug": "plumb_low_pressure",  "severity": "medium"},
    {"code": "PLUMB_PIPE_BROKEN",  "name": "Pipe Broken",         "slug": "plumb_pipe_broken",   "severity": "critical","requires_photo": True},
    {"code": "PLUMB_TAP_NOT_WORK", "name": "Tap Not Working",     "slug": "plumb_tap_not_working","severity": "low"},
    {"code": "PLUMB_OVERFLOW",     "name": "Water Tank Overflow", "slug": "plumb_overflow",      "severity": "high",   "requires_photo": True},
    {"code": "PLUMB_MOTOR",        "name": "Motor Not Working",   "slug": "plumb_motor_not_working","severity": "high"},

    # Electrical
    {"code": "ELEC_NO_POWER",      "name": "No Power",            "slug": "elec_no_power",       "severity": "critical"},
    {"code": "ELEC_SHORT_CIRCUIT", "name": "Short Circuit",       "slug": "elec_short_circuit",  "severity": "critical","requires_photo": True},
    {"code": "ELEC_FAN_NOT_WORK",  "name": "Fan Not Working",     "slug": "elec_fan_not_working","severity": "medium"},
    {"code": "ELEC_SWITCH",        "name": "Switch Not Working",  "slug": "elec_switch_not_working","severity": "low"},
    {"code": "ELEC_SOCKET_SPARK",  "name": "Socket Sparking",     "slug": "elec_socket_sparking","severity": "critical","requires_photo": True},
    {"code": "ELEC_WIRING",        "name": "Wiring Issue",        "slug": "elec_wiring_issue",   "severity": "high"},
    {"code": "ELEC_MCB_TRIP",      "name": "MCB Trip",            "slug": "elec_mcb_trip",       "severity": "high"},

    # Washing Machine
    {"code": "WM_NOT_SPINNING",    "name": "Not Spinning",        "slug": "wm_not_spinning",     "severity": "high"},
    {"code": "WM_WATER_LEAKAGE",   "name": "Water Leakage",       "slug": "wm_water_leakage",    "severity": "medium", "requires_photo": True},
    {"code": "WM_NOT_DRAINING",    "name": "Not Draining",        "slug": "wm_not_draining",     "severity": "high"},
    {"code": "WM_DOOR_LOCK",       "name": "Door Lock Issue",     "slug": "wm_door_lock_issue",  "severity": "medium"},
    {"code": "WM_NOISE_ISSUE",     "name": "Noise Issue",         "slug": "wm_noise_issue",      "severity": "medium"},
    {"code": "WM_POWER_ISSUE",     "name": "Power Issue",         "slug": "wm_power_issue",      "severity": "high"},

    # Cleaning
    {"code": "CLEAN_DEEP",         "name": "Deep Cleaning Required","slug": "clean_deep_required","severity": "low"},
    {"code": "CLEAN_MOVE_IN",      "name": "Move In Cleaning",    "slug": "clean_move_in",       "severity": "low"},
    {"code": "CLEAN_MOVE_OUT",     "name": "Move Out Cleaning",   "slug": "clean_move_out",      "severity": "low"},
    {"code": "CLEAN_STAIN",        "name": "Stain Removal",       "slug": "clean_stain_removal", "severity": "medium", "requires_photo": True},
    {"code": "CLEAN_ODOR",         "name": "Bad Odor",            "slug": "clean_bad_odor",      "severity": "medium", "requires_description": True},

    # Real Estate
    {"code": "RE_BUY_INQUIRY",     "name": "Buy Inquiry",         "slug": "re_buy_inquiry",      "severity": "low",    "requires_description": True},
    {"code": "RE_RENT_INQUIRY",    "name": "Rent Inquiry",        "slug": "re_rent_inquiry",     "severity": "low",    "requires_description": True},
    {"code": "RE_SITE_VISIT",      "name": "Site Visit Request",  "slug": "re_site_visit_request","severity": "low"},

    # Coaching
    {"code": "COACH_DEMO",         "name": "Demo Class Request",  "slug": "coach_demo_request",  "severity": "low"},
    {"code": "COACH_INQUIRY",      "name": "Course Inquiry",      "slug": "coach_course_inquiry","severity": "low",    "requires_description": True},
    {"code": "COACH_ADMISSION",    "name": "Admission Inquiry",   "slug": "coach_admission_inquiry","severity": "low"},
]

# ── Service → issue slug mapping ──────────────────────────────────────────────
# Maps service slug → list of issue slugs
SERVICE_ISSUE_MAP: dict[str, list[str]] = {
    # Real live catalog slug (Final Phase E2E audit, 2026-08-02) -- the
    # 'ac_repair' key below was aspirational and never matched any actual
    # seeded master_services row; 'ac-service' is what's live today.
    "ac-service": [
        "ac_not_cooling", "ac_water_leakage", "ac_noise_issue", "ac_gas_refill_needed",
        "ac_not_starting", "ac_bad_smell", "ac_remote_not_working", "ac_cooling_low",
    ],
    "ac_repair": [
        "ac_not_cooling", "ac_water_leakage", "ac_noise_issue", "ac_gas_refill_needed",
        "ac_not_starting", "ac_bad_smell", "ac_remote_not_working", "ac_cooling_low",
    ],
    "pipe_repair": [
        "plumb_leakage", "plumb_blockage", "plumb_low_pressure", "plumb_pipe_broken",
        "plumb_tap_not_working", "plumb_overflow", "plumb_motor_not_working",
    ],
    "drain_unblocking": [
        "plumb_blockage", "plumb_overflow",
    ],
    "ac_maintenance": [
        "ac_bad_smell", "ac_cooling_low", "ac_gas_refill_needed",
    ],
}


async def run():
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        # Create / fetch issue types
        issue_ids: dict[str, str] = {}
        for spec in ISSUES:
            slug = spec["slug"]
            existing = await db.scalar(select(MasterIssueType).where(MasterIssueType.slug == slug))
            if existing:
                issue_ids[slug] = str(existing.id)
                print(f"  [skip] issue {slug}")
                continue
            row = MasterIssueType(
                code=spec["code"],
                name=spec["name"],
                slug=slug,
                severity=spec.get("severity", "medium"),
                requires_photo=spec.get("requires_photo", False),
                requires_description=spec.get("requires_description", False),
                customer_visible=True,
                status="active",
                is_active=True,
                display_order=0,
            )
            db.add(row)
            await db.flush()
            issue_ids[slug] = str(row.id)
            print(f"  [created] issue {slug}")
        await db.commit()

        # Create service mappings
        for service_slug, issue_slugs in SERVICE_ISSUE_MAP.items():
            svc = await db.scalar(select(MasterService).where(MasterService.slug == service_slug))
            if not svc:
                print(f"  [skip] service '{service_slug}' not found in DB — seed master services first")
                continue
            for issue_slug in issue_slugs:
                if issue_slug not in issue_ids:
                    print(f"  [skip] issue '{issue_slug}' not in issue_ids map")
                    continue
                issue_uuid = issue_ids[issue_slug]
                from uuid import UUID
                existing_map = await db.scalar(
                    select(ServiceIssueMapping).where(
                        ServiceIssueMapping.master_service_id == svc.id,
                        ServiceIssueMapping.issue_type_id == UUID(issue_uuid),
                        ServiceIssueMapping.deleted_at.is_(None),
                    )
                )
                if existing_map:
                    print(f"  [skip] mapping {service_slug} -> {issue_slug}")
                    continue
                m = ServiceIssueMapping(
                    master_service_id=svc.id,
                    issue_type_id=UUID(issue_uuid),
                    status="active",
                    is_common=True,
                    customer_visible=True,
                    display_order=issue_slugs.index(issue_slug),
                )
                db.add(m)
                print(f"  [mapped] {service_slug} -> {issue_slug}")
        await db.commit()

    await engine.dispose()
    print("Done.")


if __name__ == "__main__":
    asyncio.run(run())
