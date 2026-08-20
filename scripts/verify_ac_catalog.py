"""Read-only/rollback verification for the canonical AC catalog setup."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import create_engine
from app.engines.admin_catalog.models import (
    JobTypeDefinition,
    MasterService,
    MasterServiceBrand,
    MasterServiceJobType,
    MasterServiceType,
    ServiceJobWorkflow,
)
from app.engines.admin_catalog.question_service import CatalogQuestionService
from app.engines.admin_catalog.tenant_service import TenantCatalogService
from app.engines.checklist_catalog.models import (
    ChecklistItem,
    ChecklistSection,
    ChecklistTemplateVersion,
    JobTypeChecklistMapping,
)
from app.engines.entitlement.service import entitlement_service
from app.engines.tenant_engine.models import Tenant


AC_SLUGS = {"ac_repair", "ac_installation", "ac_maintenance", "ac_gas_refill"}
EXPECTED_CHECKLIST_ITEMS = {
    "ac_repair": 8,
    "ac_installation": 8,
    "ac_maintenance": 8,
    "ac_gas_refill": 9,
}


async def verify() -> None:
    engine = create_engine()
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as db:
        tenant = (await db.execute(select(Tenant).where(
            Tenant.vertical == "home_services"
        ).order_by(Tenant.created_at.desc()))).scalars().first()
        if not tenant:
            raise AssertionError("No Home Services tenant exists for entitlement verification")

        services = (await db.execute(select(MasterService).where(
            MasterService.slug.in_(AC_SLUGS),
            MasterService.is_active.is_(True),
            MasterService.deleted_at.is_(None),
        ))).scalars().all()
        assert len(services) == 4, f"expected 4 AC services, found {len(services)}"

        catalog = TenantCatalogService(
            db=db,
            actor_id=tenant.owner_user_id,
            actor_role="tenant_owner",
            actor_tenant_id=tenant.id,
        )
        available = await catalog.list_home_services_available(tenant.id)
        ac_ids = {str(service.id) for service in services}
        ac_rows = [row for row in available["services"] if row.get("service_id") in ac_ids]
        assert len(ac_rows) == 4, f"tenant projection returned {len(ac_rows)} AC services"
        assert all(not row.get("admin_blockers") for row in ac_rows), "an AC blueprint has admin blockers"
        available_by_service = {row["service_id"]: row for row in ac_rows}

        for service in services:
            assert service.service_group_id
            assert await entitlement_service.has_category_entitlement(
                db, tenant.id, service.service_group_id
            ), f"tenant is not entitled to {service.slug}"
            configured_types = (await db.execute(select(MasterServiceType.id).where(
                MasterServiceType.master_service_id == service.id,
                MasterServiceType.is_active.is_(True),
            ))).scalars().all()
            configured_brands = (await db.execute(select(MasterServiceBrand.id).where(
                MasterServiceBrand.master_service_id == service.id,
                MasterServiceBrand.is_active.is_(True),
                MasterServiceBrand.status == "active",
            ))).scalars().all()
            assert len(configured_types) == 4
            assert len(configured_brands) == 11

            link, job_type = (await db.execute(
                select(MasterServiceJobType, JobTypeDefinition)
                .join(JobTypeDefinition, JobTypeDefinition.id == MasterServiceJobType.job_type_id)
                .where(
                    MasterServiceJobType.master_service_id == service.id,
                    MasterServiceJobType.is_active.is_(True),
                )
            )).one()
            workflow = (await db.execute(select(ServiceJobWorkflow).where(
                ServiceJobWorkflow.master_service_id == service.id,
                ServiceJobWorkflow.job_type_id == job_type.id,
                ServiceJobWorkflow.is_current.is_(True),
                ServiceJobWorkflow.status == "published",
            ))).scalar_one()
            assert len(workflow.steps_json or []) == 12
            assert len(workflow.transitions_json or []) == 11

            mapping = (await db.execute(select(JobTypeChecklistMapping).where(
                JobTypeChecklistMapping.master_service_job_type_id == link.id,
                JobTypeChecklistMapping.service_job_workflow_id == workflow.id,
                JobTypeChecklistMapping.status == "active",
            ))).scalars().first()
            assert mapping, f"{service.slug} has no active workflow-pinned checklist"
            assert mapping.usage == "REQUIRED"
            assert mapping.actor == "TECHNICIAN"
            assert mapping.completion_gate == "REQUIRE_BEFORE_JOB_COMPLETION"
            version = await db.get(ChecklistTemplateVersion, mapping.checklist_template_version_id)
            assert version and version.status == "PUBLISHED"
            sections = (await db.execute(select(ChecklistSection.id).where(
                ChecklistSection.checklist_template_version_id == version.id,
            ))).scalars().all()
            item_count = len((await db.execute(select(ChecklistItem.id).where(
                ChecklistItem.checklist_section_id.in_(sections),
            ))).scalars().all())
            assert len(sections) == 3
            assert item_count == EXPECTED_CHECKLIST_ITEMS[service.slug]

            question_service = CatalogQuestionService(db)
            questions = await question_service.resolve_applicable_questions(
                service.id, job_type.id,
                {"selected_problem_id": None, "enabled_dimension_ids": [], "prior_answers": {}},
            )
            by_key = {q["question_key"]: q for q in questions["questions"]}
            assert len(by_key["ac_type"]["options"]) == 4
            assert len(by_key["brand"]["options"]) == 11
            assert all(o.get("code") for o in by_key["ac_type"]["options"])
            assert all(o.get("code") for o in by_key["brand"]["options"])
            preview = await question_service.list_questions(service.id, job_type.id)
            preview_by_key = {q["question_key"]: q for q in preview["questions"]}
            assert len(preview_by_key["ac_type"]["options"]) == 4
            assert len(preview_by_key["brand"]["options"]) == 11
            assert all(
                q["options"]
                for q in preview["questions"]
                if q.get("answer_source") == "static"
                and q.get("input_type") in {"single_select", "multi_select"}
            ), f"{service.slug} has a choice question without answers"

            payload = {"master_service_id": str(service.id), "job_type_id": str(job_type.id),
                       "warranty_days": 5}
            if workflow.pricing_behavior == "fixed":
                payload["tenant_base_price"] = "1000.00"
            else:
                payload["tenant_visit_fee"] = "299.00"
            # The verifier is safe both before and after a tenant has enabled
            # the catalog. Exercise the mutation only for disabled offerings;
            # an already-enabled row is itself the persisted success state.
            if available_by_service[str(service.id)].get("is_enabled"):
                assert available_by_service[str(service.id)]["admin_ready"] is True
            else:
                enabled = await catalog.enable_service(payload, tenant.id)
                assert enabled["is_enabled"] is True

        # The write path is exercised through flush but intentionally rolled
        # back so verification never changes the tenant's draft setup.
        await db.rollback()

    await engine.dispose()
    print("PASS: entitlement, 4 service projections, enable state, workflows, questions and checklists")


if __name__ == "__main__":
    asyncio.run(verify())
