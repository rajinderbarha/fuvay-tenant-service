"""Idempotently publish the complete Air Conditioning catalog contract.

This is platform-owned structure only: services, job-type workflows,
dimensions, allowed brands/types, customer questions, problems and technician
completion checklists. Providers remain the sole owners of all price amounts.

Run::

    python scripts/configure_ac_catalog.py
"""
from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
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
    CatalogQuestion,
    CatalogQuestionOption,
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
    TenantService,
    TenantServiceBrand,
    TenantServiceType,
)
from app.engines.checklist_catalog.models import (
    ChecklistItem,
    ChecklistSection,
    ChecklistTemplate,
    ChecklistTemplateVersion,
    JobTypeChecklistMapping,
)
from app.engines.entitlement.service import entitlement_service
from app.engines.tenant_engine.models import Tenant


NOW = lambda: datetime.now(timezone.utc)
AC_GROUP_SLUG = "ac_services"
AC_GROUP_ICON_URL = "https://res.cloudinary.com/dr1b4ezct/image/upload/v1787511005/serviceos/customer-home/service-groups/946f4a221bb1ed857f466041.png.png"
AC_SERVICE_JOB_TYPES = {
    "ac_repair": "repair",
    "ac_installation": "installation",
    "ac_maintenance": "service",
    "ac_gas_refill": "service",
}
AC_TYPE_SLUGS = ("split_ac", "window_ac", "cassette_ac", "tower_ac")
AC_BRAND_SLUGS = (
    "lg", "samsung", "voltas", "blue-star", "daikin", "hitachi",
    "carrier", "lloyd", "o-general", "panasonic", "haier",
)


def _step(key, name, status, app, role, order, *, customer=False, tenant=False,
          staff=False, photo=False, note=False, sla=None):
    return {
        "step_key": key,
        "step_name": name,
        "maps_to_status": status,
        "owner_app": app,
        "owner_role": role,
        "customer_visible": customer,
        "tenant_visible": tenant,
        "staff_visible": staff,
        "admin_visible": True,
        "requires_note": note,
        "requires_photo": photo,
        "requires_approval": False,
        "sla_minutes": sla,
        "display_order": order,
    }


WORKFLOW_STEPS = [
    _step("booking_created", "Booking Created", None, "customer_app", "customer", 1, customer=True),
    _step("provider_accepted", "Provider Accepted", None, "tenant_app", "tenant_owner", 2,
          customer=True, tenant=True, sla=30),
    _step("technician_assigned", "Technician Assigned", "assigned", "tenant_app", "tenant_manager", 3,
          customer=True, tenant=True, staff=True),
    _step("technician_accepted", "Technician Accepted", "accepted", "staff_app", "technician", 4,
          tenant=True, staff=True),
    _step("on_the_way", "On The Way", "on_the_way", "staff_app", "technician", 5,
          customer=True, tenant=True, staff=True),
    _step("arrived", "Arrived", "reached_site", "staff_app", "technician", 6,
          customer=True, tenant=True, staff=True),
    _step("inspection_started", "Inspection Started", "inspection_started", "staff_app", "technician", 7,
          tenant=True, staff=True),
    _step("inspection_done", "Inspection Complete", "inspection_done", "staff_app", "technician", 8,
          tenant=True, staff=True, note=True),
    _step("work_started", "Work Started", "service_started", "staff_app", "technician", 9,
          tenant=True, staff=True),
    _step("work_completed", "Work Completed", "work_done", "staff_app", "technician", 10,
          customer=True, tenant=True, staff=True, photo=True, note=True),
    _step("job_completed", "Job Completed", "completed", "system", "system", 11,
          customer=True, tenant=True, staff=True),
    _step("review_requested", "Review Requested", None, "customer_app", "customer", 12,
          customer=True),
]

WORKFLOW_TRANSITIONS = [
    {"from_step_key": "booking_created", "to_step_key": "provider_accepted", "action_label": "Accept Booking", "allowed_role": "tenant_owner", "requires_reason": False, "triggers_notification": True, "auto_transition": False},
    {"from_step_key": "provider_accepted", "to_step_key": "technician_assigned", "action_label": "Assign Technician", "allowed_role": "tenant_manager", "requires_reason": False, "triggers_notification": True, "auto_transition": False},
    {"from_step_key": "technician_assigned", "to_step_key": "technician_accepted", "action_label": "Accept Job", "allowed_role": "technician", "requires_reason": False, "triggers_notification": False, "auto_transition": False},
    {"from_step_key": "technician_accepted", "to_step_key": "on_the_way", "action_label": "Start Travel", "allowed_role": "technician", "requires_reason": False, "triggers_notification": True, "auto_transition": False},
    {"from_step_key": "on_the_way", "to_step_key": "arrived", "action_label": "Mark Arrived", "allowed_role": "technician", "requires_reason": False, "triggers_notification": False, "auto_transition": False},
    {"from_step_key": "arrived", "to_step_key": "inspection_started", "action_label": "Start Inspection", "allowed_role": "technician", "requires_reason": False, "triggers_notification": False, "auto_transition": False},
    {"from_step_key": "inspection_started", "to_step_key": "inspection_done", "action_label": "Finish Inspection", "allowed_role": "technician", "requires_reason": False, "triggers_notification": False, "auto_transition": False},
    {"from_step_key": "inspection_done", "to_step_key": "work_started", "action_label": "Start Work", "allowed_role": "technician", "requires_reason": False, "triggers_notification": False, "auto_transition": False},
    {"from_step_key": "work_started", "to_step_key": "work_completed", "action_label": "Complete Work", "allowed_role": "technician", "requires_reason": False, "triggers_notification": True, "auto_transition": False},
    # The assigned technician explicitly finalizes after completion proof,
    # customer handover, and direct-payment reconciliation. This is not an
    # automatic system transition; authoring it as system-only made the staff
    # app's real Finalize action impossible to complete.
    {"from_step_key": "work_completed", "to_step_key": "job_completed", "action_label": "Finalize Job", "allowed_role": "technician", "requires_reason": False, "triggers_notification": True, "auto_transition": False},
    {"from_step_key": "job_completed", "to_step_key": "review_requested", "action_label": "Request Review", "allowed_role": "system", "requires_reason": False, "triggers_notification": True, "auto_transition": True},
]


def _workflow_journey(*, quote_approval_required: bool) -> tuple[list[dict], list[dict]]:
    """Return a runtime-valid journey for the workflow capability flags.

    Inspection-first services must expose the estimate gate in every app.
    Keeping this construction beside the catalog content prevents a future
    re-run from publishing the pre-migration journey that skipped directly
    from inspection to work while the backend still required approval.
    """
    steps = [dict(step) for step in WORKFLOW_STEPS]
    transitions = [dict(transition) for transition in WORKFLOW_TRANSITIONS]
    if not quote_approval_required:
        # Fixed-price installation and maintenance have no diagnostic quote
        # gate. Keeping inspection_started/inspection_done in those journeys
        # made the runtime contradict the published blueprint and forced a
        # technician through two meaningless repair-only screens.
        inspection_keys = {"inspection_started", "inspection_done"}
        steps = [step for step in steps if step["step_key"] not in inspection_keys]
        transitions = [
            transition for transition in transitions
            if transition["from_step_key"] not in inspection_keys
            and transition["to_step_key"] not in inspection_keys
        ]
        transitions.append({
            "from_step_key": "arrived", "to_step_key": "work_started",
            "action_label": "Start Work", "allowed_role": "technician",
            "requires_reason": False, "triggers_notification": False,
            "auto_transition": False,
        })
        for order, step in enumerate(steps, start=1):
            step["display_order"] = order
        return steps, transitions

    insertion = next(
        index + 1 for index, step in enumerate(steps)
        if step.get("maps_to_status") == "inspection_done"
    )
    steps.insert(insertion, _step(
        "estimate_approval", "Estimate Approval", "quote_required",
        "customer_app", "customer", insertion + 1,
        customer=True, tenant=True, staff=True,
    ) | {"requires_approval": True})
    for order, step in enumerate(steps, start=1):
        step["display_order"] = order

    transitions = [
        transition for transition in transitions
        if not (
            transition["from_step_key"] == "inspection_done"
            and transition["to_step_key"] == "work_started"
        )
    ]
    transitions.extend([
        {"from_step_key": "inspection_done", "to_step_key": "estimate_approval", "action_label": "Submit Estimate", "allowed_role": "technician", "requires_reason": False, "triggers_notification": True, "auto_transition": False},
        # Quote approval is recorded by the dedicated customer quote endpoint;
        # the job remains at quote_required until the assigned technician
        # starts the approved work. Making this transition customer-owned made
        # the staff app impossible to advance after a valid approval.
        {"from_step_key": "estimate_approval", "to_step_key": "work_started", "action_label": "Start Approved Work", "allowed_role": "technician", "requires_reason": False, "triggers_notification": True, "auto_transition": False},
    ])
    return steps, transitions

WORKFLOW_RULES = {
    "ac_repair": dict(inspection_required=True, quote_approval_required=True,
                      checklist_required=True, pricing_behavior="inspection_required"),
    "ac_installation": dict(inspection_required=False, quote_approval_required=False,
                            checklist_required=True, pricing_behavior="fixed"),
    "ac_maintenance": dict(inspection_required=False, quote_approval_required=False,
                           checklist_required=True, pricing_behavior="fixed"),
    "ac_gas_refill": dict(inspection_required=True, quote_approval_required=True,
                          checklist_required=True, pricing_behavior="inspection_required"),
}

ISSUES = {
    "ac_repair": [
        ("not_cooling", "AC is not cooling", "high"),
        ("water_leakage", "Water leakage", "medium"),
        ("unusual_noise", "Unusual noise or vibration", "medium"),
        ("not_starting", "AC is not starting", "high"),
        ("remote_control", "Remote or control problem", "low"),
        ("bad_smell", "Bad smell from the unit", "medium"),
        ("frequent_cycling", "Frequently turning on and off", "medium"),
        ("ice_formation", "Ice formation on the unit", "high"),
    ],
    "ac_installation": [
        ("new_installation", "New AC installation", "low"),
        ("relocation_installation", "Install an AC moved from another location", "medium"),
    ],
    "ac_maintenance": [
        ("routine_service", "Routine AC servicing", "low"),
        ("deep_cleaning", "Deep cleaning", "low"),
        ("seasonal_tuneup", "Seasonal performance tune-up", "low"),
    ],
    "ac_gas_refill": [
        ("low_cooling_gas", "Low cooling or suspected low refrigerant", "high"),
        ("leak_test_refill", "Leak test and refrigerant refill", "high"),
    ],
}

QUESTIONS = {
    "ac_repair": [
        ("unit_powering_on", "Is the AC powering on?", "single_select", [("yes", "Yes"), ("no", "No"), ("intermittent", "Sometimes")]),
        ("issue_duration", "How long have you noticed this problem?", "single_select", [("today", "Started today"), ("few_days", "A few days"), ("few_weeks", "A few weeks"), ("longer", "More than a month")]),
        ("problem_details", "Describe any sounds, leaks, smells, or error code you noticed.", "text", []),
    ],
    "ac_installation": [
        ("installation_location", "Where will the AC be installed?", "single_select", [("bedroom", "Bedroom"), ("living_room", "Living room"), ("office", "Office"), ("shop", "Shop or commercial space"), ("other", "Other")]),
        ("existing_unit", "Is an existing AC being replaced?", "single_select", [("yes", "Yes"), ("no", "No")]),
        ("power_point_ready", "Is the electrical point ready near the installation location?", "single_select", [("yes", "Yes"), ("no", "No"), ("unsure", "Not sure")]),
    ],
    "ac_maintenance": [
        ("last_service", "When was the AC last serviced?", "single_select", [("under_3_months", "Less than 3 months ago"), ("3_to_6_months", "3–6 months ago"), ("6_to_12_months", "6–12 months ago"), ("over_12_months", "More than a year ago"), ("unknown", "I don't know")]),
        ("maintenance_goal", "What do you need from this service?", "single_select", [("routine", "Routine servicing"), ("deep_clean", "Deep cleaning"), ("performance", "Cooling performance check")]),
    ],
    "ac_gas_refill": [
        ("cooling_level", "How is the AC cooling now?", "single_select", [("none", "Not cooling"), ("low", "Cooling is weak"), ("intermittent", "Cooling is intermittent")]),
        ("previous_refill", "Has refrigerant been refilled in the last 12 months?", "single_select", [("yes", "Yes"), ("no", "No"), ("unknown", "I don't know")]),
        ("visible_ice", "Can you see ice on the indoor unit or pipes?", "single_select", [("yes", "Yes"), ("no", "No"), ("unsure", "Not sure")]),
    ],
}

CHECKLISTS = {
    "ac_repair": [
        ("Safety & Preparation", [
            ("YES_NO", "Power isolated before opening the unit", True, False, None),
            ("CHECKBOX", "Work area protected", True, False, None),
        ]),
        ("Diagnosis & Repair", [
            ("LONG_TEXT", "Diagnosis and root cause", True, False, None),
            ("SHORT_TEXT", "Parts repaired or replaced", False, False, None),
            ("MEASUREMENT", "Supply-air temperature after repair", False, False, "°C"),
        ]),
        ("Completion Evidence", [
            ("YES_NO", "Cooling and controls tested", True, False, None),
            ("PHOTO", "Photo of completed repair", True, True, None),
            ("SIGNATURE", "Customer sign-off", True, True, None),
        ]),
    ],
    "ac_installation": [
        ("Safety & Site", [
            ("YES_NO", "Mounting location and load safety verified", True, False, None),
            ("YES_NO", "Electrical supply and earthing verified", True, False, None),
        ]),
        ("Installation", [
            ("YES_NO", "Indoor and outdoor units securely mounted", True, False, None),
            ("YES_NO", "Drain line slope and leak test completed", True, False, None),
            ("YES_NO", "Vacuuming and refrigerant line test completed", True, False, None),
        ]),
        ("Handover", [
            ("YES_NO", "Cooling and remote functions demonstrated", True, False, None),
            ("PHOTO", "Photos of indoor and outdoor installation", True, True, None),
            ("SIGNATURE", "Customer installation sign-off", True, True, None),
        ]),
    ],
    "ac_maintenance": [
        ("Preparation", [
            ("YES_NO", "Power isolated and work area protected", True, False, None),
        ]),
        ("Service Work", [
            ("YES_NO", "Filters and evaporator coil cleaned", True, False, None),
            ("YES_NO", "Drain tray and drain line cleaned", True, False, None),
            ("YES_NO", "Electrical connections and fan checked", True, False, None),
            ("MEASUREMENT", "Supply-air temperature after servicing", False, False, "°C"),
        ]),
        ("Completion", [
            ("YES_NO", "Cooling performance verified", True, False, None),
            ("PHOTO", "Photo of cleaned unit", True, True, None),
            ("SIGNATURE", "Customer service sign-off", True, True, None),
        ]),
    ],
    "ac_gas_refill": [
        ("Safety & Diagnosis", [
            ("YES_NO", "Power and refrigerant handling safety verified", True, False, None),
            ("YES_NO", "Leak inspection completed before refill", True, False, None),
            ("LONG_TEXT", "Leak findings and corrective action", True, False, None),
        ]),
        ("Refrigerant Work", [
            ("MEASUREMENT", "Pressure before refill", True, False, "psi"),
            ("MEASUREMENT", "Pressure after refill", True, False, "psi"),
            ("SHORT_TEXT", "Refrigerant type and quantity used", True, False, None),
        ]),
        ("Completion", [
            ("YES_NO", "Cooling and leak test verified after refill", True, False, None),
            ("PHOTO", "Photo of pressure reading or completed unit", True, True, None),
            ("SIGNATURE", "Customer sign-off", True, True, None),
        ]),
    ],
}


async def _one(db, model, **filters):
    return (await db.execute(select(model).filter_by(**filters))).scalars().first()


async def _ensure_dimension(db, key, name, legacy_source, order):
    row = await _one(db, CatalogDimension, key=key)
    if not row:
        row = CatalogDimension(key=key, name=name, data_type="single_select",
                               legacy_source=legacy_source, is_active=True,
                               display_order=order)
        db.add(row)
        await db.flush()
    else:
        row.name, row.legacy_source, row.is_active = name, legacy_source, True
    return row


async def _ensure_question(db, service, job_type, key, label, input_type,
                           order, *, dimension=None, options=()):
    row = await _one(db, CatalogQuestion, master_service_id=service.id,
                     job_type_id=job_type.id, question_key=key)
    source = "dimension" if dimension else ("free" if input_type == "text" else "static")
    if not row:
        row = CatalogQuestion(master_service_id=service.id, job_type_id=job_type.id,
                              question_key=key, label=label, input_type=input_type,
                              answer_source=source, dimension_id=dimension.id if dimension else None,
                              required=True, customer_visible=True, tenant_setup_visible=False,
                              deepseek_enabled=True, display_order=order, is_active=True)
        db.add(row)
        await db.flush()
    else:
        row.label, row.input_type, row.answer_source = label, input_type, source
        row.dimension_id = dimension.id if dimension else None
        row.required, row.customer_visible, row.deepseek_enabled, row.is_active = True, True, True, True
        row.display_order = order
    for opt_order, (code, option_label) in enumerate(options):
        opt = await _one(db, CatalogQuestionOption, question_id=row.id, code=code)
        if not opt:
            db.add(CatalogQuestionOption(question_id=row.id, code=code, label=option_label,
                                         display_order=opt_order, is_active=True))
        else:
            opt.label, opt.display_order, opt.is_active = option_label, opt_order, True
    return row


async def _ensure_checklist(db, slug, service, link, workflow, *, sections=None):
    code = f"{slug.upper()}_COMPLETION_V1"
    template = await _one(db, ChecklistTemplate, code=code)
    if not template:
        template = ChecklistTemplate(name=f"{service.service_name} - Job Completion", code=code,
                                      description=f"Required technician completion evidence for {service.service_name}.",
                                      purpose="COMPLETION", status="active", owner_scope="PLATFORM")
        db.add(template)
        await db.flush()
    else:
        template.status = "active"
    version = await _one(db, ChecklistTemplateVersion, checklist_template_id=template.id,
                         version_number=1)
    if not version:
        version = ChecklistTemplateVersion(checklist_template_id=template.id, version_number=1,
                                            status="PUBLISHED", change_summary="Canonical AC completion checklist",
                                            published_at=NOW())
        db.add(version)
        await db.flush()
        for section_order, (title, items) in enumerate(sections or CHECKLISTS[slug]):
            section = ChecklistSection(checklist_template_version_id=version.id, title=title,
                                       display_order=section_order)
            db.add(section)
            await db.flush()
            for item_order, (item_type, label, required, evidence, unit) in enumerate(items):
                db.add(ChecklistItem(
                    checklist_section_id=section.id, item_type=item_type, label=label,
                    is_required=required, evidence_required=evidence,
                    min_evidence_count=1 if evidence else 0,
                    max_evidence_count=3 if item_type == "PHOTO" else 1,
                    allowed_file_types=["image/jpeg", "image/png", "image/webp"] if item_type == "PHOTO" else None,
                    measurement_unit=unit, display_order=item_order,
                    failure_behavior="BLOCK" if required else None,
                    customer_visible=item_type == "SIGNATURE",
                ))
    else:
        version.status = "PUBLISHED"

    # One authoritative active completion checklist per AC job type.
    old_mappings = (await db.execute(select(JobTypeChecklistMapping).where(
        JobTypeChecklistMapping.master_service_job_type_id == link.id,
    ))).scalars().all()
    for old in old_mappings:
        old.status = "active" if (
            old.checklist_template_version_id == version.id and old.phase == "EXECUTION"
        ) else "inactive"
    mapping = next((m for m in old_mappings if (
        m.checklist_template_version_id == version.id and m.phase == "EXECUTION"
    )), None)
    if not mapping:
        mapping = JobTypeChecklistMapping(
            master_service_job_type_id=link.id,
            service_job_workflow_id=workflow.id,
            checklist_template_version_id=version.id,
            phase="EXECUTION", usage="REQUIRED", actor="TECHNICIAN",
            completion_gate="REQUIRE_BEFORE_JOB_COMPLETION", status="active",
        )
        db.add(mapping)
    else:
        mapping.service_job_workflow_id = workflow.id
        mapping.usage, mapping.actor = "REQUIRED", "TECHNICIAN"
        mapping.completion_gate, mapping.status = "REQUIRE_BEFORE_JOB_COMPLETION", "active"


async def configure() -> None:
    engine = create_engine()
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as db:
        category = (await db.execute(select(ServiceCategory).where(
            ServiceCategory.vertical_type == "home_services",
            ServiceCategory.is_active.is_(True),
        ))).scalars().first()
        if not category:
            raise RuntimeError("Active Home Services category is missing")
        group = (await db.execute(select(ServiceGroup).where(
            ServiceGroup.category_id == category.id,
            ServiceGroup.slug == AC_GROUP_SLUG,
            ServiceGroup.deleted_at.is_(None),
        ))).scalar_one_or_none()
        if not group:
            raise RuntimeError("Active AC & HVAC service group is missing")
        group.status = "active"
        group.icon_url = AC_GROUP_ICON_URL

        type_dimension = await _ensure_dimension(db, "type", "Equipment Type", "service_types", 10)
        brand_dimension = await _ensure_dimension(db, "brand", "Brand", "brands", 20)

        types = (await db.execute(select(ServiceType).where(
            ServiceType.slug.in_(AC_TYPE_SLUGS), ServiceType.is_active.is_(True),
            ServiceType.deleted_at.is_(None),
        ))).scalars().all()
        brands = (await db.execute(select(Brand).where(
            Brand.slug.in_(AC_BRAND_SLUGS), Brand.is_active.is_(True),
            Brand.deleted_at.is_(None),
        ))).scalars().all()
        if len(types) != len(AC_TYPE_SLUGS):
            raise RuntimeError(f"Expected {len(AC_TYPE_SLUGS)} AC types; found {len(types)}")
        if len(brands) != len(AC_BRAND_SLUGS):
            raise RuntimeError(f"Expected {len(AC_BRAND_SLUGS)} AC brands; found {len(brands)}")

        services = {}
        links = {}
        for order, (slug, job_key) in enumerate(AC_SERVICE_JOB_TYPES.items()):
            service = await _one(db, MasterService, slug=slug)
            job_type = await _one(db, JobTypeDefinition, key=job_key)
            if not service or not job_type:
                raise RuntimeError(f"Missing service/job type: {slug}/{job_key}")
            service.category_id, service.service_group_id = category.id, group.id
            service.job_type, service.job_type_id = job_key, job_type.id
            service.is_active, service.deleted_at = True, None
            service.requires_checklist = True
            service.is_brand_required = True
            service.is_type_required = True
            service.requires_issue_type = True
            service.requires_schedule = True
            service.requires_address = True
            service.tenant_override_allowed = True
            service.display_order = order
            link = await _one(db, MasterServiceJobType, master_service_id=service.id,
                              job_type_id=job_type.id)
            if not link:
                link = MasterServiceJobType(master_service_id=service.id, job_type_id=job_type.id,
                                            is_active=True, display_order=0)
                db.add(link)
                await db.flush()
            else:
                link.is_active = True
            services[slug] = (service, job_type)
            links[slug] = link

            for idx, service_type in enumerate(types):
                mapping = await _one(db, ServiceTypeMapping, type_id=service_type.id,
                                     category_id=category.id, service_group_id=group.id,
                                     service_id=service.id)
                if not mapping:
                    db.add(ServiceTypeMapping(type_id=service_type.id, category_id=category.id,
                                              service_group_id=group.id, service_id=service.id,
                                              customer_visible=True, provider_visible=True,
                                              status="active", display_order=idx))
                else:
                    mapping.status, mapping.customer_visible, mapping.provider_visible = "active", True, True
                    mapping.display_order = idx
                runtime_mapping = await _one(
                    db, MasterServiceType,
                    master_service_id=service.id, service_type_id=service_type.id,
                )
                if not runtime_mapping:
                    db.add(MasterServiceType(
                        master_service_id=service.id,
                        service_type_id=service_type.id,
                        is_required=False,
                        is_default=False,
                        is_active=True,
                    ))
                else:
                    runtime_mapping.is_active = True
            for idx, brand in enumerate(brands):
                mapping = await _one(db, BrandMapping, brand_id=brand.id,
                                     category_id=category.id, service_group_id=group.id,
                                     service_id=service.id)
                if not mapping:
                    db.add(BrandMapping(brand_id=brand.id, category_id=category.id,
                                        service_group_id=group.id, service_id=service.id,
                                        customer_visible=True, provider_visible=True,
                                        status="active", display_order=idx))
                else:
                    mapping.status, mapping.customer_visible, mapping.provider_visible = "active", True, True
                    mapping.display_order = idx
                runtime_mapping = await _one(
                    db, MasterServiceBrand,
                    master_service_id=service.id, brand_id=brand.id,
                )
                if not runtime_mapping:
                    db.add(MasterServiceBrand(
                        master_service_id=service.id,
                        brand_id=brand.id,
                        is_required=False,
                        is_default=False,
                        is_active=True,
                        status="active",
                        display_order=idx,
                        can_override_price=True,
                        is_routing_only=False,
                    ))
                else:
                    runtime_mapping.is_active = True
                    runtime_mapping.status = "active"
                    runtime_mapping.display_order = idx
                    runtime_mapping.can_override_price = True

            for dim_order, dimension in enumerate((type_dimension, brand_dimension)):
                cfg = await _one(db, ServiceJobDimension, master_service_id=service.id,
                                 job_type_id=job_type.id, dimension_id=dimension.id)
                if not cfg:
                    cfg = ServiceJobDimension(master_service_id=service.id, job_type_id=job_type.id,
                                              dimension_id=dimension.id)
                    db.add(cfg)
                cfg.enabled = cfg.required = cfg.ask_customer = cfg.show_during_tenant_setup = True
                cfg.use_for_matching = True
                dimension_affects_price = WORKFLOW_RULES[slug]["pricing_behavior"] not in {
                    "inspection_required", "custom_quote",
                }
                cfg.affects_price = dimension_affects_price
                cfg.allow_tenant_override = dimension_affects_price
                cfg.allow_all_coverage = cfg.allow_selected_coverage = cfg.allow_exclusion_coverage = True
                cfg.display_order = dim_order

            await _ensure_question(db, service, job_type, "ac_type", "What type of AC is it?",
                                   "single_select", 0, dimension=type_dimension)
            await _ensure_question(db, service, job_type, "brand", "Which AC brand is it?",
                                   "single_select", 1, dimension=brand_dimension)
            for q_order, (key, label, input_type, options) in enumerate(QUESTIONS[slug], start=2):
                await _ensure_question(db, service, job_type, key, label, input_type,
                                       q_order, options=options)

            for issue_order, (code, name, severity) in enumerate(ISSUES[slug]):
                issue_slug = f"{slug}-{code}"
                issue = await _one(db, MasterIssueType, slug=issue_slug)
                if not issue:
                    issue = MasterIssueType(category_id=category.id, master_service_id=service.id,
                                            code=code.upper(), name=name, slug=issue_slug,
                                            severity=severity, is_active=True, display_order=issue_order,
                                            vertical_type="home_services", status="active",
                                            requires_description=True, customer_visible=True)
                    db.add(issue)
                    await db.flush()
                else:
                    issue.name, issue.severity, issue.is_active, issue.status = name, severity, True, "active"
                    issue.customer_visible, issue.master_service_id = True, service.id
                issue_map = (await db.execute(select(ServiceIssueMapping).where(
                    ServiceIssueMapping.master_service_id == service.id,
                    ServiceIssueMapping.issue_type_id == issue.id,
                    ServiceIssueMapping.deleted_at.is_(None),
                ))).scalars().first()
                if not issue_map:
                    db.add(ServiceIssueMapping(master_service_id=service.id, issue_type_id=issue.id,
                                               job_type_id=job_type.id, status="active",
                                               is_common=issue_order < 3, is_default=issue_order == 0,
                                               customer_visible=True, requires_description=True,
                                               display_order=issue_order))
                else:
                    issue_map.job_type_id, issue_map.status = job_type.id, "active"
                    issue_map.customer_visible, issue_map.display_order = True, issue_order

            published_blueprint = (await db.execute(select(ServiceBlueprintVersion).where(
                ServiceBlueprintVersion.master_service_id == service.id,
                ServiceBlueprintVersion.status == "published",
            ).order_by(ServiceBlueprintVersion.version_number.desc()))).scalars().first()
            if not published_blueprint:
                db.add(ServiceBlueprintVersion(
                    master_service_id=service.id, version_number=1, status="published",
                    snapshot={"job_type": job_key, "requires_type": True, "requires_brand": True,
                              "pricing_model": service.pricing_model, "is_active": True},
                    change_summary="Canonical AC setup contract", published_at=NOW(),
                ))

        await db.commit()

    # Use the canonical append-only workflow writer, which also bumps setup
    # revisions and validates every transition against the runtime graph.
    async with session_factory() as db:
        workflow_writer = JobTypeBlueprintService(db)
        for slug, (service, job_type) in services.items():
            steps, transitions = _workflow_journey(
                quote_approval_required=WORKFLOW_RULES[slug]["quote_approval_required"],
            )
            await workflow_writer.set_workflow(
                service.id, job_type.id,
                {
                    **WORKFLOW_RULES[slug],
                    "schedule_required": True,
                    "address_required": True,
                    "technician_required": True,
                    "service_area_required": True,
                    "availability_required": True,
                    "steps": steps,
                    "transitions": transitions,
                },
            )

    async with session_factory() as db:
        for slug, (service, job_type) in services.items():
            workflow = (await db.execute(select(ServiceJobWorkflow).where(
                ServiceJobWorkflow.master_service_id == service.id,
                ServiceJobWorkflow.job_type_id == job_type.id,
                ServiceJobWorkflow.is_current.is_(True),
                ServiceJobWorkflow.status == "published",
            ))).scalar_one()
            link = await _one(db, MasterServiceJobType, master_service_id=service.id,
                              job_type_id=job_type.id)
            await _ensure_checklist(db, slug, service, link, workflow)

        # Remove legacy Type/Brand ranges from inspection-first services.
        # They were never part of the customer price contract, but keeping
        # them populated lets older screens accidentally surface a second,
        # contradictory Repair price.
        inspection_service_ids = {
            service.id for slug, (service, _) in services.items()
            if WORKFLOW_RULES[slug]["pricing_behavior"] in {"inspection_required", "custom_quote"}
        }
        inspection_tenant_services = (await db.execute(select(TenantService).where(
            TenantService.master_service_id.in_(inspection_service_ids),
            TenantService.deleted_at.is_(None),
        ))).scalars().all()
        inspection_tenant_service_ids = [row.id for row in inspection_tenant_services]
        for row in inspection_tenant_services:
            row.tenant_base_price = None
            row.tenant_min_price = None
            row.tenant_max_price = None
            if row.tenant_visit_fee is None:
                row.setup_status = "draft"
                row.published_at = None
        if inspection_tenant_service_ids:
            for row in (await db.execute(select(TenantServiceType).where(
                TenantServiceType.tenant_service_id.in_(inspection_tenant_service_ids),
            ))).scalars().all():
                row.tenant_min_price = None
                row.tenant_max_price = None
            for row in (await db.execute(select(TenantServiceBrand).where(
                TenantServiceBrand.tenant_service_id.in_(inspection_tenant_service_ids),
            ))).scalars().all():
                row.tenant_min_price = None
                row.tenant_max_price = None

        # Repair the currently registered workspace and any registration that
        # completed before the code fix. Future signups use the same helper in
        # public_registration.service.
        tenants = (await db.execute(select(Tenant).where(Tenant.vertical == "home_services"))).scalars().all()
        for tenant in tenants:
            await entitlement_service.grant_registration_defaults(
                db, tenant_id=tenant.id, module_key="home_services",
                actor_id=tenant.owner_user_id, actor_role="tenant_owner",
                commit=False,
            )
        await db.commit()

    await engine.dispose()
    print(f"Configured {len(services)} AC services, {len(types)} types, {len(brands)} brands")
    print(f"Published {sum(len(v) for v in ISSUES.values())} problems and "
          f"{sum(len(v) + 2 for v in QUESTIONS.values())} customer questions")
    print("Published 4 workflows and 4 job-completion checklists")


if __name__ == "__main__":
    asyncio.run(configure())
