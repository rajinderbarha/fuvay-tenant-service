"""Wires the deterministic question-flow for AC Installation, which was
never fully connected (unlike ac_repair, which got a Phase-2 baseline
script): zero master_service_job_types, zero service_job_workflow, zero
service_issue_mappings, zero brand_mappings, zero catalog_questions --
despite MasterService.is_brand_required=True and is_type_required=True.
This is why DeepSeek would ask "which brand?" / "confirm your city" in
plain chat with no real list to offer: there was no real, admin-configured
brand or type list wired to this specific master_service at all.

Adds: master_service_job_type + service_job_workflow (installation),
one issue type + mapping ("New AC Installation"), and two real tap-select
CatalogQuestions (brand, type) sourced from the real Brand/ServiceType rows
already used elsewhere (LG/Samsung/Voltas; Split AC/Window AC).

Idempotent -- safe to re-run.
Run: python scripts/seed_ac_installation_question_flow.py
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.engines.admin_catalog.models import (
    MasterService, MasterServiceJobType, ServiceJobWorkflow, JobTypeDefinition,
    MasterIssueType, ServiceIssueMapping, CatalogQuestion, CatalogQuestionOption,
    Brand, BrandMapping, ServiceType, ServiceTypeMapping,
)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://serviceos:serviceos@localhost:5432/serviceos")

AC_INSTALL_SLUG = "ac-installation"
BRAND_SLUGS = ["lg", "samsung", "voltas"]
TYPE_SLUGS = ["split_ac", "window_ac"]


async def run():
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        ms = (await db.execute(select(MasterService).where(MasterService.slug == AC_INSTALL_SLUG))).scalar_one_or_none()
        if not ms:
            print(f"[FAIL] master_service '{AC_INSTALL_SLUG}' not found")
            return

        jt = (await db.execute(select(JobTypeDefinition).where(JobTypeDefinition.key == "installation"))).scalar_one_or_none()
        if not jt:
            print("[FAIL] canonical job_type 'installation' not found")
            return

        # ── master_service_job_types + service_job_workflow ────────────────
        msjt = (await db.execute(select(MasterServiceJobType).where(
            MasterServiceJobType.master_service_id == ms.id, MasterServiceJobType.job_type_id == jt.id,
        ))).scalar_one_or_none()
        if not msjt:
            db.add(MasterServiceJobType(master_service_id=ms.id, job_type_id=jt.id, is_active=True))
            print("[CREATE] master_service_job_type")
        else:
            print("[SKIP]   master_service_job_type")

        sjw = (await db.execute(select(ServiceJobWorkflow).where(
            ServiceJobWorkflow.master_service_id == ms.id, ServiceJobWorkflow.job_type_id == jt.id,
        ))).scalar_one_or_none()
        if not sjw:
            db.add(ServiceJobWorkflow(
                master_service_id=ms.id, job_type_id=jt.id,
                inspection_required=False, quote_approval_required=True,
                checklist_required=False, schedule_required=True, address_required=True,
                technician_required=True, service_area_required=True, availability_required=True,
                pricing_behavior="range",
            ))
            print("[CREATE] service_job_workflow")
        else:
            print("[SKIP]   service_job_workflow")

        # ── issue type + mapping (resolves job_type_id via selected_problem_id) ──
        issue = (await db.execute(select(MasterIssueType).where(
            MasterIssueType.slug == f"{AC_INSTALL_SLUG}-new-installation"
        ))).scalar_one_or_none()
        if not issue:
            issue = MasterIssueType(
                category_id=ms.category_id, master_service_id=ms.id,
                code="new_installation", name="New AC Installation",
                slug=f"{AC_INSTALL_SLUG}-new-installation",
                severity="low", is_active=True, vertical_type="home_services",
                status="active", customer_visible=True,
            )
            db.add(issue)
            await db.flush()
            print("[CREATE] issue_type: New AC Installation")
        else:
            print("[SKIP]   issue_type: New AC Installation")

        mapping = (await db.execute(select(ServiceIssueMapping).where(
            ServiceIssueMapping.master_service_id == ms.id, ServiceIssueMapping.issue_type_id == issue.id,
        ))).scalar_one_or_none()
        if not mapping:
            db.add(ServiceIssueMapping(
                master_service_id=ms.id, issue_type_id=issue.id, job_type_id=jt.id,
                status="active", is_common=True, is_default=True, customer_visible=True,
            ))
            print("[CREATE] service_issue_mapping")
        else:
            print("[SKIP]   service_issue_mapping")

        # ── brand_mappings (admin-catalog-level, distinct from tenant enablement) ──
        brands = (await db.execute(select(Brand).where(Brand.slug.in_(BRAND_SLUGS)))).scalars().all()
        for b in brands:
            bm = (await db.execute(select(BrandMapping).where(
                BrandMapping.brand_id == b.id, BrandMapping.service_id == ms.id,
            ))).scalar_one_or_none()
            if not bm:
                db.add(BrandMapping(
                    brand_id=b.id, category_id=ms.category_id, service_group_id=ms.service_group_id,
                    service_id=ms.id, customer_visible=True, provider_visible=True, status="active",
                ))
                print(f"[CREATE] brand_mapping: {b.name}")
            else:
                print(f"[SKIP]   brand_mapping: {b.name}")

        # ── brand CatalogQuestion (tap-select) ──────────────────────────────
        brand_q = (await db.execute(select(CatalogQuestion).where(
            CatalogQuestion.master_service_id == ms.id, CatalogQuestion.job_type_id == jt.id,
            CatalogQuestion.question_key == "brand",
        ))).scalar_one_or_none()
        if not brand_q:
            brand_q = CatalogQuestion(
                master_service_id=ms.id, job_type_id=jt.id, question_key="brand",
                label="Which AC brand?", input_type="single_select", answer_source="static",
                required=True, customer_visible=True, deepseek_enabled=True,
                display_order=0, is_active=True,
            )
            db.add(brand_q)
            await db.flush()
            print("[CREATE] question: Which AC brand?")
        else:
            print("[SKIP]   question: Which AC brand?")

        for i, b in enumerate(brands):
            opt = (await db.execute(select(CatalogQuestionOption).where(
                CatalogQuestionOption.question_id == brand_q.id, CatalogQuestionOption.code == b.slug,
            ))).scalar_one_or_none()
            if not opt:
                db.add(CatalogQuestionOption(question_id=brand_q.id, code=b.slug, label=b.name, display_order=i, is_active=True))

        # ── type CatalogQuestion (Split AC / Window AC, tap-select) ────────
        types = (await db.execute(select(ServiceType).where(ServiceType.slug.in_(TYPE_SLUGS)))).scalars().all()
        type_q = (await db.execute(select(CatalogQuestion).where(
            CatalogQuestion.master_service_id == ms.id, CatalogQuestion.job_type_id == jt.id,
            CatalogQuestion.question_key == "ac_type",
        ))).scalar_one_or_none()
        if not type_q:
            type_q = CatalogQuestion(
                master_service_id=ms.id, job_type_id=jt.id, question_key="ac_type",
                label="Split AC or Window AC?", input_type="single_select", answer_source="static",
                required=True, customer_visible=True, deepseek_enabled=True,
                display_order=1, is_active=True,
            )
            db.add(type_q)
            await db.flush()
            print("[CREATE] question: Split AC or Window AC?")
        else:
            print("[SKIP]   question: Split AC or Window AC?")

        for i, t in enumerate(types):
            opt = (await db.execute(select(CatalogQuestionOption).where(
                CatalogQuestionOption.question_id == type_q.id, CatalogQuestionOption.code == t.slug,
            ))).scalar_one_or_none()
            if not opt:
                db.add(CatalogQuestionOption(question_id=type_q.id, code=t.slug, label=t.name, display_order=i, is_active=True))

            stm = (await db.execute(select(ServiceTypeMapping).where(
                ServiceTypeMapping.type_id == t.id, ServiceTypeMapping.service_id == ms.id,
            ))).scalar_one_or_none()
            if not stm:
                db.add(ServiceTypeMapping(
                    type_id=t.id, category_id=ms.category_id, service_group_id=ms.service_group_id,
                    service_id=ms.id, customer_visible=True, provider_visible=True, status="active",
                ))
                print(f"[CREATE] service_type_mapping: {t.name} -> AC Installation")

        await db.commit()

    await engine.dispose()
    print("\n[DONE] AC Installation question-flow seed complete.")


if __name__ == "__main__":
    asyncio.run(run())
