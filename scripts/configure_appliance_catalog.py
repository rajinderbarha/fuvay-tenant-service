"""Publish the market-ready non-AC Home Services appliance catalog.

This is the deterministic admin-side catalog configurator for Geyser,
Refrigerator, Washing Machine, Chimney and RO/Water Purifier. It writes only
platform-owned structure: groups, services, types, brands, customer questions,
problems, versioned workflows and technician completion checklists. Providers
remain the only owners of price amounts.

Run::

    python scripts/configure_appliance_catalog.py
"""
from __future__ import annotations

import asyncio
import re
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import create_engine
from app.engines.admin_catalog.job_type_blueprint_service import JobTypeBlueprintService
from app.engines.admin_catalog.models import (
    Brand,
    BrandMapping,
    CatalogDimension,
    JobTypeDefinition,
    MasterIssueType,
    MasterService,
    MasterServiceBrand,
    MasterServiceJobType,
    MasterServiceType,
    ServiceBlueprintVersion,
    ServiceCategory,
    ServiceGroup,
    ServiceIssueMapping,
    ServiceJobDimension,
    ServiceJobWorkflow,
    ServiceType,
    ServiceTypeMapping,
)
from scripts.configure_ac_catalog import (
    _ensure_checklist,
    _ensure_dimension,
    _ensure_question,
    _one,
    _workflow_journey,
)


NOW = lambda: datetime.now(timezone.utc)

ICON_URLS = {
    "geyser_services": "https://res.cloudinary.com/dr1b4ezct/image/upload/v1787511014/serviceos/customer-home/service-groups/dc82f12f09810fac491f8238.png.png",
    "refrigerator_services": "https://res.cloudinary.com/dr1b4ezct/image/upload/v1787511018/serviceos/customer-home/service-groups/91f0b92600884db2a7c31fc2.png.png",
    "washing_machine_services": "https://res.cloudinary.com/dr1b4ezct/image/upload/v1787511026/serviceos/customer-home/service-groups/e95c802224fa37997b1e74e0.png.png",
    "chimney_services": "https://res.cloudinary.com/dr1b4ezct/image/upload/v1787511009/serviceos/customer-home/service-groups/e1da97ab12387b9ed14b1948.png.png",
    "ro_services": "https://res.cloudinary.com/dr1b4ezct/image/upload/v1787511022/serviceos/customer-home/service-groups/80d7b108137fed1db905eb4b.png.png",
}


def _q(key, label, options):
    return (key, label, "single_select", options)


CATALOG = {
    "geyser_services": {
        "name": "Geyser & Water Heater",
        "description": "Repair, installation and preventive care for domestic water heaters.",
        "types": [("Storage Geyser", "storage_geyser"), ("Instant Geyser", "instant_geyser"), ("Gas Geyser", "gas_geyser"), ("Solar Water Heater", "solar_water_heater")],
        "brands": ["AO Smith", "Racold", "Bajaj", "Havells", "V-Guard", "Crompton", "Venus"],
        "services": [
            {
                "slug": "geyser_repair", "name": "Geyser Repair", "job": "repair",
                "description": "On-site diagnosis and repair with an estimate before paid work begins.",
                "issues": [("not_heating", "Water is not heating", "high"), ("water_leak", "Water leaking from the geyser", "high"), ("mcb_trip", "Geyser is tripping the MCB", "critical"), ("low_hot_water", "Hot water runs out too quickly", "medium"), ("noise", "Unusual noise from the geyser", "medium"), ("no_power", "Geyser is not switching on", "high")],
                "questions": [_q("indicator_state", "What does the power indicator show?", [("on", "On"), ("off", "Off"), ("intermittent", "Turns on and off"), ("none", "There is no indicator")]), _q("leak_location", "If there is a leak, where is it visible?", [("tank", "From the tank"), ("pipe", "From a pipe or connection"), ("valve", "From the safety valve"), ("none", "No visible leak")]), _q("issue_duration", "How long has this been happening?", [("today", "Started today"), ("days", "A few days"), ("weeks", "A few weeks"), ("longer", "More than a month")])],
            },
            {
                "slug": "geyser_installation", "name": "Geyser Installation", "job": "installation",
                "description": "Safe mounting, water connections, electrical checks and commissioning.",
                "issues": [("new_install", "Install a new geyser", "low"), ("replace", "Replace an existing geyser", "medium")],
                "questions": [_q("site_ready", "Is the mounting location ready?", [("yes", "Yes"), ("no", "No"), ("unsure", "Not sure")]), _q("connections_ready", "Are water and electrical connections available?", [("both", "Both are ready"), ("water", "Only water is ready"), ("power", "Only power is ready"), ("neither", "Neither is ready")])],
            },
            {
                "slug": "geyser_maintenance", "name": "Geyser Service & Descaling", "job": "service",
                "description": "Tank descaling, element inspection and safety-valve checks.",
                "issues": [("routine", "Routine annual service", "low"), ("scale", "Scale buildup or reduced heating", "medium"), ("safety_check", "Safety and electrical check", "medium")],
                "questions": [_q("last_service", "When was the geyser last serviced?", [("six_months", "Within 6 months"), ("one_year", "6-12 months ago"), ("older", "More than a year ago"), ("unknown", "I do not know")]), _q("water_quality", "What kind of water supply do you have?", [("soft", "Soft water"), ("hard", "Hard water"), ("unknown", "Not sure")])],
            },
        ],
    },
    "refrigerator_services": {
        "name": "Refrigerator",
        "description": "Cooling-system repair and preventive refrigerator maintenance.",
        "types": [("Single Door", "single_door_refrigerator"), ("Double Door", "double_door_refrigerator"), ("Side-by-Side", "side_by_side_refrigerator"), ("French Door", "french_door_refrigerator")],
        "brands": ["LG", "Samsung", "Whirlpool", "Godrej", "Haier", "Panasonic", "Bosch"],
        "services": [
            {
                "slug": "refrigerator_repair", "name": "Refrigerator Repair", "job": "repair",
                "description": "Diagnosis of cooling, electrical, leakage and compressor faults.",
                "issues": [("not_cooling", "Refrigerator is not cooling", "high"), ("over_freezing", "Food is freezing in the fridge section", "medium"), ("water_leak", "Water leaking from the refrigerator", "medium"), ("noise", "Unusual noise or vibration", "medium"), ("no_power", "Refrigerator is not switching on", "high"), ("door_seal", "Door is not closing or sealing", "medium"), ("ice_buildup", "Heavy ice buildup", "medium")],
                "questions": [_q("freezer_state", "Is the freezer cooling?", [("normal", "Cooling normally"), ("weak", "Cooling weakly"), ("none", "Not cooling"), ("unknown", "Not sure")]), _q("compressor_sound", "Can you hear the compressor running?", [("yes", "Yes"), ("no", "No"), ("clicking", "It clicks repeatedly"), ("unknown", "Not sure")]), _q("issue_duration", "How long has this problem been present?", [("today", "Started today"), ("days", "A few days"), ("weeks", "A few weeks"), ("longer", "More than a month")])],
            },
            {
                "slug": "refrigerator_maintenance", "name": "Refrigerator Preventive Service", "job": "service",
                "description": "Coil cleaning, drain inspection, seal check and performance testing.",
                "issues": [("routine", "Routine preventive maintenance", "low"), ("coil_clean", "Condenser coil cleaning", "low"), ("performance", "Cooling performance check", "medium")],
                "questions": [_q("last_service", "When was the refrigerator last serviced?", [("six_months", "Within 6 months"), ("one_year", "6-12 months ago"), ("older", "More than a year ago"), ("never", "Never or not sure")]), _q("location_clearance", "Is there ventilation space around the refrigerator?", [("yes", "Yes"), ("limited", "Very little"), ("none", "No space"), ("unknown", "Not sure")])],
            },
        ],
    },
    "washing_machine_services": {
        "name": "Washing Machine",
        "description": "Repair, installation and preventive care for automatic and semi-automatic washers.",
        "types": [("Front Load", "front_load_washer"), ("Top Load", "top_load_washer"), ("Semi-Automatic", "semi_automatic_washer")],
        "brands": ["LG", "Samsung", "Whirlpool", "IFB", "Bosch", "Haier", "Godrej", "Panasonic"],
        "services": [
            {
                "slug": "washing_machine_repair", "name": "Washing Machine Repair", "job": "repair",
                "description": "Diagnosis of drainage, spin, leakage, electrical and control faults.",
                "issues": [("not_spinning", "Drum is not spinning", "high"), ("not_draining", "Water is not draining", "high"), ("water_leak", "Water leaking from the machine", "medium"), ("no_power", "Machine is not switching on", "high"), ("noise", "Unusual noise or vibration", "medium"), ("door_lock", "Door or lid is not locking", "medium"), ("error_code", "Error code on the display", "medium")],
                "questions": [_q("cycle_stage", "At which stage does the cycle stop?", [("fill", "Water filling"), ("wash", "Washing"), ("drain", "Draining"), ("spin", "Spinning"), ("before_start", "Before it starts")]), _q("error_display", "Is an error code visible?", [("yes", "Yes"), ("no", "No"), ("no_display", "The machine has no display")]), _q("issue_duration", "How long has this been happening?", [("today", "Started today"), ("days", "A few days"), ("weeks", "A few weeks"), ("longer", "More than a month")])],
            },
            {
                "slug": "washing_machine_installation", "name": "Washing Machine Installation", "job": "installation",
                "description": "Leveling, inlet and drain connections, test cycle and customer handover.",
                "issues": [("new_install", "Install a new washing machine", "low"), ("relocation", "Reconnect after moving", "low")],
                "questions": [_q("connections", "Are an inlet tap, drain and power point ready?", [("all", "All are ready"), ("some", "Only some are ready"), ("none", "None are ready"), ("unsure", "Not sure")]), _q("stand_required", "Do you need a stand or trolley installed?", [("yes", "Yes"), ("no", "No"), ("already", "Already installed")])],
            },
            {
                "slug": "washing_machine_maintenance", "name": "Washing Machine Deep Clean", "job": "service",
                "description": "Drum, filter, inlet and drain cleaning with a complete test cycle.",
                "issues": [("routine", "Routine machine cleaning", "low"), ("odor", "Bad smell from the drum", "medium"), ("residue", "Lint or detergent residue", "low")],
                "questions": [_q("last_clean", "When was the machine last deep-cleaned?", [("six_months", "Within 6 months"), ("one_year", "6-12 months ago"), ("older", "More than a year ago"), ("never", "Never")]), _q("water_supply", "What is the water supply quality?", [("soft", "Soft water"), ("hard", "Hard water"), ("unknown", "Not sure")])],
            },
        ],
    },
    "chimney_services": {
        "name": "Chimney & Hob",
        "description": "Kitchen chimney repair, installation and intensive degreasing.",
        "types": [("Wall-Mounted Chimney", "wall_mounted_chimney"), ("Island Chimney", "island_chimney"), ("Built-In Chimney", "built_in_chimney"), ("Straight-Line Chimney", "straight_line_chimney")],
        "brands": ["Faber", "Elica", "Glen", "Hindware", "Kaff", "Bosch"],
        "services": [
            {
                "slug": "chimney_repair", "name": "Chimney Repair", "job": "repair",
                "description": "Diagnosis of suction, motor, control, light and vibration faults.",
                "issues": [("low_suction", "Low or no suction", "high"), ("motor_noise", "Motor is noisy", "medium"), ("no_power", "Chimney is not switching on", "high"), ("light_fault", "Chimney light is not working", "low"), ("control_fault", "Buttons or touch controls are not working", "medium")],
                "questions": [_q("motor_state", "Does the motor run?", [("normal", "Runs normally"), ("slow", "Runs slowly"), ("noise", "Runs with noise"), ("none", "Does not run")]), _q("filter_state", "When was the filter last cleaned?", [("month", "Within a month"), ("quarter", "1-3 months ago"), ("older", "More than 3 months ago"), ("unknown", "Not sure")])],
            },
            {
                "slug": "chimney_installation", "name": "Chimney Installation", "job": "installation",
                "description": "Mounting, duct routing, electrical connection and suction testing.",
                "issues": [("new_install", "Install a new chimney", "low"), ("replace", "Replace an existing chimney", "medium")],
                "questions": [_q("duct_ready", "Is a duct opening available?", [("yes", "Yes"), ("no", "No"), ("ductless", "This is a ductless model"), ("unsure", "Not sure")]), _q("power_ready", "Is a power point available near the chimney?", [("yes", "Yes"), ("no", "No"), ("unsure", "Not sure")])],
            },
            {
                "slug": "chimney_deep_clean", "name": "Chimney Deep Cleaning", "job": "service",
                "description": "Filter, blower and housing degreasing with suction verification.",
                "issues": [("routine", "Routine chimney cleaning", "low"), ("heavy_grease", "Heavy grease buildup", "medium"), ("odor_smoke", "Smoke or odor is not clearing", "medium")],
                "questions": [_q("last_clean", "When was the chimney last professionally cleaned?", [("three_months", "Within 3 months"), ("six_months", "3-6 months ago"), ("older", "More than 6 months ago"), ("never", "Never")]), _q("filter_type", "What type of filter does it use?", [("baffle", "Baffle filter"), ("mesh", "Mesh filter"), ("carbon", "Carbon filter"), ("unknown", "Not sure")])],
            },
        ],
    },
    "ro_services": {
        "name": "RO & Water Purifier",
        "description": "Water purifier repair, installation and filter/membrane maintenance.",
        "types": [("RO + UV", "ro_uv_purifier"), ("RO + UV + UF", "ro_uv_uf_purifier"), ("UV Purifier", "uv_purifier"), ("Gravity Purifier", "gravity_purifier")],
        "brands": ["Kent", "Aquaguard", "Livpure", "Pureit", "AO Smith", "Blue Star"],
        "services": [
            {
                "slug": "ro_repair", "name": "RO Water Purifier Repair", "job": "repair",
                "description": "Diagnosis of flow, leakage, taste, pump, UV and control faults.",
                "issues": [("no_water", "No purified water output", "high"), ("slow_flow", "Water flow is very slow", "medium"), ("leak", "Water leaking from the purifier", "high"), ("bad_taste", "Bad taste or odor", "medium"), ("no_power", "Purifier is not switching on", "high"), ("alarm", "Filter-change light or alarm is on", "medium")],
                "questions": [_q("inlet_flow", "Is water reaching the purifier?", [("yes", "Yes"), ("low", "Flow is low"), ("no", "No"), ("unknown", "Not sure")]), _q("tank_state", "Does the storage tank fill?", [("normal", "Fills normally"), ("slow", "Fills slowly"), ("none", "Does not fill"), ("no_tank", "No storage tank")]), _q("service_age", "When were the filters last replaced?", [("six_months", "Within 6 months"), ("one_year", "6-12 months ago"), ("older", "More than a year ago"), ("unknown", "Not sure")])],
            },
            {
                "slug": "ro_installation", "name": "RO Water Purifier Installation", "job": "installation",
                "description": "Mounting, inlet/drain connection, flushing and TDS verification.",
                "issues": [("new_install", "Install a new water purifier", "low"), ("relocation", "Reinstall after moving", "low")],
                "questions": [_q("inlet_ready", "Is a water inlet available near the installation point?", [("yes", "Yes"), ("no", "No"), ("unsure", "Not sure")]), _q("drain_ready", "Is a drain outlet available?", [("yes", "Yes"), ("no", "No"), ("unsure", "Not sure")])],
            },
            {
                "slug": "ro_maintenance", "name": "RO Filter & Membrane Service", "job": "service",
                "description": "Filter inspection or replacement, sanitisation, flushing and TDS check.",
                "issues": [("routine", "Routine purifier service", "low"), ("filter_due", "Filters are due for replacement", "medium"), ("tds_high", "Purified-water TDS is high", "high"), ("sanitize", "Tank sanitisation", "low")],
                "questions": [_q("last_service", "When was the purifier last serviced?", [("six_months", "Within 6 months"), ("one_year", "6-12 months ago"), ("older", "More than a year ago"), ("unknown", "Not sure")]), _q("tds_known", "Do you know the current output TDS?", [("normal", "Below 150 ppm"), ("high", "150 ppm or higher"), ("unknown", "Not sure")])],
            },
        ],
    },
}


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _workflow_rule(job_key: str) -> dict:
    inspection = job_key == "repair"
    return {
        "inspection_required": inspection,
        "quote_approval_required": inspection,
        "checklist_required": True,
        "pricing_behavior": "inspection_required" if inspection else "fixed",
    }


def _checklist_sections(group_name: str, service_name: str, job_key: str):
    if job_key == "repair":
        work_items = [
            ("LONG_TEXT", "Record the diagnosis and root cause", True, False, None),
            ("SHORT_TEXT", "Record parts repaired or replaced", False, False, None),
            ("YES_NO", f"{group_name} safety and operating checks passed", True, False, None),
        ]
    elif job_key == "installation":
        work_items = [
            ("YES_NO", "Mounting and connection points are secure", True, False, None),
            ("YES_NO", "Electrical, water and drainage checks are complete", True, False, None),
            ("YES_NO", "A full commissioning test passed", True, False, None),
        ]
    else:
        work_items = [
            ("YES_NO", "Required cleaning or preventive tasks are complete", True, False, None),
            ("SHORT_TEXT", "Record consumables or parts replaced", False, False, None),
            ("YES_NO", "Final performance test passed", True, False, None),
        ]
    return [
        ("Safety & Preparation", [("YES_NO", "Power or utilities isolated where required", True, False, None), ("CHECKBOX", "Customer property and work area protected", True, False, None)]),
        ("Service Work", work_items),
        ("Completion Evidence", [("PHOTO", f"Photo of completed {service_name.lower()}", True, True, None), ("LONG_TEXT", "Completion notes and customer guidance", True, False, None), ("SIGNATURE", "Customer sign-off", True, True, None)]),
    ]


async def _ensure_brand(db, name: str, order: int) -> Brand:
    slug = _slug(name)
    row = await _one(db, Brand, slug=slug)
    if not row:
        row = Brand(name=name, slug=slug, code=slug.replace("-", "_").upper(),
                    display_name=name, normalized_name=name.lower(), status="active",
                    is_global=True, is_active=True, display_order=order)
        db.add(row)
        await db.flush()
    else:
        row.name = row.display_name = name
        row.status, row.is_active, row.deleted_at = "active", True, None
    return row


async def configure() -> None:
    engine = create_engine()
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    service_context: dict[str, tuple[MasterService, JobTypeDefinition, MasterServiceJobType, dict, str]] = {}

    async with session_factory() as db:
        category = (await db.execute(select(ServiceCategory).where(
            ServiceCategory.vertical_type == "home_services",
            ServiceCategory.is_active.is_(True),
        ))).scalars().first()
        if not category:
            raise RuntimeError("Active Home Services category is missing")

        type_dimension = await _ensure_dimension(db, "type", "Equipment Type", "service_types", 10)
        brand_dimension = await _ensure_dimension(db, "brand", "Brand", "brands", 20)

        for group_order, (group_slug, group_spec) in enumerate(CATALOG.items(), start=1):
            group = await _one(db, ServiceGroup, slug=group_slug)
            if not group:
                group = ServiceGroup(category_id=category.id, code=group_slug.upper(),
                                     name=group_spec["name"], slug=group_slug,
                                     description=group_spec["description"], status="active",
                                     display_order=group_order)
                db.add(group)
                await db.flush()
            group.category_id, group.name = category.id, group_spec["name"]
            group.description, group.status = group_spec["description"], "active"
            group.display_order, group.deleted_at = group_order, None
            group.icon_url = ICON_URLS[group_slug]

            types = []
            for type_order, (type_name, type_slug) in enumerate(group_spec["types"]):
                service_type = await _one(db, ServiceType, slug=type_slug)
                if not service_type:
                    service_type = ServiceType(category_id=category.id, name=type_name,
                                               slug=type_slug, code=type_slug.upper(),
                                               type_family=group_slug, is_active=True,
                                               status="active", customer_visible=True,
                                               display_order=type_order)
                    db.add(service_type)
                    await db.flush()
                else:
                    service_type.category_id, service_type.name = category.id, type_name
                    service_type.is_active, service_type.status = True, "active"
                    service_type.deleted_at = None
                types.append(service_type)

            brands = [await _ensure_brand(db, name, index) for index, name in enumerate(group_spec["brands"])]

            for service_order, spec in enumerate(group_spec["services"]):
                job_type = await _one(db, JobTypeDefinition, key=spec["job"])
                if not job_type:
                    raise RuntimeError(f"Active job type '{spec['job']}' is missing")
                service = await _one(db, MasterService, slug=spec["slug"])
                if not service:
                    service = MasterService(category_id=category.id, service_group_id=group.id,
                                            service_name=spec["name"], slug=spec["slug"],
                                            description=spec["description"], job_type=spec["job"],
                                            job_type_id=job_type.id,
                                            pricing_model="inspection_based" if spec["job"] == "repair" else "fixed",
                                            base_price=Decimal("0"), visit_fee=Decimal("0"),
                                            estimated_duration_minutes=60,
                                            requires_checklist=True, is_brand_required=True,
                                            is_type_required=True, requires_issue_type=True,
                                            requires_schedule=True, requires_address=True,
                                            tenant_override_allowed=True, is_active=True,
                                            display_order=service_order)
                    db.add(service)
                    await db.flush()
                else:
                    service.category_id, service.service_group_id = category.id, group.id
                    service.service_name, service.description = spec["name"], spec["description"]
                    service.job_type, service.job_type_id = spec["job"], job_type.id
                    service.pricing_model = "inspection_based" if spec["job"] == "repair" else "fixed"
                    service.base_price, service.visit_fee = Decimal("0"), Decimal("0")
                    service.requires_checklist = service.is_brand_required = service.is_type_required = True
                    service.requires_issue_type = service.requires_schedule = service.requires_address = True
                    service.tenant_override_allowed, service.is_active = True, True
                    service.display_order, service.deleted_at = service_order, None

                link = await _one(db, MasterServiceJobType, master_service_id=service.id, job_type_id=job_type.id)
                if not link:
                    link = MasterServiceJobType(master_service_id=service.id, job_type_id=job_type.id,
                                                is_active=True, display_order=0)
                    db.add(link)
                    await db.flush()
                else:
                    link.is_active = True

                for index, service_type in enumerate(types):
                    mapping = await _one(db, ServiceTypeMapping, type_id=service_type.id,
                                         category_id=category.id, service_group_id=group.id,
                                         service_id=service.id)
                    if not mapping:
                        db.add(ServiceTypeMapping(type_id=service_type.id, category_id=category.id,
                                                  service_group_id=group.id, service_id=service.id,
                                                  customer_visible=True, provider_visible=True,
                                                  status="active", display_order=index))
                    else:
                        mapping.status, mapping.customer_visible, mapping.provider_visible = "active", True, True
                    runtime = await _one(db, MasterServiceType, master_service_id=service.id,
                                         service_type_id=service_type.id)
                    if not runtime:
                        db.add(MasterServiceType(master_service_id=service.id,
                                                 service_type_id=service_type.id,
                                                 is_required=False, is_default=False, is_active=True))
                    else:
                        runtime.is_active = True

                for index, brand in enumerate(brands):
                    mapping = await _one(db, BrandMapping, brand_id=brand.id,
                                         category_id=category.id, service_group_id=group.id,
                                         service_id=service.id)
                    if not mapping:
                        db.add(BrandMapping(brand_id=brand.id, category_id=category.id,
                                            service_group_id=group.id, service_id=service.id,
                                            customer_visible=True, provider_visible=True,
                                            status="active", display_order=index))
                    else:
                        mapping.status, mapping.customer_visible, mapping.provider_visible = "active", True, True
                    runtime = await _one(db, MasterServiceBrand, master_service_id=service.id,
                                         brand_id=brand.id)
                    if not runtime:
                        db.add(MasterServiceBrand(master_service_id=service.id, brand_id=brand.id,
                                                  is_required=False, is_default=False, is_active=True,
                                                  status="active", display_order=index,
                                                  can_override_price=spec["job"] != "repair",
                                                  is_routing_only=spec["job"] == "repair"))
                    else:
                        runtime.is_active, runtime.status = True, "active"
                        runtime.display_order = index
                        runtime.can_override_price = spec["job"] != "repair"
                        runtime.is_routing_only = spec["job"] == "repair"

                for dimension_order, dimension in enumerate((type_dimension, brand_dimension)):
                    config = await _one(db, ServiceJobDimension, master_service_id=service.id,
                                        job_type_id=job_type.id, dimension_id=dimension.id)
                    if not config:
                        config = ServiceJobDimension(master_service_id=service.id,
                                                     job_type_id=job_type.id,
                                                     dimension_id=dimension.id)
                        db.add(config)
                    config.enabled = config.required = config.ask_customer = True
                    config.show_during_tenant_setup = config.use_for_matching = True
                    config.affects_price = config.allow_tenant_override = spec["job"] != "repair"
                    config.allow_all_coverage = config.allow_selected_coverage = True
                    config.allow_exclusion_coverage = True
                    config.display_order = dimension_order

                await _ensure_question(db, service, job_type, "equipment_type",
                                       f"What type of {group_spec['name'].lower()} is it?",
                                       "single_select", 0, dimension=type_dimension)
                await _ensure_question(db, service, job_type, "brand", "Which brand is it?",
                                       "single_select", 1, dimension=brand_dimension)
                for question_order, (key, label, input_type, options) in enumerate(spec["questions"], start=2):
                    await _ensure_question(db, service, job_type, key, label, input_type,
                                           question_order, options=options)

                for issue_order, (code, name, severity) in enumerate(spec["issues"]):
                    issue_slug = f"{spec['slug']}-{code}"
                    issue = await _one(db, MasterIssueType, slug=issue_slug)
                    if not issue:
                        issue = MasterIssueType(category_id=category.id, master_service_id=service.id,
                                                code=f"{spec['slug']}_{code}".upper(), name=name,
                                                slug=issue_slug, severity=severity, is_active=True,
                                                display_order=issue_order, vertical_type="home_services",
                                                status="active", requires_description=spec["job"] == "repair",
                                                customer_visible=True)
                        db.add(issue)
                        await db.flush()
                    else:
                        issue.category_id, issue.master_service_id = category.id, service.id
                        issue.name, issue.severity = name, severity
                        issue.is_active, issue.status, issue.customer_visible = True, "active", True
                        issue.display_order = issue_order
                    issue_mapping = (await db.execute(select(ServiceIssueMapping).where(
                        ServiceIssueMapping.master_service_id == service.id,
                        ServiceIssueMapping.issue_type_id == issue.id,
                        ServiceIssueMapping.deleted_at.is_(None),
                    ))).scalars().first()
                    if not issue_mapping:
                        db.add(ServiceIssueMapping(master_service_id=service.id,
                                                   issue_type_id=issue.id,
                                                   job_type_id=job_type.id, status="active",
                                                   is_common=issue_order < 3,
                                                   is_default=issue_order == 0,
                                                   customer_visible=True,
                                                   requires_description=spec["job"] == "repair",
                                                   display_order=issue_order))
                    else:
                        issue_mapping.job_type_id, issue_mapping.status = job_type.id, "active"
                        issue_mapping.customer_visible, issue_mapping.display_order = True, issue_order

                blueprint = (await db.execute(select(ServiceBlueprintVersion).where(
                    ServiceBlueprintVersion.master_service_id == service.id,
                    ServiceBlueprintVersion.status == "published",
                ).order_by(ServiceBlueprintVersion.version_number.desc()))).scalars().first()
                if not blueprint:
                    db.add(ServiceBlueprintVersion(master_service_id=service.id,
                                                   version_number=1, status="published",
                                                   snapshot={"job_type": spec["job"], "requires_type": True,
                                                             "requires_brand": True,
                                                             "pricing_model": service.pricing_model,
                                                             "is_active": True},
                                                   change_summary="Canonical appliance setup contract",
                                                   published_at=NOW()))
                service_context[spec["slug"]] = (service, job_type, link, spec, group_spec["name"])

        await db.commit()

    async with session_factory() as db:
        writer = JobTypeBlueprintService(db)
        for slug, (service, job_type, _link, spec, _group_name) in service_context.items():
            rule = _workflow_rule(spec["job"])
            steps, transitions = _workflow_journey(
                quote_approval_required=rule["quote_approval_required"],
            )
            await writer.set_workflow(service.id, job_type.id, {
                **rule,
                "schedule_required": True,
                "address_required": True,
                "technician_required": True,
                "service_area_required": True,
                "availability_required": True,
                "steps": steps,
                "transitions": transitions,
            })

    async with session_factory() as db:
        for slug, (service, job_type, _link, spec, group_name) in service_context.items():
            workflow = (await db.execute(select(ServiceJobWorkflow).where(
                ServiceJobWorkflow.master_service_id == service.id,
                ServiceJobWorkflow.job_type_id == job_type.id,
                ServiceJobWorkflow.is_current.is_(True),
                ServiceJobWorkflow.status == "published",
            ))).scalar_one()
            link = await _one(db, MasterServiceJobType, master_service_id=service.id,
                              job_type_id=job_type.id)
            await _ensure_checklist(
                db, slug, service, link, workflow,
                sections=_checklist_sections(group_name, spec["name"], spec["job"]),
            )
        await db.commit()

    await engine.dispose()
    service_count = sum(len(group["services"]) for group in CATALOG.values())
    problem_count = sum(len(service["issues"]) for group in CATALOG.values() for service in group["services"])
    question_count = sum(len(service["questions"]) + 2 for group in CATALOG.values() for service in group["services"])
    print(f"Configured {len(CATALOG)} appliance groups and {service_count} services")
    print(f"Published {problem_count} problems, {question_count} customer questions, {service_count} workflows and {service_count} checklists")


if __name__ == "__main__":
    asyncio.run(configure())
