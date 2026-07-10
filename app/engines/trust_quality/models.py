"""Trust & Quality Engine models — migration 095 (Phase 1).

Badge Engine + Badge Rule Engine + Health Engine + Health Rule Engine +
Risk Scoring Engine + Recalculation Jobs + Audit Logs.
"""
import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, Text, DateTime, Integer, Numeric, Index, UniqueConstraint, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class BadgeDefinition(Base):
    __tablename__ = "badge_definitions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    badge_key: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    icon: Mapped[str | None] = mapped_column(String(100))
    color: Mapped[str | None] = mapped_column(String(30))
    target_type: Mapped[str] = mapped_column(String(30), nullable=False)
    customer_visible: Mapped[bool] = mapped_column(Boolean, default=False)
    tenant_visible: Mapped[bool] = mapped_column(Boolean, default=True)
    admin_only: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    def to_dict(self) -> dict:
        return {
            "id": str(self.id), "badge_key": self.badge_key, "name": self.name,
            "description": self.description, "icon": self.icon, "color": self.color,
            "target_type": self.target_type, "customer_visible": self.customer_visible,
            "tenant_visible": self.tenant_visible, "admin_only": self.admin_only,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class BadgeRule(Base):
    __tablename__ = "badge_rules"
    __table_args__ = (
        Index("ix_badge_rule_badge_id2", "badge_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_key: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    badge_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("badge_definitions.id", ondelete="CASCADE"), nullable=False)
    target_type: Mapped[str] = mapped_column(String(30), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(30), nullable=False)
    scope_type: Mapped[str] = mapped_column(String(20), default="global")
    scope_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    auto_award: Mapped[bool] = mapped_column(Boolean, default=True)
    manual_award_allowed: Mapped[bool] = mapped_column(Boolean, default=True)
    requires_admin_review: Mapped[bool] = mapped_column(Boolean, default=False)
    expiry_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    expiry_days: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    def to_dict(self) -> dict:
        return {
            "id": str(self.id), "rule_key": self.rule_key, "badge_id": str(self.badge_id),
            "target_type": self.target_type, "rule_type": self.rule_type,
            "scope_type": self.scope_type, "scope_id": str(self.scope_id) if self.scope_id else None,
            "auto_award": self.auto_award, "manual_award_allowed": self.manual_award_allowed,
            "requires_admin_review": self.requires_admin_review,
            "expiry_enabled": self.expiry_enabled, "expiry_days": self.expiry_days,
            "status": self.status, "version": self.version,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class BadgeRuleCriteria(Base):
    __tablename__ = "badge_rule_criteria"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    badge_rule_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("badge_rules.id", ondelete="CASCADE"), nullable=False)
    metric_key: Mapped[str] = mapped_column(String(80), nullable=False)
    operator: Mapped[str] = mapped_column(String(30), nullable=False)
    value_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    time_window_days: Mapped[int | None] = mapped_column(Integer)
    is_required: Mapped[bool] = mapped_column(Boolean, default=True)
    weight: Mapped[float | None] = mapped_column(Numeric(5, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    def to_dict(self) -> dict:
        return {
            "id": str(self.id), "metric_key": self.metric_key, "operator": self.operator,
            "value": self.value_json, "time_window_days": self.time_window_days,
            "is_required": self.is_required, "weight": float(self.weight) if self.weight is not None else None,
        }


class BadgeRuleRemovalCriteria(Base):
    __tablename__ = "badge_rule_removal_criteria"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    badge_rule_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("badge_rules.id", ondelete="CASCADE"), nullable=False)
    metric_key: Mapped[str] = mapped_column(String(80), nullable=False)
    operator: Mapped[str] = mapped_column(String(30), nullable=False)
    value_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    time_window_days: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    def to_dict(self) -> dict:
        return {
            "id": str(self.id), "metric_key": self.metric_key, "operator": self.operator,
            "value": self.value_json, "time_window_days": self.time_window_days,
        }


class BadgeAssignment(Base):
    __tablename__ = "badge_assignments"
    __table_args__ = (
        Index("ix_badge_assign_target2", "target_type", "target_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    badge_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("badge_definitions.id", ondelete="CASCADE"), nullable=False)
    badge_rule_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("badge_rules.id", ondelete="SET NULL"))
    target_type: Mapped[str] = mapped_column(String(30), nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active")
    award_source: Mapped[str] = mapped_column(String(30), default="auto_rule")
    assigned_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    assigned_reason: Mapped[str | None] = mapped_column(Text)
    earned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    revoked_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    def to_dict(self) -> dict:
        return {
            "id": str(self.id), "badge_id": str(self.badge_id),
            "badge_rule_id": str(self.badge_rule_id) if self.badge_rule_id else None,
            "target_type": self.target_type, "target_id": str(self.target_id),
            "status": self.status, "award_source": self.award_source,
            "assigned_reason": self.assigned_reason,
            "earned_at": self.earned_at.isoformat() if self.earned_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
            "revoked_reason": self.revoked_reason,
        }


class HealthFormula(Base):
    __tablename__ = "health_formulas"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    formula_key: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    target_type: Mapped[str] = mapped_column(String(30), nullable=False)
    scope_type: Mapped[str] = mapped_column(String(20), default="global")
    scope_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    base_score: Mapped[float] = mapped_column(Numeric(6, 2), default=100)
    min_score: Mapped[float] = mapped_column(Numeric(6, 2), default=0)
    max_score: Mapped[float] = mapped_column(Numeric(6, 2), default=100)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    def to_dict(self) -> dict:
        return {
            "id": str(self.id), "formula_key": self.formula_key, "name": self.name,
            "target_type": self.target_type, "scope_type": self.scope_type,
            "scope_id": str(self.scope_id) if self.scope_id else None,
            "base_score": float(self.base_score), "min_score": float(self.min_score),
            "max_score": float(self.max_score), "status": self.status, "version": self.version,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class HealthFormulaComponent(Base):
    __tablename__ = "health_formula_components"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    formula_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("health_formulas.id", ondelete="CASCADE"), nullable=False)
    metric_key: Mapped[str] = mapped_column(String(80), nullable=False)
    weight_percent: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    direction: Mapped[str] = mapped_column(String(10), default="positive")
    min_value: Mapped[float | None] = mapped_column(Numeric(12, 4))
    max_value: Mapped[float | None] = mapped_column(Numeric(12, 4))
    normalization_method: Mapped[str] = mapped_column(String(30), default="linear")
    is_required: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    def to_dict(self) -> dict:
        return {
            "id": str(self.id), "metric_key": self.metric_key,
            "weight_percent": float(self.weight_percent), "direction": self.direction,
            "min_value": float(self.min_value) if self.min_value is not None else None,
            "max_value": float(self.max_value) if self.max_value is not None else None,
            "normalization_method": self.normalization_method, "is_required": self.is_required,
        }


class HealthPenaltyRule(Base):
    __tablename__ = "health_penalty_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    formula_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("health_formulas.id", ondelete="CASCADE"), nullable=False)
    metric_key: Mapped[str] = mapped_column(String(80), nullable=False)
    operator: Mapped[str] = mapped_column(String(30), nullable=False)
    value_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    penalty_points: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    hard_override_score: Mapped[float | None] = mapped_column(Numeric(6, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    def to_dict(self) -> dict:
        return {
            "id": str(self.id), "metric_key": self.metric_key, "operator": self.operator,
            "value": self.value_json, "penalty_points": float(self.penalty_points),
            "hard_override_score": float(self.hard_override_score) if self.hard_override_score is not None else None,
        }


class HealthBonusRule(Base):
    __tablename__ = "health_bonus_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    formula_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("health_formulas.id", ondelete="CASCADE"), nullable=False)
    metric_key: Mapped[str] = mapped_column(String(80), nullable=False)
    operator: Mapped[str] = mapped_column(String(30), nullable=False)
    value_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    bonus_points: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    max_bonus_cap: Mapped[float | None] = mapped_column(Numeric(6, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    def to_dict(self) -> dict:
        return {
            "id": str(self.id), "metric_key": self.metric_key, "operator": self.operator,
            "value": self.value_json, "bonus_points": float(self.bonus_points),
            "max_bonus_cap": float(self.max_bonus_cap) if self.max_bonus_cap is not None else None,
        }


class HealthBandRule(Base):
    __tablename__ = "health_band_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    formula_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("health_formulas.id", ondelete="CASCADE"), nullable=False)
    band_key: Mapped[str] = mapped_column(String(40), nullable=False)
    band_name: Mapped[str] = mapped_column(String(80), nullable=False)
    min_score: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    max_score: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    color: Mapped[str | None] = mapped_column(String(30))
    bookable_allowed: Mapped[bool] = mapped_column(Boolean, default=True)
    recommended_action: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    def to_dict(self) -> dict:
        return {
            "id": str(self.id), "band_key": self.band_key, "band_name": self.band_name,
            "min_score": float(self.min_score), "max_score": float(self.max_score),
            "color": self.color, "bookable_allowed": self.bookable_allowed,
            "recommended_action": self.recommended_action,
        }


class HealthScore(Base):
    __tablename__ = "health_scores"
    __table_args__ = (
        UniqueConstraint("target_type", "target_id", "formula_id", name="uq_health_score_target_formula"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    target_type: Mapped[str] = mapped_column(String(30), nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    formula_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("health_formulas.id", ondelete="CASCADE"), nullable=False)
    score: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    band_key: Mapped[str | None] = mapped_column(String(40))
    risk_level: Mapped[str | None] = mapped_column(String(30))
    component_breakdown_json: Mapped[dict | None] = mapped_column(JSONB)
    penalties_json: Mapped[dict | None] = mapped_column(JSONB)
    bonuses_json: Mapped[dict | None] = mapped_column(JSONB)
    recommended_actions_json: Mapped[dict | None] = mapped_column(JSONB)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    def to_dict(self) -> dict:
        return {
            "id": str(self.id), "target_type": self.target_type, "target_id": str(self.target_id),
            "formula_id": str(self.formula_id), "score": float(self.score),
            "band_key": self.band_key, "risk_level": self.risk_level,
            "component_breakdown": self.component_breakdown_json,
            "penalties": self.penalties_json, "bonuses": self.bonuses_json,
            "recommended_actions": self.recommended_actions_json,
            "calculated_at": self.calculated_at.isoformat() if self.calculated_at else None,
        }


class RiskRule(Base):
    __tablename__ = "risk_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_key: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    target_type: Mapped[str] = mapped_column(String(30), nullable=False)
    scope_type: Mapped[str] = mapped_column(String(20), default="global")
    scope_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    condition_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(30), nullable=False)
    risk_score_delta: Mapped[float] = mapped_column(Numeric(6, 2), default=0)
    recommended_actions_json: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    def to_dict(self) -> dict:
        return {
            "id": str(self.id), "rule_key": self.rule_key, "name": self.name,
            "target_type": self.target_type, "condition": self.condition_json,
            "risk_level": self.risk_level, "risk_score_delta": float(self.risk_score_delta),
            "recommended_actions": self.recommended_actions_json, "status": self.status,
        }


class RiskScore(Base):
    __tablename__ = "risk_scores"
    __table_args__ = (
        UniqueConstraint("target_type", "target_id", name="uq_risk_score_target"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    target_type: Mapped[str] = mapped_column(String(30), nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    risk_score: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(30), nullable=False)
    reasons_json: Mapped[dict | None] = mapped_column(JSONB)
    recommended_actions_json: Mapped[dict | None] = mapped_column(JSONB)
    bookable_impact: Mapped[bool] = mapped_column(Boolean, default=False)
    finance_impact: Mapped[bool] = mapped_column(Boolean, default=False)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    def to_dict(self) -> dict:
        return {
            "id": str(self.id), "target_type": self.target_type, "target_id": str(self.target_id),
            "risk_score": float(self.risk_score), "risk_level": self.risk_level,
            "reasons": self.reasons_json or [], "recommended_actions": self.recommended_actions_json or [],
            "bookable_impact": self.bookable_impact, "finance_impact": self.finance_impact,
            "calculated_at": self.calculated_at.isoformat() if self.calculated_at else None,
        }


class TrustQualityRecalculationJob(Base):
    __tablename__ = "trust_quality_recalculation_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_type: Mapped[str] = mapped_column(String(20), nullable=False)
    scope_type: Mapped[str] = mapped_column(String(20), default="all")
    scope_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    status: Mapped[str] = mapped_column(String(20), default="queued")
    total_count: Mapped[int] = mapped_column(Integer, default=0)
    processed_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    triggered_by: Mapped[str] = mapped_column(String(30), default="manual")
    triggered_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_summary: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    def to_dict(self) -> dict:
        return {
            "id": str(self.id), "job_type": self.job_type, "scope_type": self.scope_type,
            "scope_id": str(self.scope_id) if self.scope_id else None, "status": self.status,
            "total_count": self.total_count, "processed_count": self.processed_count,
            "failed_count": self.failed_count, "triggered_by": self.triggered_by,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_summary": self.error_summary,
        }


class TrustQualityAuditLog(Base):
    __tablename__ = "trust_quality_audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    action_type: Mapped[str] = mapped_column(String(80), nullable=False)
    target_type: Mapped[str | None] = mapped_column(String(30))
    target_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    actor_role: Mapped[str | None] = mapped_column(String(40))
    old_value_json: Mapped[dict | None] = mapped_column(JSONB)
    new_value_json: Mapped[dict | None] = mapped_column(JSONB)
    reason: Mapped[str | None] = mapped_column(Text)
    request_id: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    def to_dict(self) -> dict:
        return {
            "id": str(self.id), "action_type": self.action_type,
            "target_type": self.target_type, "target_id": str(self.target_id) if self.target_id else None,
            "actor_role": self.actor_role, "old_value": self.old_value_json,
            "new_value": self.new_value_json, "reason": self.reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
