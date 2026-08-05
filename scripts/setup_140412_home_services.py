"""Canonical, deterministic, idempotent setup/verification entrypoint for the
zipcode-140412 Home Services demo/dev environment (tenant Guramrit).

Consolidates what were previously three (four, counting an ad-hoc inline
python snippet never saved as a script) separate seed scripts into one
reusable entrypoint, per the "one deterministic 140412 setup" requirement.
Reuses their existing `run()` functions directly rather than duplicating
their logic -- this file adds only:
  1. Orchestration (call each step in dependency order).
  2. The previously ad-hoc, non-idempotent `ServiceType` (Split AC / Window
     AC) creation this environment needed but had never been captured in a
     script -- fixed here to check-before-insert like every other step.
  3. A non-mutating `--verify-only` mode that reports readiness without
     writing anything.
  4. A final validation report covering the full canonical chain: category
     -> service_group -> master_service -> job_type/workflow -> issue
     mapping -> catalog question/options -> tenant_service (published) ->
     tenant_service_area_service, for every AC + the 8 other seeded
     services, plus a tenant/area summary.

Never adds admin-owned service pricing (admin_catalog MasterService.
base_price stays as an estimate-only fallback, already established
elsewhere in this codebase -- see _compute_price_snapshot's own docstring
in app/engines/home_service_booking/service.py). All *bookable* pricing
here is tenant-owned (TenantService.tenant_min_price/max_price,
TenantServiceAreaService.min_price/max_price/base_price).

Safe to re-run any number of times: every step below is check-before-write
against a stable lookup key (slug/code/composite FK pair), matching this
repo's existing seed-script convention -- never a blind INSERT.

Run:
  python scripts/setup_140412_home_services.py               # seed + report
  python scripts/setup_140412_home_services.py --verify-only  # report only
"""
from __future__ import annotations
import argparse
import asyncio
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.engines.admin_catalog.models import (
    ServiceCategory, ServiceGroup, MasterService, TenantService,
    MasterServiceJobType, ServiceJobWorkflow, MasterIssueType,
    ServiceIssueMapping, CatalogQuestion, CatalogQuestionOption,
    ServiceType, BrandMapping, JobTypeDefinition,
)
from app.engines.serviceability.models import TenantServiceArea, TenantServiceAreaService

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://serviceos:serviceos@localhost:5432/serviceos")

TENANT_ID = uuid.UUID("244beeec-fedc-452e-8054-317e45557d4d")  # Guramrit
ZIPCODE = "140412"

# All offering slugs Guramrit is expected to publish + fully wire for
# 140412 -- used by the validation report. `ac-service` was HISTORICALLY
# excluded here: it was a real, correctly-configured offering, just
# published only by a DIFFERENT tenant (the pre-existing Ludhiana demo
# tenant, id 5209ef33-...), not Guramrit. That was also the root cause of
# a real product defect ("Brand appears as the first question, before any
# real issue selection") -- Guramrit's only rich-enough offering was
# ac-installation, whose only configured questions ARE brand/type, so
# there was never a genuine "what's wrong with your AC" issue choice at
# 140412. `ensure_ac_service_guramrit_publication` now publishes
# ac-service's real 8-issue diagnostic catalog for Guramrit too, so it
# belongs in this list going forward.
EXPECTED_OFFERING_SLUGS = [
    "ac-installation", "ac-gas-refilling", "ac-service",
    "pipe-repair", "drain-unblocking",
    "electrical-fault-fix", "fan-light-installation",
    "interior-wall-painting", "general-pest-control",
    "regular-home-cleaning", "full-home-deep-clean",
]

TYPE_DEFS = [("Split AC", "split_ac"), ("Window AC", "window_ac")]

# AC Gas Refilling had zero question-flow wiring (found by this report) --
# same pattern as seed_140412_question_flows.py's CONTENT table, just for
# the one AC offering that script doesn't cover.
AC_GAS_REFILLING_CONTENT = {
    "slug": "ac-gas-refilling",
    "job_type_key": "service",
    "issue": {"name": "Low Cooling / Gas Refill Needed", "code": "gas_refill_needed"},
    "question": {
        "key": "cooling_symptom", "label": "What's happening with the cooling?",
        "options": ["Not cooling at all", "Cooling weakly", "Warm air only", "Ice forming on unit"],
    },
}


async def ensure_ac_gas_refilling_question_flow(db: AsyncSession) -> None:
    """Found by this script's own validation report: `ac-gas-refilling`
    had zero master_service_job_type/workflow/issue-mapping/question rows
    -- fully published and bookable, but the question flow could never
    resolve a job_type_id for it. Same pattern as
    seed_140412_question_flows.py, applied to the one AC offering that
    script doesn't cover."""
    c = AC_GAS_REFILLING_CONTENT
    ms = (await db.execute(select(MasterService).where(MasterService.slug == c["slug"]))).scalar_one_or_none()
    if not ms:
        print(f"  [WARN] master_service '{c['slug']}' not found - skipping")
        return
    jt = (await db.execute(select(JobTypeDefinition).where(JobTypeDefinition.key == c["job_type_key"]))).scalar_one_or_none()
    if not jt:
        print(f"  [WARN] job_type '{c['job_type_key']}' not found - skipping")
        return

    if not (await db.execute(select(MasterServiceJobType).where(
        MasterServiceJobType.master_service_id == ms.id, MasterServiceJobType.job_type_id == jt.id,
    ))).scalar_one_or_none():
        db.add(MasterServiceJobType(master_service_id=ms.id, job_type_id=jt.id, is_active=True))
        print("  [CREATE] master_service_job_type (ac-gas-refilling)")
    else:
        print("  [SKIP]   master_service_job_type (ac-gas-refilling)")

    if not (await db.execute(select(ServiceJobWorkflow).where(
        ServiceJobWorkflow.master_service_id == ms.id, ServiceJobWorkflow.job_type_id == jt.id,
    ))).scalar_one_or_none():
        db.add(ServiceJobWorkflow(
            master_service_id=ms.id, job_type_id=jt.id,
            inspection_required=False, quote_approval_required=False,
            checklist_required=False, schedule_required=True, address_required=True,
            technician_required=True, service_area_required=True, availability_required=True,
            pricing_behavior="fixed",
        ))
        print("  [CREATE] service_job_workflow (ac-gas-refilling)")
    else:
        print("  [SKIP]   service_job_workflow (ac-gas-refilling)")

    idata = c["issue"]
    issue_slug = f"{c['slug']}-{idata['code']}"
    issue = (await db.execute(select(MasterIssueType).where(MasterIssueType.slug == issue_slug))).scalar_one_or_none()
    if not issue:
        issue = MasterIssueType(
            category_id=ms.category_id, master_service_id=ms.id,
            code=idata["code"], name=idata["name"], slug=issue_slug,
            severity="medium", is_active=True, vertical_type="home_services",
            status="active", customer_visible=True,
        )
        db.add(issue)
        await db.flush()
        print(f"  [CREATE] issue_type: {idata['name']}")
    else:
        print(f"  [SKIP]   issue_type: {idata['name']}")

    if not (await db.execute(select(ServiceIssueMapping).where(
        ServiceIssueMapping.master_service_id == ms.id, ServiceIssueMapping.issue_type_id == issue.id,
    ))).scalar_one_or_none():
        db.add(ServiceIssueMapping(
            master_service_id=ms.id, issue_type_id=issue.id, job_type_id=jt.id,
            status="active", is_common=True, is_default=True, customer_visible=True,
        ))
        print("  [CREATE] service_issue_mapping (ac-gas-refilling)")
    else:
        print("  [SKIP]   service_issue_mapping (ac-gas-refilling)")

    qdata = c["question"]
    question = (await db.execute(select(CatalogQuestion).where(
        CatalogQuestion.master_service_id == ms.id, CatalogQuestion.job_type_id == jt.id,
        CatalogQuestion.question_key == qdata["key"],
    ))).scalar_one_or_none()
    if not question:
        question = CatalogQuestion(
            master_service_id=ms.id, job_type_id=jt.id, question_key=qdata["key"],
            label=qdata["label"], input_type="single_select", answer_source="static",
            required=True, customer_visible=True, deepseek_enabled=True,
            display_order=0, is_active=True,
        )
        db.add(question)
        await db.flush()
        print(f"  [CREATE] question: {qdata['label']}")
    else:
        print(f"  [SKIP]   question: {qdata['label']}")

    for i, label in enumerate(qdata["options"]):
        code = label.lower().replace(" ", "_").replace("/", "_")
        if not (await db.execute(select(CatalogQuestionOption).where(
            CatalogQuestionOption.question_id == question.id, CatalogQuestionOption.code == code,
        ))).scalar_one_or_none():
            db.add(CatalogQuestionOption(question_id=question.id, code=code, label=label, display_order=i, is_active=True))

    await db.commit()


AC_GAS_REFILLING_VISIT_FEE = 299.00


async def ensure_ac_gas_refilling_pricing_mode(db: AsyncSession) -> None:
    """Found by this script's own readiness validation (pricing-mode-aware
    check added alongside this function): `ac-gas-refilling`'s
    MasterService was configured with `pricing_model='fixed'` and
    `visit_fee=0.00` -- an inspection-first service (the technician must
    check the refrigerant type/leak before quoting a repair) misclassified
    as fixed-price, with no real number behind it. That flowed all the way
    into a live ₹0.00 `standard_price` reaching a real customer's Booking
    Review. This offering genuinely requires an on-site inspection before
    any repair price can be quoted -- corrected to the real inspection-mode
    contract (`visit_fee_plus_quote`) with the tenant-confirmed ₹299 visit
    fee, matching `ServiceJobWorkflow.inspection_required` for the same
    offering to the same fact rather than leaving the two out of sync."""
    ms = (await db.execute(select(MasterService).where(MasterService.slug == "ac-gas-refilling"))).scalar_one_or_none()
    if not ms:
        print("  [WARN] master_service 'ac-gas-refilling' not found - skipping")
        return

    changed = False
    if ms.pricing_model != "visit_fee_plus_quote":
        ms.pricing_model = "visit_fee_plus_quote"
        changed = True
    if not ms.visit_fee or float(ms.visit_fee) <= 0:
        ms.visit_fee = AC_GAS_REFILLING_VISIT_FEE
        changed = True
    print(f"  [{'UPDATE' if changed else 'SKIP'}] master_service.pricing_model/visit_fee (ac-gas-refilling)"
          f" -> pricing_model=visit_fee_plus_quote, visit_fee={AC_GAS_REFILLING_VISIT_FEE}")

    workflow = (await db.execute(select(ServiceJobWorkflow).where(
        ServiceJobWorkflow.master_service_id == ms.id, ServiceJobWorkflow.is_current.is_(True),
    ))).scalar_one_or_none()
    workflow_changed = False
    if workflow and not workflow.inspection_required:
        workflow.inspection_required = True
        workflow.pricing_behavior = "inspection_required"  # PRICING_BEHAVIORS canonical value
        workflow_changed = True
        print("  [UPDATE] service_job_workflow.inspection_required -> True (ac-gas-refilling)")
    elif workflow:
        print("  [SKIP]   service_job_workflow.inspection_required already True (ac-gas-refilling)")
    else:
        print("  [WARN] no current service_job_workflow for ac-gas-refilling - skipping workflow update")

    if changed or workflow_changed:
        await db.commit()


async def ensure_ac_installation_area_service(db: AsyncSession) -> None:
    """Found by this script's own validation report: AC Installation
    (`ac-installation`) has a published TenantService but zero
    TenantServiceAreaService rows for 140412 -- serviceable in principle
    (the tenant_service_area itself covers 140412) but not per-service
    marked available, unlike every other seeded offering."""
    tenant_area = (await db.execute(
        select(TenantServiceArea).where(TenantServiceArea.tenant_id == TENANT_ID, TenantServiceArea.zipcode == ZIPCODE)
    )).scalars().first()
    if not tenant_area:
        print("  [WARN] no tenant_service_area for 140412 - skipping")
        return
    ms = (await db.execute(select(MasterService).where(MasterService.slug == "ac-installation"))).scalar_one_or_none()
    if not ms:
        print("  [WARN] master_service 'ac-installation' not found - skipping")
        return

    existing = (await db.execute(select(TenantServiceAreaService).where(
        TenantServiceAreaService.tenant_service_area_id == tenant_area.id,
        TenantServiceAreaService.service_id == ms.id,
        TenantServiceAreaService.job_type == "installation",
    ))).scalar_one_or_none()
    if existing:
        print("  [SKIP]   tenant_service_area_service (ac-installation)")
        return

    ts = (await db.execute(select(TenantService).where(
        TenantService.tenant_id == TENANT_ID, TenantService.master_service_id == ms.id,
    ))).scalar_one_or_none()
    db.add(TenantServiceAreaService(
        tenant_service_area_id=tenant_area.id, tenant_id=TENANT_ID,
        service_id=ms.id, job_type="installation", is_available=True,
        min_price=float(ts.tenant_min_price) if ts and ts.tenant_min_price else None,
        max_price=float(ts.tenant_max_price) if ts and ts.tenant_max_price else None,
        status="ACTIVE",
    ))
    print("  [CREATE] tenant_service_area_service (ac-installation)")
    await db.commit()


AC_SERVICE_SLUG = "ac-service"
AC_SERVICE_VISIT_FEE = 299.00


async def ensure_ac_service_guramrit_publication(db: AsyncSession) -> None:
    """Root-cause fix for "Brand appears before any real issue selection":
    the admin catalog already has a full, real, 8-issue AC diagnostic
    catalog (Not Cooling, Cooling Low, Water Leakage, Noise Issue, Bad
    Smell, Remote Not Working, AC Not Starting, Gas Refill Needed) under
    master_service `ac-service`, each with its own real question-flow
    wiring -- but Guramrit never published it. Guramrit only ever
    published `ac-installation` (a single "New AC Installation" issue
    whose only configured questions are Brand/Type) and `ac-gas-refilling`
    (a single issue) -- so for zipcode 140412 there was NEVER a real
    "what's wrong with your AC" issue-first choice; Brand was the actual
    first configured question for the only rich-enough offering that
    happened to be published there. This publishes the SAME real,
    already-built ac-service catalog for Guramrit at 140412, exactly like
    a tenant onboarding to an existing service -- no new issues, no
    duplicate mappings, no fabricated price (inspection-mode via a real
    visit fee, same pattern as ac-gas-refilling)."""
    ms = (await db.execute(select(MasterService).where(MasterService.slug == AC_SERVICE_SLUG))).scalar_one_or_none()
    if not ms:
        print(f"  [WARN] master_service '{AC_SERVICE_SLUG}' not found - skipping")
        return

    changed = False
    if ms.pricing_model != "visit_fee_plus_quote":
        ms.pricing_model = "visit_fee_plus_quote"
        changed = True
    if not ms.visit_fee or float(ms.visit_fee) <= 0:
        ms.visit_fee = AC_SERVICE_VISIT_FEE
        changed = True
    print(f"  [{'UPDATE' if changed else 'SKIP'}] master_service.pricing_model/visit_fee (ac-service) -> visit_fee_plus_quote, {AC_SERVICE_VISIT_FEE}")

    # Every issue currently mapped for ac-service resolves to the same
    # job_type/workflow (confirmed live) -- mark that one current workflow
    # inspection-first, same as the ac-gas-refilling fix.
    workflows = (await db.execute(select(ServiceJobWorkflow).where(
        ServiceJobWorkflow.master_service_id == ms.id, ServiceJobWorkflow.is_current.is_(True),
    ))).scalars().all()
    workflow_changed = False
    for wf in workflows:
        if not wf.inspection_required:
            wf.inspection_required = True
            wf.pricing_behavior = "inspection_required"
            workflow_changed = True
    print(f"  [{'UPDATE' if workflow_changed else 'SKIP'}] service_job_workflow.inspection_required (ac-service, {len(workflows)} current workflow(s))")

    if changed or workflow_changed:
        await db.commit()

    ts = (await db.execute(select(TenantService).where(
        TenantService.tenant_id == TENANT_ID, TenantService.master_service_id == ms.id,
    ))).scalars().first()
    if not ts:
        from datetime import datetime, timezone
        ts = TenantService(
            tenant_id=TENANT_ID, master_service_id=ms.id, category_id=ms.category_id,
            job_type="service", is_enabled=True,
            tenant_visit_fee=AC_SERVICE_VISIT_FEE,
            override_allowed=True, requires_brand=False, requires_type=False,
            is_active=True, setup_status="published",
            published_at=datetime.now(timezone.utc),
            type_coverage_mode="all", brand_coverage_mode="all",
        )
        db.add(ts)
        await db.flush()
        print("  [CREATE] tenant_service (Guramrit x ac-service)")
    else:
        changed_ts = False
        if not (ts.is_enabled and ts.is_active and ts.setup_status == "published"):
            ts.is_enabled, ts.is_active, ts.setup_status = True, True, "published"
            changed_ts = True
        if not ts.tenant_visit_fee or float(ts.tenant_visit_fee) <= 0:
            ts.tenant_visit_fee = AC_SERVICE_VISIT_FEE
            changed_ts = True
        print(f"  [{'UPDATE' if changed_ts else 'SKIP'}] tenant_service (Guramrit x ac-service) already exists")
    await db.commit()

    tenant_area = (await db.execute(
        select(TenantServiceArea).where(TenantServiceArea.tenant_id == TENANT_ID, TenantServiceArea.zipcode == ZIPCODE)
    )).scalars().first()
    if not tenant_area:
        print("  [WARN] no tenant_service_area for 140412 - skipping area-service link")
        return

    existing_area_svc = (await db.execute(select(TenantServiceAreaService).where(
        TenantServiceAreaService.tenant_service_area_id == tenant_area.id,
        TenantServiceAreaService.service_id == ms.id,
        TenantServiceAreaService.job_type == "service",
    ))).scalar_one_or_none()
    if existing_area_svc:
        print("  [SKIP]   tenant_service_area_service (ac-service)")
    else:
        db.add(TenantServiceAreaService(
            tenant_service_area_id=tenant_area.id, tenant_id=TENANT_ID,
            service_id=ms.id, job_type="service", is_available=True,
            status="ACTIVE",
        ))
        print("  [CREATE] tenant_service_area_service (ac-service)")
        await db.commit()


# ── AC-ISSUE-DATA-01: Gas Refill deduplication + compatibility metadata ──────
#
# Real duplicate found by live audit: `ac-gas-refilling`'s own single issue
# ("Low Cooling / Gas Refill Needed") and `ac-service`'s "Gas Refill
# Needed" issue mean the same real customer intent -- both resolve to
# inspection-mode pricing with the same real ₹299 visit fee (ac-service is
# now published for Guramrit at 140412; ac-gas-refilling was the ONLY
# gas-refill entry point before that publication existed). Customers must
# see exactly one "Gas refill needed" choice.
#
# Chosen mechanism: mark `ac-gas-refilling`'s issue mapping
# `customer_visible=False` (a real, existing column -- never a fuzzy
# label match, never a destructive delete). `ac-service`'s own "Gas Refill
# Needed" issue becomes the sole customer-visible entry point going
# forward. This is non-destructive and reversible:
#   - The `ac-gas-refilling` MasterService, its MasterIssueType row, its
#     ServiceIssueMapping row, and its CatalogQuestion all remain in the
#     database exactly as they are.
#   - Any EXISTING draft/booking/job that already references the legacy
#     issue id (`selected_problem_id` or an entry in
#     `service_option_ids_json`) keeps resolving normally -- nothing reads
#     `customer_visible` when loading an already-selected problem, only
#     when LISTING issues for a NEW selection
#     (offering_catalog_service.list_serviceable_issues explicitly filters
#     `ServiceIssueMapping.customer_visible == True`).
#   - A NEW draft can no longer be started against the legacy hidden
#     issue id (list_serviceable_issues excludes it, and select_issue
#     re-validates against that same list -- see the "hidden issue
#     rejected" test).
AC_GAS_REFILLING_ID = uuid.UUID("b54e5517-ec51-4694-899b-04307e7f95bf")

# Selection-mode/compatibility metadata (AC-ISSUE-DATA-01 section 3) --
# stored in `ServiceIssueMapping.metadata_json` (existing JSONB column,
# no schema change). Derived from real workflow facts, never from label
# text: an "installation" job type is a customer-exclusive intent (only
# one such issue may ever be selected, alone); everything else sharing
# ac-service's single "service" job type is a compatible diagnostic
# symptom (any number may be selected together, since they already
# provably resolve to the identical master_service/job_type/workflow).
COMPATIBILITY_GROUP_INSTALLATION = "ac_installation"
COMPATIBILITY_GROUP_AC_SERVICE_DIAGNOSTIC = "ac_service_diagnostic"


async def ensure_gas_refill_deduplication_and_compatibility_metadata(db: AsyncSession) -> None:
    """Idempotently (a) hides the legacy ac-gas-refilling issue from new
    selection, (b) stamps selection_mode/compatibility_group onto every
    customer-visible AC issue mapping, and (c) fixes a real content bug
    found by the issue-to-question audit: ac-service's shared
    `issue_detail` question literally asked "Please describe where you'd
    like the AC installed" for EVERY diagnostic issue (Not Cooling, Noise,
    Water Leakage, ...) -- installation-flavored copy left over from
    before ac-service was published for repair/diagnostic use. Fixed to
    generic, always-relevant wording. This is the one question-content fix
    this sprint makes without a schema change; see the module docstring
    this function is called from for why true PER-ISSUE questions are not
    possible today (CatalogQuestion has no issue-type scoping column --
    only master_service_id + job_type_id)."""
    from app.engines.admin_catalog.models import (
        MasterService, MasterIssueType, ServiceIssueMapping, CatalogQuestion, JobTypeDefinition,
    )

    # (a) Hide the legacy gas-refill entry point.
    gas_mapping = (await db.execute(
        select(ServiceIssueMapping).where(ServiceIssueMapping.master_service_id == AC_GAS_REFILLING_ID)
    )).scalars().first()
    if gas_mapping and gas_mapping.customer_visible:
        gas_mapping.customer_visible = False
        print("  [UPDATE] service_issue_mapping.customer_visible=False (ac-gas-refilling legacy 'Low Cooling / Gas Refill Needed')")
        await db.commit()
    else:
        print("  [SKIP]   ac-gas-refilling issue mapping already hidden/missing")

    # (b) Compatibility metadata for every customer-visible AC issue.
    ac_service = (await db.execute(select(MasterService).where(MasterService.slug == AC_SERVICE_SLUG))).scalar_one_or_none()
    ac_install = (await db.execute(select(MasterService).where(MasterService.slug == "ac-installation"))).scalar_one_or_none()
    stamped = 0
    for ms, group, mode in [
        (ac_service, COMPATIBILITY_GROUP_AC_SERVICE_DIAGNOSTIC, "compatible_multi"),
        (ac_install, COMPATIBILITY_GROUP_INSTALLATION, "exclusive"),
    ]:
        if not ms:
            continue
        mappings = (await db.execute(
            select(ServiceIssueMapping).where(
                ServiceIssueMapping.master_service_id == ms.id, ServiceIssueMapping.customer_visible.is_(True),
            )
        )).scalars().all()
        for m in mappings:
            meta = dict(m.metadata_json or {})
            if meta.get("selection_mode") != mode or meta.get("compatibility_group") != group:
                meta["selection_mode"] = mode
                meta["compatibility_group"] = group
                m.metadata_json = meta
                stamped += 1
    print(f"  [{'UPDATE' if stamped else 'SKIP'}] compatibility metadata stamped on {stamped} issue mapping(s)")
    if stamped:
        await db.commit()

    # (c) Fix the installation-flavored shared question label.
    if ac_service:
        bad_question = (await db.execute(
            select(CatalogQuestion).where(
                CatalogQuestion.master_service_id == ac_service.id, CatalogQuestion.question_key == "issue_detail",
            )
        )).scalar_one_or_none()
        correct_label = "Please share any additional details about the issue."
        if bad_question and bad_question.label != correct_label:
            bad_question.label = correct_label
            print("  [UPDATE] catalog_question 'issue_detail' label (ac-service) -> generic, no longer installation-flavored")
            await db.commit()
        else:
            print("  [SKIP]   catalog_question 'issue_detail' label already correct")


async def ensure_ac_service_required_field_flags(db: AsyncSession) -> None:
    """Real confirm-blocking bug fixed here.

    `ac-service` carried `is_type_required = True`, but its question flow
    only ever asks brand / capacity_ton / issue_detail -- there is NO
    service-type ("Split AC" / "Window AC") question anywhere in it. So
    `draft.offering_type_id` could never be populated, and
    `_compute_missing_fields` rejected EVERY diagnostic AC booking at
    confirmation with "Missing required fields: offering_type_id".

    The honest fix is to make the requirement match the flow that actually
    exists: a diagnostic repair visit is priced off the visit fee and the
    technician's on-site estimate, and genuinely does not need the unit's
    cabinet type up front. `is_brand_required` is deliberately LEFT ON --
    the flow really does ask for brand, and that answer now reaches
    `draft.brand_id` (see the case-insensitive bridge fix in
    question_flow_service._bridge_to_draft_columns).
    """
    ac_service = (await db.execute(
        select(MasterService).where(MasterService.slug == AC_SERVICE_SLUG)
    )).scalar_one_or_none()
    if not ac_service:
        print("  [SKIP]   ac-service not found.")
        return

    from app.engines.admin_catalog.models import CatalogQuestion
    keys = set((await db.execute(
        select(CatalogQuestion.question_key).where(
            CatalogQuestion.master_service_id == ac_service.id,
            CatalogQuestion.is_active.is_(True),
        )
    )).scalars().all())
    asks_type = bool(keys & {"ac_type", "service_type", "offering_type"})

    if ac_service.is_type_required and not asks_type:
        ac_service.is_type_required = False
        await db.commit()
        print("  [UPDATE] ac-service.is_type_required -> False "
              "(no service-type question exists in its flow; was blocking every confirmation)")
    else:
        print(f"  [SKIP]   ac-service.is_type_required already consistent "
              f"(required={ac_service.is_type_required}, asks_type={asks_type})")


async def ensure_guramrit_ac_service_entitlement(db: AsyncSession) -> None:
    """CUSTOMER-CHAT-UX-04 root cause: every ac-service (diagnostic) booking
    reached Booking Review as "This isn't ready to review yet" and never
    showed a price, because `select_best_provider` excluded Guramrit --
    the ONLY covering tenant -- with `TENANT_CATEGORY_NOT_ENTITLED`.

    Confirmed live: Guramrit had ZERO rows in both
    `tenant_module_entitlements` and `tenant_category_entitlements`.
    `ac-installation`/`ac-gas-refilling` have `service_group_id = NULL`,
    so matching_engine's entitlement gate is skipped entirely for them
    (`if svc_group_row:`) and they always worked -- masking the gap.
    `ac-service` is the only AC master service WITH a service_group_id
    ("Ac Service"), so it was the only one the gate ever applied to, and
    it failed closed for every single diagnostic issue.

    Creates the canonical two-level entitlement (module -> category) that
    `EntitlementService.get_entitled_tenant_ids_for_category` requires,
    rather than weakening the gate itself -- the gate is correct; the
    tenant provisioning was genuinely missing."""
    from datetime import datetime, timezone
    from app.engines.entitlement.models import TenantCategoryEntitlement, TenantModuleEntitlement
    from app.engines.admin_catalog.models import MasterService, ServiceGroup, ServiceCategory
    from app.engines.tenant_engine.models import Tenant
    from app.engines.vertical_catalog.models import Vertical

    tenant = (await db.execute(
        select(Tenant).where(Tenant.tenant_name.ilike("%guramrit%"))
    )).scalars().first()
    if not tenant:
        print("  [SKIP]   Guramrit tenant not found -- entitlement provisioning skipped.")
        return

    ac_service = (await db.execute(
        select(MasterService).where(MasterService.slug == AC_SERVICE_SLUG)
    )).scalars().first()
    if not ac_service or not ac_service.service_group_id:
        print("  [SKIP]   ac-service has no service_group_id -- entitlement gate does not apply.")
        return

    group = await db.get(ServiceGroup, ac_service.service_group_id)
    category = await db.get(ServiceCategory, group.category_id) if group else None
    if not category:
        print("  [SKIP]   ac-service group has no parent ServiceCategory -- cannot resolve module.")
        return

    # The module (vertical) the entitlement chain joins through. The
    # category's own vertical_type is the authoritative link.
    vertical = (await db.execute(
        select(Vertical).where(Vertical.key == category.vertical_type)
    )).scalars().first()
    if not vertical:
        print(f"  [SKIP]   No Vertical row for '{category.vertical_type}' -- cannot create module entitlement.")
        return
    if not vertical.is_enabled:
        vertical.is_enabled = True
        print(f"  [UPDATE] vertical '{vertical.key}'.is_enabled -> True (entitlement resolver requires it)")

    module_ent = (await db.execute(
        select(TenantModuleEntitlement).where(
            TenantModuleEntitlement.tenant_id == tenant.id,
            TenantModuleEntitlement.module_id == vertical.id,
        )
    )).scalars().first()
    if not module_ent:
        module_ent = TenantModuleEntitlement(
            tenant_id=tenant.id, module_id=vertical.id,
            status="ACTIVE", source="setup_script", enabled_at=datetime.now(timezone.utc),
        )
        db.add(module_ent)
        await db.flush()
        print(f"  [CREATE] tenant_module_entitlement (Guramrit x {vertical.key})")
    elif module_ent.status != "ACTIVE":
        module_ent.status = "ACTIVE"
        module_ent.disabled_at = None
        print(f"  [UPDATE] tenant_module_entitlement (Guramrit x {vertical.key}) -> ACTIVE")
    else:
        print(f"  [SKIP]   tenant_module_entitlement (Guramrit x {vertical.key}) already ACTIVE")

    cat_ent = (await db.execute(
        select(TenantCategoryEntitlement).where(
            TenantCategoryEntitlement.tenant_id == tenant.id,
            TenantCategoryEntitlement.category_id == group.id,
        )
    )).scalars().first()
    if not cat_ent:
        db.add(TenantCategoryEntitlement(
            tenant_id=tenant.id, category_id=group.id,
            module_entitlement_id=module_ent.id,
            status="ACTIVE", source="setup_script", enabled_at=datetime.now(timezone.utc),
        ))
        print(f"  [CREATE] tenant_category_entitlement (Guramrit x '{group.name}')")
    else:
        changed = False
        if cat_ent.status != "ACTIVE":
            cat_ent.status = "ACTIVE"
            cat_ent.disabled_at = None
            changed = True
        if cat_ent.module_entitlement_id != module_ent.id:
            cat_ent.module_entitlement_id = module_ent.id
            changed = True
        print(f"  [{'UPDATE' if changed else 'SKIP'}]   tenant_category_entitlement (Guramrit x '{group.name}')")

    await db.commit()


async def ensure_ac_installation_tenant_price_coverage(db: AsyncSession) -> None:
    """Found live while verifying AC Installation's real fixed price flows
    through to Booking Review: Guramrit's TenantService for AC Installation
    has a real, positive tenant price (tenant_min_price=1200/tenant_max_
    price=1800) but its `type_coverage_mode`/`brand_coverage_mode` default
    to 'selected' with ZERO TenantServiceType/TenantServiceBrand override
    rows ever created -- meaning `TenantCatalogService.resolve_tenant_price`
    (and therefore provider matching's own eligibility gate) reports
    `COMBINATION_NOT_SUPPORTED` / `NO_VALID_PRICE_RULE` for EVERY real
    type+brand combination a customer could actually select (Split/Window
    AC x LG/Samsung/Voltas), not just a synthetic test case -- this would
    have blocked every real AC Installation booking at match-and-price.
    Corrected to 'all' coverage, matching the real fact that Guramrit
    quotes the same tenant_min/max price regardless of AC type or brand."""
    ts = (await db.execute(select(TenantService).where(
        TenantService.tenant_id == TENANT_ID,
        TenantService.master_service_id == uuid.UUID("b598ad10-938e-4754-83bd-63b2fe626f20"),
    ))).scalars().first()
    if not ts:
        print("  [WARN] no tenant_service for Guramrit x ac-installation - skipping")
        return
    changed = False
    if ts.type_coverage_mode != "all":
        ts.type_coverage_mode = "all"
        changed = True
    if ts.brand_coverage_mode != "all":
        ts.brand_coverage_mode = "all"
        changed = True
    print(f"  [{'UPDATE' if changed else 'SKIP'}] tenant_service.type_coverage_mode/brand_coverage_mode (ac-installation) -> all/all")
    if changed:
        await db.commit()


async def ensure_service_types(db: AsyncSession) -> int:
    """Previously created via a one-off `python -c` snippet with no
    existence check -- re-running that snippet would have created
    duplicate ServiceType rows every time. Fixed here to the same
    check-before-insert pattern as every other step in this file."""
    created = 0
    for name, slug in TYPE_DEFS:
        existing = (await db.execute(select(ServiceType).where(ServiceType.slug == slug))).scalar_one_or_none()
        if existing:
            print(f"  [SKIP]   service_type: {name} (already exists)")
            continue
        db.add(ServiceType(
            category_id=uuid.UUID("59d8f3aa-932d-429e-93bd-8d4f2ed615c3"),  # Air Conditioning
            name=name, slug=slug, code=slug, customer_visible=True, status="active",
        ))
        print(f"  [CREATE] service_type: {name}")
        created += 1
    await db.commit()
    return created


async def validation_report(db: AsyncSession) -> bool:
    """Non-mutating readiness report for the full canonical chain. Returns
    True iff every expected offering is fully bookable (published tenant
    offering + real question-flow wiring), matching this mission's
    completion gate, not just "some rows exist somewhere"."""
    print("\n" + "=" * 78)
    print("VALIDATION REPORT - zipcode 140412 / tenant Guramrit")
    print("=" * 78)

    tenant_area = (await db.execute(
        select(TenantServiceArea).where(
            TenantServiceArea.tenant_id == TENANT_ID, TenantServiceArea.zipcode == ZIPCODE,
        )
    )).scalars().first()
    print(f"\nTenant service area 140412: {'OK ' + str(tenant_area.id) if tenant_area else 'MISSING'}")
    if not tenant_area:
        print("[BLOCKED] No tenant_service_area for 140412 -- nothing else can be verified.")
        return False

    all_ok = True
    print(f"\n{'offering_slug':<26} {'published':<10} {'job_type/workflow':<18} {'issue_map':<10} {'questions':<10} {'area_svc':<9} "
          f"{'pricing_mode':<11} pricing_detail")
    print("-" * 120)

    for slug in EXPECTED_OFFERING_SLUGS:
        ms = (await db.execute(select(MasterService).where(MasterService.slug == slug))).scalar_one_or_none()
        if not ms:
            print(f"{slug:<26} {'MISSING MASTER_SERVICE':<60}")
            all_ok = False
            continue

        ts = (await db.execute(select(TenantService).where(
            TenantService.tenant_id == TENANT_ID, TenantService.master_service_id == ms.id,
            TenantService.is_enabled.is_(True), TenantService.is_active.is_(True),
            TenantService.setup_status == "published",
        ))).scalars().first()
        published = "YES" if ts else "NO"
        if not ts:
            all_ok = False

        msjt_count = (await db.execute(
            select(func.count()).select_from(MasterServiceJobType).where(MasterServiceJobType.master_service_id == ms.id)
        )).scalar_one()
        sjw_count = (await db.execute(
            select(func.count()).select_from(ServiceJobWorkflow).where(ServiceJobWorkflow.master_service_id == ms.id)
        )).scalar_one()
        jt_wf = f"{msjt_count}/{sjw_count}"
        if msjt_count == 0 or sjw_count == 0:
            all_ok = False

        issue_count = (await db.execute(
            select(func.count()).select_from(ServiceIssueMapping).where(
                ServiceIssueMapping.master_service_id == ms.id, ServiceIssueMapping.status == "active",
            )
        )).scalar_one()
        if issue_count == 0:
            all_ok = False

        q_count = (await db.execute(
            select(func.count()).select_from(CatalogQuestion).where(CatalogQuestion.master_service_id == ms.id)
        )).scalar_one()

        area_svc = (await db.execute(
            select(func.count()).select_from(TenantServiceAreaService).where(
                TenantServiceAreaService.tenant_service_area_id == tenant_area.id,
                TenantServiceAreaService.service_id == ms.id,
                TenantServiceAreaService.is_available.is_(True),
            )
        )).scalar_one()
        if area_svc == 0:
            all_ok = False

        # Pricing-mode-aware readiness (real defect found live: a fixed-
        # price offering with `base_price=0.00` and an inspection-first
        # offering misconfigured as fixed both looked "bookable" by every
        # check above while being unbookable at a correct, non-zero
        # customer price). Never treats a database `base_price=0` as
        # readiness for inspection mode, and never treats admin catalog
        # `base_price` alone as readiness for fixed mode -- fixed-price
        # readiness requires the TENANT's own configured price.
        pricing_mode = "inspection" if ms.pricing_model == "visit_fee_plus_quote" else "fixed"
        if pricing_mode == "inspection":
            visit_fee = float(ms.visit_fee) if ms.visit_fee else 0.0
            pricing_ready = visit_fee > 0
            pricing_detail = f"visit_fee=Rs.{visit_fee:g}" if pricing_ready else "MISSING/ZERO visit_fee"
        else:
            ts_price = (await db.execute(select(TenantService).where(
                TenantService.tenant_id == TENANT_ID, TenantService.master_service_id == ms.id,
            ))).scalars().first()
            tenant_price_value = None
            if ts_price:
                if ts_price.tenant_base_price and float(ts_price.tenant_base_price) > 0:
                    tenant_price_value = float(ts_price.tenant_base_price)
                elif ts_price.tenant_min_price and float(ts_price.tenant_min_price) > 0:
                    tenant_price_value = float(ts_price.tenant_min_price)
            pricing_ready = tenant_price_value is not None
            pricing_detail = f"tenant_price=Rs.{tenant_price_value:g}" if pricing_ready else "MISSING/ZERO tenant price"
        if not pricing_ready:
            all_ok = False

        print(f"{slug:<26} {published:<10} {jt_wf:<18} {issue_count:<10} {q_count:<10} {area_svc:<9} "
              f"{pricing_mode:<11} {pricing_detail}")

    # Option-count sanity check per question -- an empty options list on a
    # single_select question is the same class of "looks populated but
    # isn't" failure this mission explicitly calls out.
    empty_option_questions = (await db.execute(
        select(CatalogQuestion.id, CatalogQuestion.label)
        .outerjoin(CatalogQuestionOption, CatalogQuestionOption.question_id == CatalogQuestion.id)
        .where(CatalogQuestion.input_type == "single_select", CatalogQuestion.answer_source == "static")
        .group_by(CatalogQuestion.id, CatalogQuestion.label)
        .having(func.count(CatalogQuestionOption.id) == 0)
    )).all()
    if empty_option_questions:
        all_ok = False
        print(f"\n[FAIL] {len(empty_option_questions)} single_select question(s) with ZERO options:")
        for qid, label in empty_option_questions:
            print(f"    - {label} ({qid})")
    else:
        print("\n[OK] No single_select question has an empty options list.")

    # AC Installation brand/type wiring specifically (the two-dimension case).
    ac_install = (await db.execute(select(MasterService).where(MasterService.slug == "ac-installation"))).scalar_one_or_none()
    if ac_install:
        brand_map_count = (await db.execute(
            select(func.count()).select_from(BrandMapping).where(BrandMapping.service_id == ac_install.id)
        )).scalar_one()
        type_count = (await db.execute(select(func.count()).select_from(ServiceType))).scalar_one()
        print(f"\nAC Installation: {brand_map_count} brand mapping(s), {type_count} ServiceType row(s) in catalog.")
        if brand_map_count == 0:
            all_ok = False

    # ── AC-ISSUE-DATA-01: issue-catalog integrity (Section 6) ────────────────
    print("\n" + "-" * 78)
    print("AC ISSUE CATALOG INTEGRITY (AC-ISSUE-DATA-01)")
    print("-" * 78)

    ac_service_ms = (await db.execute(select(MasterService).where(MasterService.slug == AC_SERVICE_SLUG))).scalar_one_or_none()
    if ac_service_ms or ac_install:
        from app.engines.admin_catalog.models import MasterIssueType, ServiceIssueMapping as SIM

        ac_ms_ids = [m.id for m in [ac_service_ms, ac_install] if m]
        visible_rows = (await db.execute(
            select(MasterIssueType.name, SIM.metadata_json, SIM.master_service_id)
            .join(SIM, SIM.issue_type_id == MasterIssueType.id)
            .where(SIM.master_service_id.in_(ac_ms_ids), SIM.status == "active", SIM.customer_visible.is_(True))
        )).all()

        # (1) Duplicate customer-visible intent -- same label shown twice.
        labels_seen: dict[str, int] = {}
        for name, _meta, _ms_id in visible_rows:
            labels_seen[name] = labels_seen.get(name, 0) + 1
        duplicate_labels = {label: count for label, count in labels_seen.items() if count > 1}
        if duplicate_labels:
            all_ok = False
            print(f"[FAIL] Duplicate customer-visible issue label(s): {duplicate_labels}")
        else:
            print(f"[OK] No duplicate customer-visible AC issue labels ({len(visible_rows)} visible issues).")

        # (2) Every visible issue has compatibility classification stamped.
        unclassified = [name for name, meta, _ms_id in visible_rows if not (meta or {}).get("selection_mode")]
        if unclassified:
            all_ok = False
            print(f"[FAIL] Issue(s) missing selection_mode/compatibility_group metadata: {unclassified}")
        else:
            print("[OK] Every visible AC issue has selection_mode/compatibility_group metadata.")

        # (3) The legacy gas-refill duplicate must be hidden, not deleted.
        gas_mapping = (await db.execute(
            select(SIM).where(SIM.master_service_id == AC_GAS_REFILLING_ID)
        )).scalars().first()
        if gas_mapping is None:
            all_ok = False
            print("[FAIL] ac-gas-refilling issue mapping missing entirely (should be hidden, not deleted).")
        elif gas_mapping.customer_visible:
            all_ok = False
            print("[FAIL] ac-gas-refilling legacy issue is still customer-visible -- Gas Refill will appear twice.")
        else:
            print("[OK] Legacy ac-gas-refilling issue is hidden (row preserved, historical drafts still resolve).")
    else:
        print("[SKIP] ac-service/ac-installation not found -- issue-catalog integrity checks skipped.")

    print("\n" + "=" * 78)
    print(f"OVERALL: {'READY' if all_ok else 'NOT READY'}")
    print("=" * 78)
    return all_ok


async def main(verify_only: bool) -> int:
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        if not verify_only:
            print("-- Step 1/6: categories/groups/master_services/tenant_services (8 non-AC services) --")
            from scripts.seed_140412_home_services import run as run_home_services
            await run_home_services()

            print("\n-- Step 2/6: question-flow wiring for the 8 non-AC services --")
            from scripts.seed_140412_question_flows import run as run_question_flows
            await run_question_flows()

            print("\n-- Step 3/6: ServiceType rows (Split AC / Window AC) --")
            await ensure_service_types(db)

            print("\n-- Step 4/6: AC Installation question-flow (brand/type) --")
            from scripts.seed_ac_installation_question_flow import run as run_ac_installation
            await run_ac_installation()

            print("\n-- Step 5/8: AC Gas Refilling question-flow (found missing by this script) --")
            await ensure_ac_gas_refilling_question_flow(db)

            print("\n-- Step 6/8: AC Installation tenant_service_area_service (found missing by this script) --")
            await ensure_ac_installation_area_service(db)

            print("\n-- Step 7/8: AC Gas Refilling pricing mode (found misconfigured by this script) --")
            await ensure_ac_gas_refilling_pricing_mode(db)

            print("\n-- Step 8/9: AC Installation tenant price coverage (found misconfigured by this script) --")
            await ensure_ac_installation_tenant_price_coverage(db)

            print("\n-- Step 9/10: AC Service (rich issue catalog) Guramrit publication (found missing by this script) --")
            await ensure_ac_service_guramrit_publication(db)

            print("\n-- Step 10/11: Gas Refill deduplication + compatibility metadata (AC-ISSUE-DATA-01) --")
            await ensure_gas_refill_deduplication_and_compatibility_metadata(db)

            print("\n-- Step 11/12: Guramrit ac-service category entitlement (CUSTOMER-CHAT-UX-04) --")
            await ensure_guramrit_ac_service_entitlement(db)

            print("\n-- Step 12/12: ac-service required-field flags (confirm-blocking bug) --")
            await ensure_ac_service_required_field_flags(db)
        else:
            print("[--verify-only] Skipping all writes, running validation report only.\n")

        ok = await validation_report(db)

    await engine.dispose()
    return 0 if ok else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only", action="store_true", help="Report readiness without writing anything.")
    args = parser.parse_args()
    exit_code = asyncio.run(main(args.verify_only))
    sys.exit(exit_code)
