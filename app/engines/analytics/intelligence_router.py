"""Intelligence Command Center Router — /v1/admin/intelligence (migration 103)."""
from __future__ import annotations
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import require_super_admin
from app.dependencies.db import get_db
from app.engines.analytics.intelligence_service import IntelligenceService
from app.schemas.base import ok

_svc = IntelligenceService()


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


router = APIRouter(
    prefix="/v1/admin/intelligence",
    tags=["Intelligence Command Center"],
    dependencies=[Depends(require_super_admin)],
)


# ── Summary ──────────────────────────────────────────────────────────────────

@router.get("/summary")
async def get_summary(r: Request, db: AsyncSession = Depends(get_db)):
    data = await _svc.get_summary(db)
    return ok(data, _rid(r), "intelligence.summary")


# ── RAG static paths BEFORE parameterized ────────────────────────────────────

@router.get("/rag/summary")
async def get_rag_summary(r: Request, db: AsyncSession = Depends(get_db)):
    data = await _svc.get_rag_summary(db)
    return ok(data, _rid(r), "intelligence.rag.summary")


@router.get("/rag/query-logs")
async def list_query_logs(
    r: Request, db: AsyncSession = Depends(get_db),
    kb_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
):
    data = await _svc.list_query_logs(db, kb_id=kb_id, page=page, page_size=page_size)
    return ok(data, _rid(r), "intelligence.rag.query_logs")


@router.get("/rag/retrieval-quality")
async def get_retrieval_quality(r: Request, db: AsyncSession = Depends(get_db)):
    data = await _svc.get_retrieval_quality(db)
    return ok(data, _rid(r), "intelligence.rag.retrieval_quality")


# Knowledge base routes moved to kb_router (app/engines/analytics/kb_router.py)
# prefix: /v1/admin/intelligence/knowledge-bases


# ── Events (static paths) ────────────────────────────────────────────────────

@router.get("/events/summary")
async def get_event_summary(r: Request, db: AsyncSession = Depends(get_db)):
    data = await _svc.get_event_summary(db)
    return ok(data, _rid(r), "intelligence.events.summary")


@router.get("/events/sources")
async def get_event_sources(r: Request, db: AsyncSession = Depends(get_db)):
    data = await _svc.get_event_sources(db)
    return ok(data, _rid(r), "intelligence.events.sources")


@router.get("/events/failures")
async def get_event_failures(r: Request, db: AsyncSession = Depends(get_db)):
    data = await _svc.get_event_failures(db)
    return ok(data, _rid(r), "intelligence.events.failures")


# ── Risk (static before parameterized) ───────────────────────────────────────

@router.get("/risk/summary")
async def get_risk_summary(r: Request, db: AsyncSession = Depends(get_db)):
    data = await _svc.get_risk_summary(db)
    return ok(data, _rid(r), "intelligence.risk.summary")


@router.get("/risk/entities")
async def list_risk_entities(
    r: Request, db: AsyncSession = Depends(get_db),
    risk_level: Optional[str] = Query(None),
    entity_type: Optional[str] = Query(None),
    page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
):
    data = await _svc.list_risk_entities(db, risk_level=risk_level, entity_type=entity_type, page=page, page_size=page_size)
    return ok(data, _rid(r), "intelligence.risk.entities")


@router.get("/risk/{entity_type}/{entity_id}")
async def get_risk_entity(entity_type: str, entity_id: str, r: Request, db: AsyncSession = Depends(get_db)):
    data = await _svc.get_risk_entity(db, entity_type, entity_id)
    if data is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Risk entity not found")
    return ok(data, _rid(r), "intelligence.risk.entity")


@router.post("/risk/{entity_type}/{entity_id}/recompute")
async def recompute_risk(entity_type: str, entity_id: str, r: Request, db: AsyncSession = Depends(get_db)):
    data = await _svc.recompute_risk(db, entity_type, entity_id, None)
    return ok(data, _rid(r), "intelligence.risk.recompute")


# ── Anomalies (static run-scan BEFORE parameterized) ─────────────────────────

@router.get("/anomalies")
async def list_anomalies(
    r: Request, db: AsyncSession = Depends(get_db),
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
):
    data = await _svc.list_anomalies(db, status=status, severity=severity, page=page, page_size=page_size)
    return ok(data, _rid(r), "intelligence.anomalies.list")


@router.post("/anomalies/run-scan")
async def run_anomaly_scan(r: Request, db: AsyncSession = Depends(get_db)):
    data = await _svc.run_anomaly_scan(db, None)
    return ok(data, _rid(r), "intelligence.anomalies.run_scan")


@router.get("/anomalies/{anomaly_id}")
async def get_anomaly(anomaly_id: str, r: Request, db: AsyncSession = Depends(get_db)):
    data = await _svc.get_anomaly(db, anomaly_id)
    if data is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Anomaly not found")
    return ok(data, _rid(r), "intelligence.anomalies.get")


@router.post("/anomalies/{anomaly_id}/investigate")
async def investigate_anomaly(anomaly_id: str, r: Request, db: AsyncSession = Depends(get_db)):
    data = await _svc.investigate_anomaly(db, anomaly_id)
    return ok(data, _rid(r), "intelligence.anomalies.investigate")


@router.post("/anomalies/{anomaly_id}/resolve")
async def resolve_anomaly(anomaly_id: str, r: Request, db: AsyncSession = Depends(get_db)):
    data = await _svc.resolve_anomaly(db, anomaly_id)
    return ok(data, _rid(r), "intelligence.anomalies.resolve")


@router.post("/anomalies/{anomaly_id}/false-positive")
async def mark_false_positive(anomaly_id: str, r: Request, db: AsyncSession = Depends(get_db)):
    data = await _svc.mark_false_positive(db, anomaly_id)
    return ok(data, _rid(r), "intelligence.anomalies.false_positive")


# ── Models ────────────────────────────────────────────────────────────────────

@router.get("/models")
async def list_models(r: Request, db: AsyncSession = Depends(get_db)):
    data = await _svc.list_models(db)
    return ok(data, _rid(r), "intelligence.models.list")


@router.get("/models/{model_id}")
async def get_model(model_id: str, r: Request, db: AsyncSession = Depends(get_db)):
    data = await _svc.get_model(db, model_id)
    if data is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Model not found")
    return ok(data, _rid(r), "intelligence.models.get")


@router.post("/models/{model_id}/activate")
async def activate_model(model_id: str, r: Request, db: AsyncSession = Depends(get_db)):
    data = await _svc.activate_model(db, model_id)
    return ok(data, _rid(r), "intelligence.models.activate")


@router.post("/models/{model_id}/deactivate")
async def deactivate_model(model_id: str, r: Request, db: AsyncSession = Depends(get_db)):
    data = await _svc.deactivate_model(db, model_id)
    return ok(data, _rid(r), "intelligence.models.deactivate")


@router.post("/models/{model_id}/evaluate")
async def evaluate_model(model_id: str, r: Request, db: AsyncSession = Depends(get_db)):
    data = await _svc.evaluate_model(db, model_id)
    return ok(data, _rid(r), "intelligence.models.evaluate")


# ── Prediction Jobs ───────────────────────────────────────────────────────────

@router.get("/prediction-jobs")
async def list_prediction_jobs(
    r: Request, db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
):
    data = await _svc.list_prediction_jobs(db, page=page, page_size=page_size)
    return ok(data, _rid(r), "intelligence.prediction_jobs.list")


@router.post("/prediction-jobs")
async def create_prediction_job(payload: dict, r: Request, db: AsyncSession = Depends(get_db)):
    data = await _svc.create_prediction_job(db, payload, None)
    return ok(data, _rid(r), "intelligence.prediction_jobs.create")


@router.get("/prediction-jobs/{job_id}")
async def get_prediction_job(job_id: str, r: Request, db: AsyncSession = Depends(get_db)):
    data = await _svc.get_prediction_job(db, job_id)
    if data is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Prediction job not found")
    return ok(data, _rid(r), "intelligence.prediction_jobs.get")


@router.post("/prediction-jobs/{job_id}/cancel")
async def cancel_prediction_job(job_id: str, r: Request, db: AsyncSession = Depends(get_db)):
    data = await _svc.cancel_prediction_job(db, job_id)
    return ok(data, _rid(r), "intelligence.prediction_jobs.cancel")


@router.post("/prediction-jobs/{job_id}/retry")
async def retry_prediction_job(job_id: str, r: Request, db: AsyncSession = Depends(get_db)):
    data = await _svc.retry_prediction_job(db, job_id, None)
    return ok(data, _rid(r), "intelligence.prediction_jobs.retry")


# ── Data Quality ──────────────────────────────────────────────────────────────

@router.get("/data-quality/summary")
async def get_data_quality_summary(r: Request, db: AsyncSession = Depends(get_db)):
    data = await _svc.get_data_quality_summary(db)
    return ok(data, _rid(r), "intelligence.data_quality.summary")


@router.get("/data-quality/checks")
async def list_data_quality_checks(r: Request, db: AsyncSession = Depends(get_db)):
    data = await _svc.list_data_quality_checks(db)
    return ok(data, _rid(r), "intelligence.data_quality.checks")


@router.post("/data-quality/checks/{check_key}/run")
async def run_data_quality_check(check_key: str, r: Request, db: AsyncSession = Depends(get_db)):
    data = await _svc.run_data_quality_check(db, check_key, None)
    return ok(data, _rid(r), "intelligence.data_quality.run")


@router.get("/data-quality/checks/{check_key}/failures")
async def get_check_failures(check_key: str, r: Request, db: AsyncSession = Depends(get_db)):
    data = await _svc.get_check_failures(db, check_key)
    return ok(data, _rid(r), "intelligence.data_quality.failures")


# ── AI Usage ──────────────────────────────────────────────────────────────────

@router.get("/ai-usage/summary")
async def get_ai_usage_summary(r: Request, db: AsyncSession = Depends(get_db)):
    data = await _svc.get_ai_usage_summary(db)
    return ok(data, _rid(r), "intelligence.ai_usage.summary")


@router.get("/ai-usage/logs")
async def list_ai_usage_logs(
    r: Request, db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
):
    data = await _svc.list_ai_usage_logs(db, page=page, page_size=page_size)
    return ok(data, _rid(r), "intelligence.ai_usage.logs")


@router.get("/ai-usage/cost-breakdown")
async def get_cost_breakdown(r: Request, db: AsyncSession = Depends(get_db)):
    data = await _svc.get_cost_breakdown(db)
    return ok(data, _rid(r), "intelligence.ai_usage.cost_breakdown")


# ── Audit Logs ────────────────────────────────────────────────────────────────

@router.get("/audit-logs")
async def get_audit_logs(r: Request, db: AsyncSession = Depends(get_db)):
    data = await _svc.get_audit_logs(db)
    return ok(data, _rid(r), "intelligence.audit_logs")
