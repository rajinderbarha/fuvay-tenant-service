"""Seed INSPECTION checklists for every job type whose blueprint inspects.

Note this is NOT the same thing as scripts/seed_checklists.py, which seeds
`MasterChecklistItem` -- a separate, older table that the technician mobile
app never reads. The app resolves its checklists through the checklist_catalog
engine (ChecklistTemplate -> ChecklistTemplateVersion -> JobTypeChecklistMapping),
and that is what this script fills. Running the other script and expecting a
technician to see a checklist is the trap this one exists to close.

Why it is needed: `_next_required_action` sends a technician to the Inspection
screen whenever the job's blueprint sets `inspection_required`. If no checklist
is mapped for that exact (master service, job type) pair, the screen has
nothing to show. The projection now still lets the inspection be completed, so
this is no longer a dead end -- but an inspection with no checklist records
nothing, which is the whole point of the step.

Idempotent: a job type that already has an active inspection-phase mapping is
skipped, so re-running adds only what is missing.

Run: python scripts/seed_inspection_checklists.py [--dry-run]
"""
import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.engines.admin_catalog.models import (
    JobTypeDefinition, MasterService, MasterServiceJobType, ServiceJobWorkflow,
)
from app.engines.checklist_catalog import constants as c, service as svc
from app.engines.checklist_catalog.models import JobTypeChecklistMapping

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://serviceos:serviceos@localhost:5432/serviceos")

#: Closing steps every inspection shares -- name the fault, say what it needs,
#: show the customer. These are what turn an inspection into a quotable finding.
CLOSING = [
    "Faulty part or root cause identified",
    "Replacement parts required noted",
    "Photographed the fault and affected area",
    "Explained the finding and likely cost to the customer",
]

#: Keyed by master service name. A service not listed here gets GENERIC below,
#: and the run prints which ones did so an admin can write the real checks.
CHECKS = {
    "Air Conditioner": [
        "Confirmed the fault the customer reported",
        "Power supply, plug and MCB checked",
        "Indoor and outdoor units inspected for damage",
        "Refrigerant gas pressure checked",
        "Cooling and airflow tested",
        "Filters, coil and drainage inspected",
    ],
    "Refrigerator": [
        "Confirmed the fault the customer reported",
        "Power supply and plug checked",
        "Compressor operation checked",
        "Cooling tested in both freezer and fridge compartments",
        "Door gasket and seal inspected",
        "Thermostat, defrost and drainage checked",
    ],
    "Washing Machine": [
        "Confirmed the fault the customer reported",
        "Power supply and water inlet checked",
        "Drum rotation and motor operation tested",
        "Drain pump and filter inspected",
        "Inlet valve and hoses checked for blockage or leak",
        "Door lock, lid switch and control panel tested",
    ],
    "Television": [
        "Confirmed the fault the customer reported",
        "Power supply and adapter checked",
        "Display panel inspected for cracks or damage",
        "Picture and sound output tested",
        "HDMI, cable and other ports checked",
        "Remote and panel controls tested",
    ],
    "Laptop": [
        "Confirmed the fault the customer reported",
        "Warned the customer to back up data before any repair",
        "Power adapter and battery checked",
        "Boot and POST tested",
        "Display, keyboard and trackpad tested",
        "Storage and memory checked",
        "Fan, vents and overheating checked",
    ],
    "Desktop Computer": [
        "Confirmed the fault the customer reported",
        "Warned the customer to back up data before any repair",
        "Power supply and cabling checked",
        "Boot and POST tested",
        "Monitor, keyboard and mouse tested",
        "Storage and memory checked",
        "Fan, vents and overheating checked",
    ],
    "Printer": [
        "Confirmed the fault the customer reported",
        "Power and connectivity (USB, network or Wi-Fi) checked",
        "Paper tray, feed path and rollers inspected",
        "Cartridge or toner level and seating checked",
        "Test page printed and print quality assessed",
        "Error codes and indicator lights noted",
    ],
    "Plumbing": [
        "Confirmed the fault the customer reported",
        "Water supply and pressure checked",
        "Source of the leak or blockage located",
        "Pipes, joints and fittings inspected",
        "Drainage and outflow tested",
        "Taps, valves and flush mechanism tested",
        "Any wall, floor or ceiling damage recorded",
    ],
    "Geyser / Water Heater": [
        "Confirmed the fault the customer reported",
        "Power supply and MCB checked",
        "Heating element checked",
        "Thermostat tested",
        "Water inlet, outlet and pressure checked",
        "Tank and connections inspected for leaks",
        "Safety valve and earthing checked",
    ],
    "Kitchen Chimney": [
        "Confirmed the fault the customer reported",
        "Power supply and switch checked",
        "Motor and fan operation tested",
        "Suction performance tested",
        "Filters inspected and grease build-up assessed",
        "Ducting and exhaust outlet checked",
        "Lights and control panel tested",
    ],
    "Microwave Oven": [
        "Confirmed the fault the customer reported",
        "Power supply and plug checked",
        "Door interlock switches and seal inspected",
        "Heating tested with a water load",
        "Turntable, motor and control panel tested",
        "Interior inspected for arcing or damage",
    ],
    "Fan & Light": [
        "Confirmed the fault the customer reported",
        "Supply isolated at the switch or MCB before inspection",
        "Switch, regulator and wiring connections inspected",
        "Fan motor and blade balance checked",
        "Light fitting, holder and bulb checked",
        "Mounting, fixing and safety clearance checked",
    ],
    "MCB & Electrical Panel": [
        "Confirmed the fault the customer reported",
        "Main supply isolated and confirmed dead before opening the panel",
        "Panel inspected for burn marks, heat damage and loose terminals",
        "MCB and RCCB tripping operation tested",
        "Circuit loading and cable sizing checked",
        "Earthing and neutral connections checked",
    ],
    "Switch, Socket & Wiring": [
        "Confirmed the fault the customer reported",
        "Supply isolated and confirmed dead before inspection",
        "Switch and socket inspected for burn marks or damage",
        "Wiring, termination and junction boxes checked",
        "Continuity and earthing tested",
        "Connected load checked against the circuit rating",
    ],
    "CCTV Camera": [
        "Confirmed the fault the customer reported",
        "Power supply and adapter checked",
        "Camera lens, housing and mounting inspected",
        "Cabling and connectors checked end to end",
        "DVR / NVR, storage and recording checked",
        "Network and remote viewing tested",
    ],
    "Video Door Bell & Smart Lock": [
        "Confirmed the fault the customer reported",
        "Power supply or battery level checked",
        "Unit, mounting and weather sealing inspected",
        "Wiring and connections checked",
        "App pairing and network connectivity tested",
        "Lock mechanism and access methods tested",
    ],
    "WiFi Router & Networking": [
        "Confirmed the fault the customer reported",
        "Power adapter and indicator lights checked",
        "Incoming internet line and ISP link verified",
        "Router configuration and credentials checked",
        "Cabling and LAN ports checked",
        "Signal coverage and speed tested in the affected area",
        "Connected devices tested",
    ],
    "RO Water Purifier": [
        "Confirmed the fault the customer reported",
        "Power supply and adapter checked",
        "Inlet water supply and pressure checked",
        "Filter cartridges and RO membrane condition inspected",
        "Pump and solenoid valve tested",
        "Storage tank and tubing inspected for leaks",
        "Purified water flow rate and TDS level tested",
        "UV or UF stage checked where fitted",
    ],
    "Furniture Repair & Assembly": [
        "Confirmed the fault the customer reported",
        "Item inspected and existing damage recorded",
        "Joints, hinges and fittings checked",
        "Structural stability and load bearing checked",
        "Surface and finish damage noted",
        "Hardware and materials required noted",
        "Working space and access checked",
    ],
}

GENERIC = [
    "Confirmed the fault the customer reported",
    "Power, water or other supply to the unit checked",
    "Unit inspected for visible damage",
    "Operation tested and symptoms recorded",
]


def code_for(service_name: str, job_type_key: str) -> str:
    slug = "".join(ch if ch.isalnum() else "-" for ch in service_name.upper())
    while "--" in slug:
        slug = slug.replace("--", "-")
    suffix = "".join(ch if ch.isalnum() else "-" for ch in (job_type_key or "").upper())
    return f"INSP-{slug.strip('-')}-{suffix.strip('-') or 'JOB'}"[:80]


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="print what would be created")
    args = parser.parse_args()

    engine = create_async_engine(DATABASE_URL)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    created, skipped, generic = 0, 0, []
    async with factory() as db:
        # Every blueprint that inspects. `pricing_behavior` counts alongside the
        # boolean for the same reason the runtime does: a workflow priced only
        # after diagnosis inspects by definition.
        workflows = (await db.execute(
            select(ServiceJobWorkflow).where(ServiceJobWorkflow.is_current.is_(True))
        )).scalars().all()
        inspecting = [w for w in workflows
                      if w.inspection_required or w.pricing_behavior == "inspection_required"]

        for workflow in inspecting:
            link = (await db.execute(select(MasterServiceJobType).where(
                MasterServiceJobType.master_service_id == workflow.master_service_id,
                MasterServiceJobType.job_type_id == workflow.job_type_id,
                MasterServiceJobType.is_active.is_(True),
            ))).scalars().first()
            if link is None:
                continue  # blueprint with no active catalog link -- nothing to map to

            existing = (await db.execute(select(JobTypeChecklistMapping).where(
                JobTypeChecklistMapping.master_service_job_type_id == link.id,
                JobTypeChecklistMapping.phase == c.PURPOSE_INSPECTION.lower(),
                JobTypeChecklistMapping.status == c.MAPPING_STATUS_ACTIVE,
            ))).scalars().first()
            if existing is not None:
                skipped += 1
                continue

            service = await db.get(MasterService, workflow.master_service_id)
            job_type = await db.get(JobTypeDefinition, workflow.job_type_id)
            if service is None or job_type is None:
                continue
            service_name = service.service_name
            jt_label = job_type.label or job_type.key

            items = CHECKS.get(service_name)
            if items is None:
                items = GENERIC
                generic.append(f"{service_name} / {jt_label}")
            items = items + CLOSING

            name = f"{service_name} {jt_label} - Inspection"
            code = code_for(service_name, job_type.key)
            if args.dry_run:
                print(f"  would create  {name}  ({len(items)} items, code={code})")
                created += 1
                continue

            template = await svc.create_template(
                db, name=name, code=code, description=None,
                purpose=c.PURPOSE_INSPECTION, owner_scope=c.OWNER_SCOPE_PLATFORM,
                tenant_id=None, created_by_user_id=None,
            )
            version = await svc.get_draft_version(db, template.id)
            section = await svc.add_section(db, version, "Checklist", display_order=0)
            for index, label in enumerate(items):
                await svc.add_item(db, section, version, item_type=c.ITEM_TYPE_CHECKBOX,
                                   label=label, is_required=True, display_order=index)
            await svc.publish_version(db, version, published_by=None,
                                      change_summary="Seeded inspection checklist")
            await svc.create_mapping(
                db, master_service_job_type_id=link.id, service_job_workflow_id=None,
                checklist_template_version_id=version.id,
                phase=c.PURPOSE_INSPECTION, usage=c.USAGE_REQUIRED, actor=c.ACTOR_TECHNICIAN,
                # The technician must actually diagnose before the inspection
                # can close; this is the gate INSPECTION permits for that.
                completion_gate=c.GATE_BEFORE_INSPECTION_COMPLETE,
                condition_rules=None, display_order=0, created_by=None,
            )
            await db.commit()
            print(f"  created  {name}  ({len(items)} items)")
            created += 1

    await engine.dispose()
    print(f"\ncreated: {created}  already mapped: {skipped}")
    if generic:
        print("\nThese got the generic checklist -- write real checks for them:")
        for entry in generic:
            print("  -", entry)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
