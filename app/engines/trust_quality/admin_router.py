"""Trust & Quality Engine admin router — /v1/admin/trust-quality/ (Phase 1)."""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import P, require_permission
from app.dependencies.db import get_db
from app.engines.trust_quality.service import TrustQualityService
from app.schemas.base import ApiResponse, ok

router = APIRouter(prefix="/v1/admin/trust-quality", tags=["admin-trust-quality"])


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


def _svc(db: AsyncSession, u) -> TrustQualityService:
    return TrustQualityService(db, uuid.UUID(u.user_id) if u.user_id else None, u.role)


# ── Badge Definitions ────────────────────────────────────────────────────────

@router.get("/badges/definitions")
async def list_badge_definitions(
    r: Request, target_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db), u=Depends(require_permission(P.BADGE_MANAGEMENT_READ)),
) -> ApiResponse[dict]:
    return ok({"items": await _svc(db, u).list_badge_definitions(target_type)}, _rid(r))


@router.post("/badges/definitions")
async def create_badge_definition(
    r: Request, body: dict,
    db: AsyncSession = Depends(get_db), u=Depends(require_permission(P.BADGE_MANAGEMENT_WRITE)),
) -> ApiResponse[dict]:
    return ok(await _svc(db, u).create_badge_definition(body), _rid(r))


@router.put("/badges/definitions/{badge_id}")
async def update_badge_definition(
    r: Request, badge_id: uuid.UUID, body: dict,
    db: AsyncSession = Depends(get_db), u=Depends(require_permission(P.BADGE_MANAGEMENT_WRITE)),
) -> ApiResponse[dict]:
    return ok(await _svc(db, u).update_badge_definition(badge_id, body), _rid(r))


# ── Badge Rules ──────────────────────────────────────────────────────────────

@router.get("/badge-rules")
async def list_badge_rules(
    r: Request, target_type: Optional[str] = Query(None), status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db), u=Depends(require_permission(P.BADGE_RULES_READ)),
) -> ApiResponse[dict]:
    return ok({"items": await _svc(db, u).list_badge_rules(target_type, status)}, _rid(r))


@router.get("/badge-rules/{rule_id}")
async def get_badge_rule(
    r: Request, rule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db), u=Depends(require_permission(P.BADGE_RULES_READ)),
) -> ApiResponse[dict]:
    return ok(await _svc(db, u).get_badge_rule(rule_id), _rid(r))


@router.post("/badge-rules")
async def create_badge_rule(
    r: Request, body: dict,
    db: AsyncSession = Depends(get_db), u=Depends(require_permission(P.BADGE_RULES_WRITE)),
) -> ApiResponse[dict]:
    return ok(await _svc(db, u).create_badge_rule(body), _rid(r))


@router.put("/badge-rules/{rule_id}")
async def update_badge_rule(
    r: Request, rule_id: uuid.UUID, body: dict,
    db: AsyncSession = Depends(get_db), u=Depends(require_permission(P.BADGE_RULES_WRITE)),
) -> ApiResponse[dict]:
    return ok(await _svc(db, u).update_badge_rule(rule_id, body), _rid(r))


@router.post("/badge-rules/{rule_id}/activate")
async def activate_badge_rule(
    r: Request, rule_id: uuid.UUID, body: dict,
    db: AsyncSession = Depends(get_db), u=Depends(require_permission(P.BADGE_RULES_WRITE)),
) -> ApiResponse[dict]:
    return ok(await _svc(db, u).activate_badge_rule(rule_id, body.get("reason", "")), _rid(r))


@router.post("/badge-rules/{rule_id}/deactivate")
async def deactivate_badge_rule(
    r: Request, rule_id: uuid.UUID, body: dict,
    db: AsyncSession = Depends(get_db), u=Depends(require_permission(P.BADGE_RULES_WRITE)),
) -> ApiResponse[dict]:
    return ok(await _svc(db, u).deactivate_badge_rule(rule_id, body.get("reason", "")), _rid(r))


@router.post("/badge-rules/{rule_id}/simulate")
async def simulate_badge_rule(
    r: Request, rule_id: uuid.UUID, body: dict,
    db: AsyncSession = Depends(get_db), u=Depends(require_permission(P.BADGE_RULES_READ)),
) -> ApiResponse[dict]:
    return ok(await _svc(db, u).simulate_badge_rule(rule_id, body.get("metrics", {})), _rid(r))


# ── Badge Assignments (Badge Management) ────────────────────────────────────

@router.get("/badges/earned")
async def list_earned_badges(
    r: Request, target_type: str = Query(...), target_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db), u=Depends(require_permission(P.BADGE_MANAGEMENT_READ)),
) -> ApiResponse[dict]:
    """The badges a specific provider/staff/customer/service currently holds."""
    return ok({"items": await _svc(db, u).list_earned_badges(target_type, target_id, "admin")}, _rid(r))


@router.post("/badges/manual-award")
async def manual_award_badge(
    r: Request, body: dict,
    db: AsyncSession = Depends(get_db), u=Depends(require_permission(P.BADGE_MANAGEMENT_WRITE)),
) -> ApiResponse[dict]:
    svc = _svc(db, u)
    return ok(await svc.manual_award_badge(
        uuid.UUID(body["badge_id"]), body["target_type"], uuid.UUID(body["target_id"]),
        body.get("reason", "")), _rid(r))


@router.post("/badges/{assignment_id}/revoke")
async def revoke_badge(
    r: Request, assignment_id: uuid.UUID, body: dict,
    db: AsyncSession = Depends(get_db), u=Depends(require_permission(P.BADGE_MANAGEMENT_WRITE)),
) -> ApiResponse[dict]:
    return ok(await _svc(db, u).revoke_badge(assignment_id, body.get("reason", "")), _rid(r))


@router.post("/recalculate/badges")
async def recalculate_badges(
    r: Request, body: dict,
    db: AsyncSession = Depends(get_db), u=Depends(require_permission(P.RECALCULATION_JOBS_RUN)),
) -> ApiResponse[dict]:
    svc = _svc(db, u)
    result = await svc.recalculate_badges_for_target(
        body["target_type"], uuid.UUID(body["target_id"]), body.get("metrics", {}))
    return ok({"changes": result}, _rid(r))


# ── Health Formulas ──────────────────────────────────────────────────────────

@router.get("/health-rules")
async def list_health_formulas(
    r: Request, target_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db), u=Depends(require_permission(P.HEALTH_RULES_READ)),
) -> ApiResponse[dict]:
    return ok({"items": await _svc(db, u).list_health_formulas(target_type)}, _rid(r))


@router.get("/health-rules/{formula_id}")
async def get_health_formula(
    r: Request, formula_id: uuid.UUID,
    db: AsyncSession = Depends(get_db), u=Depends(require_permission(P.HEALTH_RULES_READ)),
) -> ApiResponse[dict]:
    return ok(await _svc(db, u).get_health_formula(formula_id), _rid(r))


@router.post("/health-rules")
async def create_health_formula(
    r: Request, body: dict,
    db: AsyncSession = Depends(get_db), u=Depends(require_permission(P.HEALTH_RULES_WRITE)),
) -> ApiResponse[dict]:
    return ok(await _svc(db, u).create_health_formula(body), _rid(r))


@router.put("/health-rules/{formula_id}")
async def update_health_formula(
    r: Request, formula_id: uuid.UUID, body: dict,
    db: AsyncSession = Depends(get_db), u=Depends(require_permission(P.HEALTH_RULES_WRITE)),
) -> ApiResponse[dict]:
    return ok(await _svc(db, u).update_health_formula(formula_id, body), _rid(r))


@router.post("/health-rules/{formula_id}/activate")
async def activate_health_formula(
    r: Request, formula_id: uuid.UUID, body: dict,
    db: AsyncSession = Depends(get_db), u=Depends(require_permission(P.HEALTH_RULES_WRITE)),
) -> ApiResponse[dict]:
    return ok(await _svc(db, u).activate_health_formula(formula_id, body.get("reason", "")), _rid(r))


@router.post("/health-rules/{formula_id}/deactivate")
async def deactivate_health_formula(
    r: Request, formula_id: uuid.UUID, body: dict,
    db: AsyncSession = Depends(get_db), u=Depends(require_permission(P.HEALTH_RULES_WRITE)),
) -> ApiResponse[dict]:
    return ok(await _svc(db, u).deactivate_health_formula(formula_id, body.get("reason", "")), _rid(r))


@router.post("/health-rules/{formula_id}/simulate")
async def simulate_health_formula(
    r: Request, formula_id: uuid.UUID, body: dict,
    db: AsyncSession = Depends(get_db), u=Depends(require_permission(P.HEALTH_RULES_READ)),
) -> ApiResponse[dict]:
    return ok(await _svc(db, u).simulate_health_formula(formula_id, body.get("metrics", {})), _rid(r))


@router.post("/recalculate/health")
async def recalculate_health(
    r: Request, body: dict,
    db: AsyncSession = Depends(get_db), u=Depends(require_permission(P.RECALCULATION_JOBS_RUN)),
) -> ApiResponse[dict]:
    svc = _svc(db, u)
    result = await svc.recalculate_health_for_target(
        uuid.UUID(body["formula_id"]), body["target_type"], uuid.UUID(body["target_id"]), body.get("metrics", {}))
    return ok(result, _rid(r))


# ── Risk Scoring ─────────────────────────────────────────────────────────────

@router.post("/recalculate/risk")
async def recalculate_risk(
    r: Request, body: dict,
    db: AsyncSession = Depends(get_db), u=Depends(require_permission(P.RECALCULATION_JOBS_RUN)),
) -> ApiResponse[dict]:
    svc = _svc(db, u)
    result = await svc.recalculate_risk_for_target(
        body["target_type"], uuid.UUID(body["target_id"]), body.get("metrics", {}))
    return ok(result, _rid(r))


# ── Recalculation Jobs ───────────────────────────────────────────────────────

@router.post("/recalculate/all")
async def recalculate_run_job(
    r: Request, body: dict,
    db: AsyncSession = Depends(get_db), u=Depends(require_permission(P.RECALCULATION_JOBS_RUN)),
) -> ApiResponse[dict]:
    svc = _svc(db, u)
    return ok(await svc.run_recalculation_job(
        body.get("job_type", "all"), body.get("scope_type", "all"),
        uuid.UUID(body["scope_id"]) if body.get("scope_id") else None), _rid(r))


@router.get("/recalculation-jobs")
async def list_recalculation_jobs(
    r: Request,
    db: AsyncSession = Depends(get_db), u=Depends(require_permission(P.RECALCULATION_JOBS_READ)),
) -> ApiResponse[dict]:
    return ok({"items": await _svc(db, u).list_recalculation_jobs()}, _rid(r))


# ── Seed Defaults ────────────────────────────────────────────────────────────

@router.post("/seed-defaults/preview")
async def seed_defaults_preview(
    r: Request,
    db: AsyncSession = Depends(get_db), u=Depends(require_permission(P.HEALTH_RULES_WRITE)),
) -> ApiResponse[dict]:
    return ok(await _svc(db, u).seed_defaults_preview(), _rid(r))


@router.post("/seed-defaults")
async def seed_defaults(
    r: Request,
    db: AsyncSession = Depends(get_db), u=Depends(require_permission(P.HEALTH_RULES_WRITE)),
) -> ApiResponse[dict]:
    return ok(await _svc(db, u).seed_defaults(), _rid(r))


# ── Audit ────────────────────────────────────────────────────────────────────

@router.get("/audit-logs")
async def list_audit_logs(
    r: Request, target_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db), u=Depends(require_permission(P.TRUST_QUALITY_READ)),
) -> ApiResponse[dict]:
    return ok({"items": await _svc(db, u).list_audit_logs(target_type)}, _rid(r))
