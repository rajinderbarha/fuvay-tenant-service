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


async def _metrics_for(svc: TrustQualityService, target_type: str,
                       target_id: uuid.UUID, body: dict) -> dict:
    """Metrics for a single-target rescore.

    An explicit `metrics` object in the body is honoured — that is how an admin
    tries out a hypothetical. When it is absent the engine reads the target's
    live metrics instead, which is what "recalculate this provider now" means and
    what the console's row-level action sends. Previously the body was the only
    source, so an omitted `metrics` silently scored the target against an empty
    metric set and wrote a zero.
    """
    if body.get("metrics"):
        return body["metrics"]
    return await svc.gather_live_metrics(target_type, target_id)


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

@router.get("/badge-assignments")
async def list_badge_assignments(
    r: Request,
    q: Optional[str] = Query(None, max_length=160),
    target_type: Optional[str] = Query(None),
    badge_key: Optional[str] = Query(None),
    award_source: Optional[str] = Query(None),
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    u=Depends(require_permission(P.BADGE_MANAGEMENT_READ)),
) -> ApiResponse[dict]:
    """Paged directory of badges currently held by providers and staff."""
    return ok(await _svc(db, u).list_badge_assignments(
        q=q, target_type=target_type, badge_key=badge_key,
        award_source=award_source, limit=limit, offset=offset,
    ), _rid(r))


@router.get("/badges/earned")
async def list_earned_badges(
    r: Request, target_type: str = Query(...), target_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db), u=Depends(require_permission(P.BADGE_MANAGEMENT_READ)),
) -> ApiResponse[dict]:
    """The fixed trust badges a specific tenant, staff member or technician currently holds."""
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
    target_type, target_id = body["target_type"], uuid.UUID(body["target_id"])
    metrics = await _metrics_for(svc, target_type, target_id, body)
    result = await svc.recalculate_badges_for_target(target_type, target_id, metrics)
    return ok({"changes": result, "metrics": metrics}, _rid(r))


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
    target_type, target_id = body["target_type"], uuid.UUID(body["target_id"])
    metrics = await _metrics_for(svc, target_type, target_id, body)
    result = await svc.recalculate_health_for_target(
        uuid.UUID(body["formula_id"]), target_type, target_id, metrics)
    return ok(result, _rid(r))


# ── Risk Scoring ─────────────────────────────────────────────────────────────

@router.post("/recalculate/risk")
async def recalculate_risk(
    r: Request, body: dict,
    db: AsyncSession = Depends(get_db), u=Depends(require_permission(P.RECALCULATION_JOBS_RUN)),
) -> ApiResponse[dict]:
    svc = _svc(db, u)
    target_type, target_id = body["target_type"], uuid.UUID(body["target_id"])
    metrics = await _metrics_for(svc, target_type, target_id, body)
    result = await svc.recalculate_risk_for_target(target_type, target_id, metrics)
    return ok(result, _rid(r))


# ── Recalculation Jobs ───────────────────────────────────────────────────────

@router.post("/recalculate/all")
async def recalculate_run_job(
    r: Request, body: dict,
    db: AsyncSession = Depends(get_db), u=Depends(require_permission(P.RECALCULATION_JOBS_RUN)),
) -> ApiResponse[dict]:
    """Queue a platform-wide sweep. Returns as soon as the job is queued.

    The sweep runs in the background worker rather than in this request — see
    `TrustQualityService.enqueue_recalculation_job`.
    """
    svc = _svc(db, u)
    return ok(await svc.enqueue_recalculation_job(
        body.get("job_type", "all"), body.get("scope_type", "all"),
        uuid.UUID(body["scope_id"]) if body.get("scope_id") else None), _rid(r))


@router.get("/recalculation-jobs")
async def list_recalculation_jobs(
    r: Request, status: Optional[str] = Query(None),
    limit: int = Query(25, ge=1, le=200), offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db), u=Depends(require_permission(P.RECALCULATION_JOBS_READ)),
) -> ApiResponse[dict]:
    return ok(await _svc(db, u).list_recalculation_jobs(status, limit, offset), _rid(r))


@router.get("/recalculation-jobs/{job_id}")
async def get_recalculation_job(
    r: Request, job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db), u=Depends(require_permission(P.RECALCULATION_JOBS_READ)),
) -> ApiResponse[dict]:
    """One job's live progress. The console polls this while a sweep is running."""
    return ok(await _svc(db, u).get_recalculation_job(job_id), _rid(r))


@router.post("/recalculation-jobs/{job_id}/cancel")
async def cancel_recalculation_job(
    r: Request, job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db), u=Depends(require_permission(P.RECALCULATION_JOBS_RUN)),
) -> ApiResponse[dict]:
    return ok(await _svc(db, u).cancel_recalculation_job(job_id), _rid(r))


# ── Engine Output (scores) ───────────────────────────────────────────────────

@router.get("/overview")
async def engine_overview(
    r: Request,
    db: AsyncSession = Depends(get_db), u=Depends(require_permission(P.TRUST_QUALITY_READ)),
) -> ApiResponse[dict]:
    """Headline counts across all three engines."""
    return ok(await _svc(db, u).get_engine_overview(), _rid(r))


@router.get("/health-scores")
async def list_health_scores(
    r: Request, target_type: Optional[str] = Query(None), band_key: Optional[str] = Query(None),
    formula_id: Optional[uuid.UUID] = Query(None),
    limit: int = Query(25, ge=1, le=200), offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db), u=Depends(require_permission(P.HEALTH_MANAGEMENT_READ)),
) -> ApiResponse[dict]:
    """The health engine's output: who scored what, worst first."""
    return ok(await _svc(db, u).list_health_scores(
        target_type, band_key, formula_id, limit, offset), _rid(r))


@router.get("/risk-scores")
async def list_risk_scores(
    r: Request, target_type: Optional[str] = Query(None), risk_level: Optional[str] = Query(None),
    limit: int = Query(25, ge=1, le=200), offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db), u=Depends(require_permission(P.RISK_SCORING_READ)),
) -> ApiResponse[dict]:
    """The risk engine's output: who is flagged and what it blocks."""
    return ok(await _svc(db, u).list_risk_scores(
        target_type, risk_level, limit, offset), _rid(r))


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
    r: Request, target_type: Optional[str] = Query(None), action_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db), u=Depends(require_permission(P.TRUST_QUALITY_READ)),
) -> ApiResponse[dict]:
    return ok(await _svc(db, u).list_audit_logs(target_type, action_type, limit, offset), _rid(r))
