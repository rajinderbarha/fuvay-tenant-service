"""Sprint 34I — Recommendation Engine Service.

RecommendationEngineService: evaluate rules, validate, explain, rank, track, accept, reject.
AdminRecommendationRuleService: CRUD + lifecycle (activate/deactivate/archive) + simulate.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.admin_catalog.models import (
    MasterDataAuditLog,
    RecommendationRule,
    RecommendationResult,
    Brand,
    MasterService,
    MasterServiceOption,
    MasterIssueType,
    ServiceCategory,
    MasterWorkflowTemplate,
)

# ─────────────────────────────────────────────────────────────────────────────
# Shared audit helper
# ─────────────────────────────────────────────────────────────────────────────

VALID_CONDITION_KEYS = {
    "vertical_type", "category_id", "category_code",
    "service_id", "service_code", "service_codes_any",
    "city_tier", "city_tier_any", "location_id", "zone_id",
    "tenant_type", "customer_flow_type",
    "requires_brand", "requires_service_option", "requires_issue_type",
    "requires_schedule", "requires_staff_assignment",
}


async def _audit(
    db: AsyncSession,
    resource: str,
    resource_id: str,
    action: str,
    actor_id: str,
    actor_role: str,
    request_id: str,
    payload: dict,
) -> None:
    log = MasterDataAuditLog(
        resource_type=resource,
        resource_id=resource_id,
        action=action,
        actor_id=actor_id,
        actor_role=actor_role,
        payload_json=payload,
        request_id=request_id,
    )
    db.add(log)


# ═════════════════════════════════════════════════════════════════════════════
# AdminRecommendationRuleService — Rule CRUD + lifecycle + simulate
# ═════════════════════════════════════════════════════════════════════════════

class AdminRecommendationRuleService:
    def __init__(
        self,
        db: AsyncSession,
        actor_id: uuid.UUID,
        actor_role: str,
        request_id: str,
    ) -> None:
        self.db = db
        self.actor_id = actor_id
        self.actor_role = actor_role
        self.request_id = request_id

    async def _log(self, action: str, resource_id: str, payload: dict) -> None:
        await _audit(
            self.db, "recommendation_rule", resource_id, action,
            str(self.actor_id), self.actor_role, self.request_id, payload,
        )

    # ── CRUD ──────────────────────────────────────────────────────────────────

    async def list_rules(
        self,
        status: str | None = None,
        rule_type: str | None = None,
        scope: str | None = None,
        vertical_type: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        q = select(RecommendationRule).where(RecommendationRule.deleted_at.is_(None))
        if status:
            q = q.where(RecommendationRule.status == status)
        if rule_type:
            q = q.where(RecommendationRule.rule_type == rule_type)
        if scope:
            q = q.where(RecommendationRule.scope == scope)
        if vertical_type:
            q = q.where(RecommendationRule.vertical_type == vertical_type)
        total = await self.db.scalar(select(func.count()).select_from(q.subquery()))
        q = q.order_by(RecommendationRule.priority.asc(), RecommendationRule.created_at.desc())
        q = q.offset((page - 1) * page_size).limit(page_size)
        rows = (await self.db.scalars(q)).all()
        return {"items": [r.to_dict() for r in rows], "total": total, "page": page, "page_size": page_size}

    async def get_rule(self, rule_id: uuid.UUID) -> RecommendationRule:
        r = await self.db.scalar(select(RecommendationRule).where(
            RecommendationRule.id == rule_id,
            RecommendationRule.deleted_at.is_(None),
        ))
        if not r:
            raise ValueError(f"Rule {rule_id} not found")
        return r

    async def create_rule(self, data: dict) -> dict:
        self._validate_rule_type(data.get("rule_type", ""))
        self._validate_scope(data.get("scope", "platform"))
        self._validate_condition_json(data.get("condition_json", {}))
        self._validate_recommendation_json(data.get("recommendation_json", {}))

        rule = RecommendationRule(
            code=data["code"],
            name=data["name"],
            description=data.get("description"),
            rule_type=data["rule_type"],
            scope=data.get("scope", "platform"),
            vertical_type=data.get("vertical_type"),
            category_id=uuid.UUID(data["category_id"]) if data.get("category_id") else None,
            service_id=uuid.UUID(data["service_id"]) if data.get("service_id") else None,
            tenant_id=uuid.UUID(data["tenant_id"]) if data.get("tenant_id") else None,
            location_id=uuid.UUID(data["location_id"]) if data.get("location_id") else None,
            priority=data.get("priority", 100),
            status="draft",
            condition_json=data.get("condition_json", {}),
            recommendation_json=data.get("recommendation_json", {}),
            explanation_template=data.get("explanation_template"),
            created_by_user_id=self.actor_id,
            updated_by_user_id=self.actor_id,
            metadata_json=data.get("metadata_json"),
        )
        self.db.add(rule)
        await self.db.flush()
        await self._log("recommendation_rule.created", str(rule.id), {"code": rule.code, "rule_type": rule.rule_type})
        await self.db.commit()
        await self.db.refresh(rule)
        return rule.to_dict()

    async def update_rule(self, rule_id: uuid.UUID, data: dict) -> dict:
        rule = await self.get_rule(rule_id)
        if rule.status == "archived":
            raise ValueError("Cannot update archived rule")

        if "rule_type" in data:
            self._validate_rule_type(data["rule_type"])
            rule.rule_type = data["rule_type"]
        if "scope" in data:
            self._validate_scope(data["scope"])
            rule.scope = data["scope"]
        if "condition_json" in data:
            self._validate_condition_json(data["condition_json"])
            rule.condition_json = data["condition_json"]
        if "recommendation_json" in data:
            self._validate_recommendation_json(data["recommendation_json"])
            rule.recommendation_json = data["recommendation_json"]

        for field in ("name", "description", "vertical_type", "priority", "explanation_template", "metadata_json"):
            if field in data:
                setattr(rule, field, data[field])

        rule.updated_by_user_id = self.actor_id
        rule.updated_at = datetime.now(timezone.utc)
        await self._log("recommendation_rule.updated", str(rule.id), {"fields": list(data.keys())})
        await self.db.commit()
        await self.db.refresh(rule)
        return rule.to_dict()

    async def delete_rule(self, rule_id: uuid.UUID) -> dict:
        rule = await self.get_rule(rule_id)
        rule.deleted_at = datetime.now(timezone.utc)
        rule.status = "archived"
        await self._log("recommendation_rule.archived", str(rule.id), {})
        await self.db.commit()
        return {"deleted": True, "id": str(rule_id)}

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def activate_rule(self, rule_id: uuid.UUID) -> dict:
        rule = await self.get_rule(rule_id)
        if rule.status == "archived":
            raise ValueError("Cannot activate archived rule")
        rule.status = "active"
        rule.updated_at = datetime.now(timezone.utc)
        await self._log("recommendation_rule.activated", str(rule.id), {})
        await self.db.commit()
        await self.db.refresh(rule)
        return rule.to_dict()

    async def deactivate_rule(self, rule_id: uuid.UUID) -> dict:
        rule = await self.get_rule(rule_id)
        if rule.status not in ("active", "draft"):
            raise ValueError(f"Cannot deactivate rule with status '{rule.status}'")
        rule.status = "inactive"
        rule.updated_at = datetime.now(timezone.utc)
        await self._log("recommendation_rule.deactivated", str(rule.id), {})
        await self.db.commit()
        await self.db.refresh(rule)
        return rule.to_dict()

    async def archive_rule(self, rule_id: uuid.UUID) -> dict:
        rule = await self.get_rule(rule_id)
        rule.status = "archived"
        rule.deleted_at = datetime.now(timezone.utc)
        rule.updated_at = datetime.now(timezone.utc)
        await self._log("recommendation_rule.archived", str(rule.id), {})
        await self.db.commit()
        await self.db.refresh(rule)
        return rule.to_dict()

    # ── Simulate (no mutation) ────────────────────────────────────────────────

    async def simulate_rule(self, rule_id: uuid.UUID, context: dict) -> dict:
        rule = await self.get_rule(rule_id)
        engine = RecommendationEngineService(self.db)

        matched = engine._evaluate_condition(rule.condition_json, context)
        recommendations: list[dict] = []
        warnings: list[str] = []

        if matched:
            recs = await engine._resolve_recommendation(rule, context)
            recommendations = recs["recommendations"]
            warnings = recs["warnings"]

        await self._log("recommendation_rule.simulated", str(rule.id), {
            "context_type": context.get("context_type"),
            "matched": matched,
        })
        await self.db.commit()

        return {
            "success": True,
            "data": {
                "rule_id":        str(rule.id),
                "rule_code":      rule.code,
                "matched":        matched,
                "recommendations": recommendations,
                "warnings":       warnings,
                "note":           "Simulation only — no database changes made",
            },
        }

    # ── Results list ─────────────────────────────────────────────────────────

    async def list_results(
        self,
        context_type: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        q = select(RecommendationResult)
        if context_type:
            q = q.where(RecommendationResult.context_type == context_type)
        if status:
            q = q.where(RecommendationResult.status == status)
        total = await self.db.scalar(select(func.count()).select_from(q.subquery()))
        q = q.order_by(RecommendationResult.created_at.desc())
        q = q.offset((page - 1) * page_size).limit(page_size)
        rows = (await self.db.scalars(q)).all()
        return {"items": [r.to_dict() for r in rows], "total": total, "page": page, "page_size": page_size}

    # ── Validation helpers ────────────────────────────────────────────────────

    @staticmethod
    def _validate_rule_type(rule_type: str) -> None:
        if rule_type not in RecommendationRule.VALID_RULE_TYPES:
            raise ValueError(
                f"Invalid rule_type '{rule_type}'. "
                f"Must be one of: {sorted(RecommendationRule.VALID_RULE_TYPES)}"
            )

    @staticmethod
    def _validate_scope(scope: str) -> None:
        if scope not in RecommendationRule.VALID_SCOPES:
            raise ValueError(
                f"Invalid scope '{scope}'. "
                f"Must be one of: {sorted(RecommendationRule.VALID_SCOPES)}"
            )

    @staticmethod
    def _validate_condition_json(condition: dict) -> None:
        if not isinstance(condition, dict):
            raise ValueError("condition_json must be a JSON object")
        invalid = set(condition.keys()) - VALID_CONDITION_KEYS
        if invalid:
            raise ValueError(f"Invalid condition keys: {sorted(invalid)}. Allowed: {sorted(VALID_CONDITION_KEYS)}")

    @staticmethod
    def _validate_recommendation_json(rec: dict) -> None:
        if not isinstance(rec, dict):
            raise ValueError("recommendation_json must be a JSON object")
        entity_type = rec.get("entity_type")
        if entity_type and entity_type not in RecommendationRule.VALID_RULE_TYPES:
            raise ValueError(f"recommendation_json.entity_type '{entity_type}' is not a recognized type")


# ═════════════════════════════════════════════════════════════════════════════
# RecommendationEngineService — Evaluate rules + produce recommendations
# ═════════════════════════════════════════════════════════════════════════════

class RecommendationEngineService:
    """Core engine: evaluate rules, rank, validate, explain, track results."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_recommendations(self, context: dict) -> dict:
        """Evaluate all active rules matching context; return ranked results."""
        rules = await self._load_active_rules(context)
        all_recs: list[dict] = []
        warnings: list[str] = []

        for rule in rules:
            if self._evaluate_condition(rule.condition_json, context):
                result = await self._resolve_recommendation(rule, context)
                for rec in result["recommendations"]:
                    rec["rule_id"] = str(rule.id)
                    rec["rule_code"] = rule.code
                all_recs.extend(result["recommendations"])
                warnings.extend(result["warnings"])

        ranked = self._rank_recommendations(all_recs)
        return {
            "recommendations": ranked,
            "warnings":        warnings,
            "rule_count":      len(rules),
            "context_type":    context.get("context_type", "unknown"),
        }

    async def _load_active_rules(self, context: dict) -> list[RecommendationRule]:
        q = (
            select(RecommendationRule)
            .where(
                RecommendationRule.status == "active",
                RecommendationRule.deleted_at.is_(None),
            )
            .order_by(RecommendationRule.priority.asc())
        )
        rows = (await self.db.scalars(q)).all()
        return list(rows)

    def _evaluate_condition(self, condition: dict, context: dict) -> bool:
        """Return True if context satisfies all condition fields."""
        if not condition:
            return True

        # vertical_type
        if "vertical_type" in condition:
            if context.get("vertical_type") != condition["vertical_type"]:
                return False

        # category_id
        if "category_id" in condition:
            if str(context.get("category_id", "")) != str(condition["category_id"]):
                return False

        # category_code
        if "category_code" in condition:
            if context.get("category_code") != condition["category_code"]:
                return False

        # service_id
        if "service_id" in condition:
            if str(context.get("service_id", "")) != str(condition["service_id"]):
                return False

        # service_code
        if "service_code" in condition:
            if context.get("service_code") != condition["service_code"]:
                return False

        # service_codes_any
        if "service_codes_any" in condition:
            ctx_code = context.get("service_code") or context.get("service_codes", [])
            if isinstance(ctx_code, str):
                ctx_code = [ctx_code]
            if not set(ctx_code) & set(condition["service_codes_any"]):
                return False

        # city_tier
        if "city_tier" in condition:
            if context.get("city_tier") != condition["city_tier"]:
                return False

        # city_tier_any
        if "city_tier_any" in condition:
            if context.get("city_tier") not in condition["city_tier_any"]:
                return False

        # boolean flags
        for flag in ("requires_brand", "requires_service_option", "requires_issue_type",
                     "requires_schedule", "requires_staff_assignment"):
            if flag in condition:
                if bool(context.get(flag)) != bool(condition[flag]):
                    return False

        # customer_flow_type
        if "customer_flow_type" in condition:
            if context.get("customer_flow_type") != condition["customer_flow_type"]:
                return False

        return True

    async def _resolve_recommendation(self, rule: RecommendationRule, context: dict) -> dict:
        """Resolve entity codes in recommendation_json to active DB records."""
        rec_json = rule.recommendation_json or {}
        entity_type = rec_json.get("entity_type", rule.rule_type)
        entity_codes = rec_json.get("entity_codes", [])
        recommendations: list[dict] = []
        warnings: list[str] = []

        if entity_type == "brand":
            for code in entity_codes:
                brand = await self.db.scalar(
                    select(Brand).where(Brand.slug == code, Brand.deleted_at.is_(None))
                )
                if not brand:
                    warnings.append(f"Brand code '{code}' not found")
                elif brand.status != "active":
                    warnings.append(f"Brand '{brand.name}' is {brand.status} — excluded")
                else:
                    recommendations.append(self._make_rec(rule, "brand", brand.id, brand.name,
                                                          "Brand recommended for this service type"))

        elif entity_type == "service_option":
            for code in entity_codes:
                opt = await self.db.scalar(
                    select(MasterServiceOption).where(
                        MasterServiceOption.code == code,
                        MasterServiceOption.deleted_at.is_(None),
                    )
                )
                if not opt:
                    warnings.append(f"Service option code '{code}' not found")
                elif opt.status != "active":
                    warnings.append(f"Option '{opt.name}' is {opt.status} — excluded")
                else:
                    recommendations.append(self._make_rec(rule, "service_option", opt.id, opt.name,
                                                          "Option recommended for this service"))

        elif entity_type == "issue_type":
            for code in entity_codes:
                issue = await self.db.scalar(
                    select(MasterIssueType).where(
                        MasterIssueType.code == code,
                        MasterIssueType.deleted_at.is_(None),
                    )
                )
                if not issue:
                    warnings.append(f"Issue type code '{code}' not found")
                elif issue.status != "active":
                    warnings.append(f"Issue '{issue.name}' is {issue.status} — excluded")
                else:
                    recommendations.append(self._make_rec(rule, "issue_type", issue.id, issue.name,
                                                          "Common issue for this service"))

        elif entity_type == "workflow_template":
            for code in entity_codes:
                # `slug`, not `code`, and `is_latest`, not `deleted_at`: this
                # branch was copied from the service_option/issue_type branches
                # above, whose models do have those columns.
                # MasterWorkflowTemplate has neither, so every lookup here
                # raised AttributeError before the query was even built — the
                # workflow_template recommendation path could never run.
                # `slug` is what the API exposes as `template_code`.
                wf = await self.db.scalar(
                    select(MasterWorkflowTemplate).where(
                        MasterWorkflowTemplate.slug == code,
                        MasterWorkflowTemplate.is_latest.is_(True),
                    )
                )
                if not wf:
                    warnings.append(f"Workflow template code '{code}' not found")
                elif wf.status != "active":
                    warnings.append(f"Workflow '{wf.name}' is {wf.status} — excluded")
                else:
                    recommendations.append(self._make_rec(rule, "workflow_template", wf.id, wf.name,
                                                          "Recommended workflow for this service type"))

        else:
            # Generic passthrough for document_requirement, checklist_template,
            # pricing_template, commission_template, provider_default, customer_next_step
            for code in entity_codes:
                recommendations.append({
                    "entity_type":       entity_type,
                    "entity_code":       code,
                    "entity_id":         None,
                    "name":              code,
                    "confidence_score":  round(1.0 - (0.05 * entity_codes.index(code)), 3),
                    "explanation":       self._explain(rule, entity_type, code, context),
                    "rule_id":           str(rule.id),
                    "rule_code":         rule.code,
                })

        return {"recommendations": recommendations, "warnings": warnings}

    def _make_rec(
        self,
        rule: RecommendationRule,
        entity_type: str,
        entity_id: uuid.UUID,
        name: str,
        explanation: str,
    ) -> dict:
        return {
            "entity_type":      entity_type,
            "entity_id":        str(entity_id),
            "name":             name,
            "confidence_score": round(max(0.5, 1.0 - (rule.priority - 100) * 0.001), 3),
            "explanation":      rule.explanation_template or explanation,
            "rule_id":          str(rule.id),
            "rule_code":        rule.code,
        }

    def _explain(self, rule: RecommendationRule, entity_type: str, code: str, context: dict) -> str:
        if rule.explanation_template:
            return rule.explanation_template.format(
                entity_type=entity_type, code=code,
                vertical=context.get("vertical_type", ""), **context,
            )
        return f"Recommended {entity_type} '{code}' based on rule '{rule.code}'"

    def _rank_recommendations(self, recs: list[dict]) -> list[dict]:
        """Sort by confidence_score descending; deduplicate by entity_type+entity_id."""
        seen: set[str] = set()
        unique: list[dict] = []
        for r in sorted(recs, key=lambda x: x.get("confidence_score", 0), reverse=True):
            key = f"{r.get('entity_type')}:{r.get('entity_id') or r.get('entity_code')}"
            if key not in seen:
                seen.add(key)
                unique.append(r)
        return unique

    async def validate_recommendation(self, entity_type: str, entity_id: str) -> dict:
        """Verify a specific entity exists and is active."""
        eid = uuid.UUID(entity_id)
        if entity_type == "brand":
            obj = await self.db.scalar(select(Brand).where(Brand.id == eid))
            return {"valid": bool(obj and obj.status == "active"), "entity_type": entity_type}
        if entity_type == "service_option":
            obj = await self.db.scalar(select(MasterServiceOption).where(MasterServiceOption.id == eid))
            return {"valid": bool(obj and obj.status == "active"), "entity_type": entity_type}
        if entity_type == "issue_type":
            obj = await self.db.scalar(select(MasterIssueType).where(MasterIssueType.id == eid))
            return {"valid": bool(obj and obj.status == "active"), "entity_type": entity_type}
        return {"valid": False, "entity_type": entity_type, "error": "Unknown entity type"}

    async def track_recommendation_result(
        self,
        db: AsyncSession,
        context_type: str,
        context_id: str | None,
        rule_id: uuid.UUID | None,
        rule_type: str | None,
        entity_type: str | None,
        entity_id: uuid.UUID | None,
        payload: dict | None,
        explanation: str | None,
        confidence_score: Decimal | None,
        actor_user_id: uuid.UUID | None,
        tenant_id: uuid.UUID | None,
        request_id: str | None,
        status: str = "shown",
    ) -> RecommendationResult:
        result = RecommendationResult(
            context_type=context_type,
            context_id=context_id,
            rule_id=rule_id,
            rule_type=rule_type,
            recommended_entity_type=entity_type,
            recommended_entity_id=entity_id,
            recommended_payload_json=payload,
            explanation=explanation,
            confidence_score=confidence_score,
            actor_user_id=actor_user_id,
            tenant_id=tenant_id,
            request_id=request_id,
            status=status,
        )
        db.add(result)
        await db.flush()
        return result

    async def accept_recommendation(self, result_id: uuid.UUID) -> dict:
        result = await self.db.scalar(
            select(RecommendationResult).where(RecommendationResult.id == result_id)
        )
        if not result:
            raise ValueError(f"Recommendation result {result_id} not found")
        result.status = "accepted"
        result.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        return result.to_dict()

    async def reject_recommendation(self, result_id: uuid.UUID, reason: str | None = None) -> dict:
        result = await self.db.scalar(
            select(RecommendationResult).where(RecommendationResult.id == result_id)
        )
        if not result:
            raise ValueError(f"Recommendation result {result_id} not found")
        result.status = "rejected"
        result.updated_at = datetime.now(timezone.utc)
        if reason and result.recommended_payload_json:
            result.recommended_payload_json = {**result.recommended_payload_json, "reject_reason": reason}
        elif reason:
            result.recommended_payload_json = {"reject_reason": reason}
        await self.db.commit()
        return result.to_dict()
