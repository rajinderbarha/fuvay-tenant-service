"""Conditional Question Engine -- service layer (migration 155).

Admin CRUD for catalog questions / their static options / their show-when
rules, PLUS the runtime resolver that returns which questions apply to a
given (master_service, job_type, selected_problem, enabled_dimensions,
prior_answers) context -- the authoritative contract DeepSeek and the
customer flow consume. DeepSeek asks only what this returns; it never
invents parameters. NO monetary fields anywhere.
"""
from __future__ import annotations

import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.admin_catalog.models import (
    CatalogQuestion, CatalogQuestionOption, CatalogQuestionRule,
    CatalogDimension, ServiceType, ServiceTypeMapping, Brand, BrandMapping,
)
from app.exceptions import ServiceOSException, NotFoundException

INPUT_TYPES = {"single_select", "multi_select", "boolean", "number", "text",
               "photo", "date", "time", "address"}
ANSWER_SOURCES = {"static", "dimension", "problem", "free"}
CONDITION_TYPES = {"job_type", "problem", "dimension_enabled", "answer_equals"}
# Explicit editable field allowlist -- fails closed against any monetary key.
EDITABLE_FIELDS = {"label", "input_type", "answer_source", "dimension_id", "required",
                   "customer_visible", "tenant_setup_visible", "deepseek_enabled",
                   "validation", "help_text", "display_order", "is_active"}


class CatalogQuestionService:
    def __init__(self, db: AsyncSession, actor_id: uuid.UUID | None = None):
        self.db = db
        self.actor_id = actor_id

    # ── Questions CRUD ────────────────────────────────────────────────────────
    async def list_questions(self, master_service_id: uuid.UUID,
                             job_type_id: uuid.UUID | None) -> dict:
        job_scope = (
            or_(CatalogQuestion.job_type_id == job_type_id,
                CatalogQuestion.job_type_id.is_(None))
            if job_type_id else CatalogQuestion.job_type_id.is_(None)
        )
        q = select(CatalogQuestion).where(
            CatalogQuestion.master_service_id == master_service_id,
            job_scope,
        ).order_by(CatalogQuestion.display_order)
        rows = (await self.db.execute(q)).scalars().all()
        out = []
        for qn in rows:
            d = qn.to_dict()
            d.pop("icon_url", None)
            # The catalog workspace and the tenant requirements preview must
            # expose the same selectable values that the customer booking
            # resolver uses. Returning an empty list for dimension-backed
            # questions made configured Type/Brand questions look unfinished
            # even though their mappings were valid at runtime.
            d["options"] = await self._resolved_options(qn)
            d["rules"] = await self._rules(qn.id)
            out.append(d)
        return {"questions": out}

    async def create_question(self, data: dict) -> dict:
        ms = data.get("master_service_id")
        key = (data.get("question_key") or "").strip()
        label = (data.get("label") or "").strip()
        input_type = data.get("input_type", "single_select")
        answer_source = data.get("answer_source", "static")
        if not ms or not key or not label:
            raise ServiceOSException("QUESTION_FIELDS_REQUIRED",
                "master_service_id, question_key and label are required.", status_code=422)
        if input_type not in INPUT_TYPES:
            raise ServiceOSException("INVALID_INPUT_TYPE", f"input_type must be one of {sorted(INPUT_TYPES)}.", status_code=422)
        if answer_source not in ANSWER_SOURCES:
            raise ServiceOSException("INVALID_ANSWER_SOURCE", f"answer_source must be one of {sorted(ANSWER_SOURCES)}.", status_code=422)
        qn = CatalogQuestion(
            master_service_id=uuid.UUID(str(ms)),
            job_type_id=uuid.UUID(str(data["job_type_id"])) if data.get("job_type_id") else None,
            question_key=key, label=label, input_type=input_type, answer_source=answer_source,
            dimension_id=uuid.UUID(str(data["dimension_id"])) if data.get("dimension_id") else None,
            required=bool(data.get("required", False)),
            customer_visible=bool(data.get("customer_visible", True)),
            tenant_setup_visible=bool(data.get("tenant_setup_visible", False)),
            deepseek_enabled=bool(data.get("deepseek_enabled", True)),
            validation=data.get("validation"), help_text=data.get("help_text"),
            display_order=int(data.get("display_order", 0)))
        self.db.add(qn)
        await self.db.commit()
        await self.db.refresh(qn)
        result = qn.to_dict()
        result.pop("icon_url", None)
        return result

    async def update_question(self, question_id: uuid.UUID, data: dict) -> dict:
        qn = await self._load(question_id)
        for field in EDITABLE_FIELDS:
            if field in data:
                value = data[field]
                if field == "input_type" and value not in INPUT_TYPES:
                    raise ServiceOSException("INVALID_INPUT_TYPE", "Invalid input_type.", status_code=422)
                if field == "answer_source" and value not in ANSWER_SOURCES:
                    raise ServiceOSException("INVALID_ANSWER_SOURCE", "Invalid answer_source.", status_code=422)
                if field == "dimension_id":
                    setattr(qn, field, uuid.UUID(str(value)) if value else None)
                else:
                    setattr(qn, field, value)
        await self.db.commit()
        await self.db.refresh(qn)
        result = qn.to_dict()
        result.pop("icon_url", None)
        return result

    # ── Options ───────────────────────────────────────────────────────────────
    async def add_option(self, question_id: uuid.UUID, data: dict) -> dict:
        await self._load(question_id)
        code = (data.get("code") or "").strip()
        label = (data.get("label") or "").strip()
        if not code or not label:
            raise ServiceOSException("OPTION_CODE_LABEL_REQUIRED", "code and label are required.", status_code=422)
        opt = CatalogQuestionOption(question_id=question_id, code=code, label=label,
                                    display_order=int(data.get("display_order", 0)))
        self.db.add(opt)
        await self.db.commit()
        await self.db.refresh(opt)
        return opt.to_dict()

    # ── Rules ─────────────────────────────────────────────────────────────────
    async def add_rule(self, question_id: uuid.UUID, data: dict) -> dict:
        await self._load(question_id)
        ctype = data.get("condition_type")
        if ctype not in CONDITION_TYPES:
            raise ServiceOSException("INVALID_CONDITION_TYPE",
                f"condition_type must be one of {sorted(CONDITION_TYPES)}.", status_code=422)
        rule = CatalogQuestionRule(
            question_id=question_id, condition_type=ctype,
            ref_id=uuid.UUID(str(data["ref_id"])) if data.get("ref_id") else None,
            expected_value=data.get("expected_value"))
        self.db.add(rule)
        await self.db.commit()
        await self.db.refresh(rule)
        return rule.to_dict()

    async def delete_rule(self, rule_id: uuid.UUID) -> dict:
        rule = (await self.db.execute(
            select(CatalogQuestionRule).where(CatalogQuestionRule.id == rule_id))).scalar_one_or_none()
        if not rule:
            raise NotFoundException("CatalogQuestionRule", str(rule_id))
        await self.db.delete(rule)
        await self.db.commit()
        return {"deleted": True, "rule_id": str(rule_id)}

    # ── Runtime resolver (the DeepSeek / customer-flow contract) ──────────────
    async def resolve_applicable_questions(self, master_service_id: uuid.UUID,
                                           job_type_id: uuid.UUID | None,
                                           context: dict) -> dict:
        """Given the current context (selected_problem_id, enabled_dimension_ids,
        prior_answers: {question_key: value}), returns the ordered list of
        questions whose show-when rules ALL pass and which aren't already
        answered. This is exactly what the backend hands DeepSeek: known
        selections + the next allowable questions + their option IDs. DeepSeek
        must not ask anything outside this list."""
        selected_problem = context.get("selected_problem_id")
        enabled_dims = set(context.get("enabled_dimension_ids") or [])
        prior = context.get("prior_answers") or {}

        rows = (await self.db.execute(select(CatalogQuestion).where(
            CatalogQuestion.master_service_id == master_service_id,
            CatalogQuestion.job_type_id == job_type_id
            if job_type_id else CatalogQuestion.job_type_id.is_(None),
            CatalogQuestion.is_active == True,  # noqa: E712
            CatalogQuestion.customer_visible == True,  # noqa: E712
        ).order_by(CatalogQuestion.display_order))).scalars().all()

        applicable = []
        for qn in rows:
            if qn.question_key in prior:
                continue  # already known -- never re-ask (spec section 19)
            rules = await self._rules(qn.id)
            if not self._rules_pass(rules, job_type_id, selected_problem, enabled_dims, prior):
                continue
            d = qn.to_dict()
            d.pop("icon_url", None)
            d["options"] = await self._resolved_options(qn)
            applicable.append(d)
        return {"questions": applicable, "known": list(prior.keys())}

    def _rules_pass(self, rules: list[dict], job_type_id, selected_problem,
                    enabled_dims: set, prior: dict) -> bool:
        for r in rules:  # all ANDed
            ct = r["condition_type"]
            if ct == "job_type":
                if str(job_type_id) != str(r["ref_id"]):
                    return False
            elif ct == "problem":
                if str(selected_problem) != str(r["ref_id"]):
                    return False
            elif ct == "dimension_enabled":
                if str(r["ref_id"]) not in {str(x) for x in enabled_dims}:
                    return False
            elif ct == "answer_equals":
                # ref_id references another question's id; expected_value is
                # the required answer. prior is keyed by question_key, so this
                # compares against expected_value directly when supplied.
                if r["expected_value"] is not None and r["expected_value"] not in prior.values():
                    return False
        return True

    async def _resolved_options(self, qn: CatalogQuestion) -> list[dict]:
        if qn.answer_source == "static":
            return await self._options(qn.id)
        if qn.answer_source == "dimension" and qn.dimension_id:
            dim = (await self.db.execute(
                select(CatalogDimension).where(CatalogDimension.id == qn.dimension_id))).scalar_one_or_none()
            if not dim:
                return []
            if dim.legacy_source == "service_types":
                rows = (await self.db.execute(
                    select(ServiceType.id, ServiceType.slug, ServiceType.name)
                    .join(ServiceTypeMapping, ServiceTypeMapping.type_id == ServiceType.id)
                    .where(
                        ServiceTypeMapping.service_id == qn.master_service_id,
                        ServiceTypeMapping.status == "active",
                        ServiceTypeMapping.customer_visible.is_(True),
                        ServiceType.is_active.is_(True),
                        ServiceType.deleted_at.is_(None),
                    )
                    .order_by(ServiceTypeMapping.display_order, ServiceType.display_order, ServiceType.name)
                )).all()
                return [{"id": str(i), "code": slug, "label": name} for i, slug, name in rows]
            if dim.legacy_source == "brands":
                rows = (await self.db.execute(
                    select(Brand.id, Brand.slug, Brand.name)
                    .join(BrandMapping, BrandMapping.brand_id == Brand.id)
                    .where(
                        BrandMapping.service_id == qn.master_service_id,
                        BrandMapping.status == "active",
                        BrandMapping.customer_visible.is_(True),
                        Brand.is_active.is_(True),
                        Brand.deleted_at.is_(None),
                    )
                    .order_by(BrandMapping.display_order, Brand.display_order, Brand.name)
                )).all()
                return [{"id": str(i), "code": slug, "label": name} for i, slug, name in rows]
            from app.engines.admin_catalog.models import CatalogDimensionValue
            rows = (await self.db.execute(
                select(CatalogDimensionValue).where(
                    CatalogDimensionValue.dimension_id == qn.dimension_id,
                    CatalogDimensionValue.is_active == True).order_by(  # noqa: E712
                    CatalogDimensionValue.display_order))).scalars().all()
            return [{"id": str(v.id), "code": v.code, "label": v.label} for v in rows]
        return []

    # ── Helpers ───────────────────────────────────────────────────────────────
    async def _options(self, question_id: uuid.UUID) -> list[dict]:
        rows = (await self.db.execute(
            select(CatalogQuestionOption).where(
                CatalogQuestionOption.question_id == question_id,
                CatalogQuestionOption.is_active == True).order_by(  # noqa: E712
                CatalogQuestionOption.display_order))).scalars().all()
        return [o.to_dict() for o in rows]

    async def _rules(self, question_id: uuid.UUID) -> list[dict]:
        rows = (await self.db.execute(
            select(CatalogQuestionRule).where(CatalogQuestionRule.question_id == question_id))).scalars().all()
        return [r.to_dict() for r in rows]

    async def _load(self, question_id: uuid.UUID) -> CatalogQuestion:
        qn = (await self.db.execute(
            select(CatalogQuestion).where(CatalogQuestion.id == question_id))).scalar_one_or_none()
        if not qn:
            raise NotFoundException("CatalogQuestion", str(question_id))
        return qn
