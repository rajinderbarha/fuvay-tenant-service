"""Wires the deterministic question-flow (migration 220 / CatalogQuestion) for
the 8 home services seeded by seed_140412_home_services.py at zipcode 140412.

Without this, the booking assistant can create a draft but has no way to
resolve draft.job_type_id (needed by QuestionFlowService), because that
resolution path is: DeepSeek picks a MasterIssueType id (via the
get_service_problems tool) -> ServiceIssueMapping -> job_type_id. With no
MasterIssueType/ServiceIssueMapping/CatalogQuestion rows for a service, the
question flow can never produce a question or option, regardless of any
frontend fix -- this is real, missing admin-catalog content, not a bug.

For each service: one MasterIssueType + ServiceIssueMapping (resolves the
service's own job_type), one MasterServiceJobType + ServiceJobWorkflow row,
and one real single_select CatalogQuestion with 3-5 options.

Idempotent -- safe to re-run. Run: python scripts/seed_140412_question_flows.py
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
)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://serviceos:serviceos@localhost:5432/serviceos")

# offering_slug -> job_type key ("repair"/"service"/"installation" -- canonical job_types rows)
# plus one issue + one question with options.
CONTENT = {
    "pipe-repair": {
        "job_type_key": "repair",
        "issue": {"name": "Pipe Leaking", "code": "pipe_leaking"},
        "question": {
            "key": "leak_location", "label": "Where is the leak?",
            "options": ["Kitchen", "Bathroom", "Outside wall", "Under sink"],
        },
    },
    "drain-unblocking": {
        "job_type_key": "service",
        "issue": {"name": "Drain Blocked", "code": "drain_blocked"},
        "question": {
            "key": "drain_location", "label": "Which drain is blocked?",
            "options": ["Kitchen sink", "Bathroom", "Toilet", "Floor drain"],
        },
    },
    "electrical-fault-fix": {
        "job_type_key": "repair",
        "issue": {"name": "Power Not Working", "code": "power_not_working"},
        "question": {
            "key": "fault_type", "label": "What's the issue?",
            "options": ["No power in a room", "Frequent tripping", "Sparking / burning smell", "Switch or socket not working"],
        },
    },
    "fan-light-installation": {
        "job_type_key": "installation",
        "issue": {"name": "New Installation", "code": "new_installation"},
        "question": {
            "key": "install_item", "label": "What needs installing?",
            "options": ["Ceiling fan", "Light fixture", "Both"],
        },
    },
    "interior-wall-painting": {
        "job_type_key": "service",
        "issue": {"name": "Wall Painting Needed", "code": "wall_painting_needed"},
        "question": {
            "key": "room_count", "label": "How many rooms need painting?",
            "options": ["1 room", "2-3 rooms", "Whole house"],
        },
    },
    "general-pest-control": {
        "job_type_key": "service",
        "issue": {"name": "Pest Infestation", "code": "pest_infestation"},
        "question": {
            "key": "pest_type", "label": "What kind of pest problem?",
            "options": ["Cockroaches", "Ants", "Termites", "Rodents", "General / preventive"],
        },
    },
    "regular-home-cleaning": {
        "job_type_key": "service",
        "issue": {"name": "Cleaning Needed", "code": "cleaning_needed"},
        "question": {
            "key": "home_size", "label": "What's your home size?",
            "options": ["1 BHK", "2 BHK", "3 BHK", "4 BHK+"],
        },
    },
    "full-home-deep-clean": {
        "job_type_key": "service",
        "issue": {"name": "Deep Cleaning Needed", "code": "deep_cleaning_needed"},
        "question": {
            "key": "home_size", "label": "What's your home size?",
            "options": ["1 BHK", "2 BHK", "3 BHK", "4 BHK+"],
        },
    },
}


async def run():
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        job_types = {
            jt.key: jt for jt in (await db.execute(
                select(JobTypeDefinition).where(JobTypeDefinition.key.in_(("repair", "service", "installation")))
            )).scalars().all()
        }
        if not job_types:
            print("[FAIL] canonical job_types (repair/service/installation) not found.")
            return

        counts = {"msjt": 0, "sjw": 0, "issue": 0, "mapping": 0, "question": 0, "option": 0}

        for slug, cdata in CONTENT.items():
            ms = (await db.execute(select(MasterService).where(MasterService.slug == slug))).scalar_one_or_none()
            if not ms:
                print(f"[WARN] master_service '{slug}' not found — run seed_140412_home_services.py first")
                continue

            jt = job_types.get(cdata["job_type_key"])
            if not jt:
                print(f"[WARN] job_type '{cdata['job_type_key']}' not found — skipping {slug}")
                continue

            print(f"[{slug}] job_type={jt.key}")

            # ── master_service_job_types ────────────────────────────────────
            msjt = (await db.execute(select(MasterServiceJobType).where(
                MasterServiceJobType.master_service_id == ms.id, MasterServiceJobType.job_type_id == jt.id,
            ))).scalar_one_or_none()
            if not msjt:
                db.add(MasterServiceJobType(master_service_id=ms.id, job_type_id=jt.id, is_active=True))
                counts["msjt"] += 1
                print("  [CREATE] master_service_job_type")
            else:
                print("  [SKIP]   master_service_job_type")

            # ── service_job_workflow ────────────────────────────────────────
            sjw = (await db.execute(select(ServiceJobWorkflow).where(
                ServiceJobWorkflow.master_service_id == ms.id, ServiceJobWorkflow.job_type_id == jt.id,
            ))).scalar_one_or_none()
            if not sjw:
                is_repair = jt.key == "repair"
                db.add(ServiceJobWorkflow(
                    master_service_id=ms.id, job_type_id=jt.id,
                    inspection_required=is_repair, quote_approval_required=is_repair,
                    checklist_required=False, schedule_required=True, address_required=True,
                    technician_required=True, service_area_required=True, availability_required=True,
                    pricing_behavior="inspection_required" if is_repair else "fixed",
                ))
                counts["sjw"] += 1
                print("  [CREATE] service_job_workflow")
            else:
                print("  [SKIP]   service_job_workflow")

            # ── master_issue_types + service_issue_mappings ────────────────
            idata = cdata["issue"]
            issue = (await db.execute(select(MasterIssueType).where(
                MasterIssueType.slug == f"{slug}-{idata['code']}"
            ))).scalar_one_or_none()
            if not issue:
                issue = MasterIssueType(
                    category_id=ms.category_id, master_service_id=ms.id,
                    code=idata["code"], name=idata["name"], slug=f"{slug}-{idata['code']}",
                    severity="medium", is_active=True, vertical_type="home_services",
                    status="active", customer_visible=True,
                )
                db.add(issue)
                await db.flush()
                counts["issue"] += 1
                print(f"  [CREATE] issue_type: {idata['name']}")
            else:
                print(f"  [SKIP]   issue_type: {idata['name']}")

            mapping = (await db.execute(select(ServiceIssueMapping).where(
                ServiceIssueMapping.master_service_id == ms.id, ServiceIssueMapping.issue_type_id == issue.id,
            ))).scalar_one_or_none()
            if not mapping:
                db.add(ServiceIssueMapping(
                    master_service_id=ms.id, issue_type_id=issue.id, job_type_id=jt.id,
                    status="active", is_common=True, is_default=True, customer_visible=True,
                ))
                counts["mapping"] += 1
                print("  [CREATE] service_issue_mapping")
            else:
                print("  [SKIP]   service_issue_mapping")

            # ── catalog_questions + options ─────────────────────────────────
            qdata = cdata["question"]
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
                counts["question"] += 1
                print(f"  [CREATE] question: {qdata['label']}")
            else:
                print(f"  [SKIP]   question: {qdata['label']}")

            for i, label in enumerate(qdata["options"]):
                code = label.lower().replace(" ", "_").replace("/", "_").replace("-", "_")
                opt = (await db.execute(select(CatalogQuestionOption).where(
                    CatalogQuestionOption.question_id == question.id, CatalogQuestionOption.code == code,
                ))).scalar_one_or_none()
                if not opt:
                    db.add(CatalogQuestionOption(
                        question_id=question.id, code=code, label=label, display_order=i, is_active=True,
                    ))
                    counts["option"] += 1

        await db.commit()

    await engine.dispose()
    print(f"\nDone — {counts}")


if __name__ == "__main__":
    asyncio.run(run())
