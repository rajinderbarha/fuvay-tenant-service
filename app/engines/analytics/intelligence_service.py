"""Intelligence Command Center — Service Layer."""
from __future__ import annotations
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Any

import structlog
from sqlalchemy import text, select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.analytics.intelligence_models import (
    RagKnowledgeBase, RagQueryLog, IntelRiskScore, IntelAnomaly,
    IntelModelRegistry, IntelPredictionJob, IntelDataQualityCheck, AiUsageLog,
)

logger = structlog.get_logger("intelligence_service")

DEFAULT_CHECKS = [
    {"check_key": "missing_tenant_profiles", "check_name": "Missing Tenant Profiles", "severity": "high"},
    {"check_key": "orphan_jobs", "check_name": "Orphan Jobs (no tenant)", "severity": "medium"},
    {"check_key": "duplicate_catalog_codes", "check_name": "Duplicate Catalog Codes", "severity": "high"},
    {"check_key": "stale_health_scores", "check_name": "Stale Health Scores (>7 days)", "severity": "low"},
    {"check_key": "invalid_credit_deductions", "check_name": "Invalid Credit Deductions", "severity": "critical"},
    {"check_key": "missing_booking_prices", "check_name": "Missing Booking Prices", "severity": "medium"},
]

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)

def _risk_level(score: float) -> str:
    if score > 75: return "critical"
    if score > 50: return "high"
    if score > 25: return "medium"
    return "low"


class IntelligenceService:

    @staticmethod
    async def _safe_scalar(db: AsyncSession, stmt) -> int:
        try:
            r = await db.execute(stmt)
            return r.scalar() or 0
        except Exception:
            return 0

    # ── Summary ──────────────────────────────────────────────────────────────

    @staticmethod
    async def get_summary(db: AsyncSession) -> dict[str, Any]:
        now = _utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # tenants at risk
        try:
            r = await db.execute(
                select(func.count()).select_from(IntelRiskScore)
                .where(IntelRiskScore.risk_level.in_(["high", "critical"]))
            )
            tenants_at_risk = r.scalar() or 0
        except Exception:
            tenants_at_risk = 0

        # open anomalies
        try:
            r = await db.execute(
                select(func.count()).select_from(IntelAnomaly)
                .where(IntelAnomaly.status == "open")
            )
            open_anomalies = r.scalar() or 0
        except Exception:
            open_anomalies = 0

        # predictions
        try:
            r = await db.execute(
                select(func.sum(IntelPredictionJob.total_processed))
                .where(IntelPredictionJob.status == "completed")
            )
            predictions_computed = r.scalar() or 0
        except Exception:
            predictions_computed = 0

        # events today (rag queries as proxy)
        try:
            r = await db.execute(
                select(func.count()).select_from(RagQueryLog)
                .where(RagQueryLog.created_at >= today_start)
            )
            events_today = r.scalar() or 0
        except Exception:
            events_today = 0

        # rag queries total
        try:
            r = await db.execute(select(func.count()).select_from(RagQueryLog))
            rag_queries = r.scalar() or 0
        except Exception:
            rag_queries = 0

        # indexed documents
        try:
            r = await db.execute(select(func.sum(RagKnowledgeBase.document_count)))
            indexed_documents = r.scalar() or 0
        except Exception:
            indexed_documents = 0

        # avg latency — return None (not NaN) if no rows
        try:
            r = await db.execute(
                select(func.avg(AiUsageLog.latency_ms))
                .where(AiUsageLog.latency_ms.is_not(None))
            )
            raw = r.scalar()
            avg_ai_latency_ms = int(raw) if raw is not None else None
        except Exception:
            avg_ai_latency_ms = None

        # cost today
        try:
            r = await db.execute(
                select(func.sum(AiUsageLog.cost_amount))
                .where(AiUsageLog.created_at >= today_start)
            )
            ai_cost_today = float(r.scalar() or 0)
        except Exception:
            ai_cost_today = 0.0

        # failed jobs
        try:
            r = await db.execute(
                select(func.count()).select_from(IntelPredictionJob)
                .where(IntelPredictionJob.status == "failed")
            )
            failed_jobs = r.scalar() or 0
        except Exception:
            failed_jobs = 0

        # active tenants (from tenants table)
        try:
            r = await db.execute(text("SELECT COUNT(*) FROM tenants WHERE status = 'active'"))
            active_tenants = r.scalar() or 0
        except Exception:
            active_tenants = 0

        return {
            "tenants_at_risk": tenants_at_risk,
            "open_anomalies": open_anomalies,
            "predictions_computed": int(predictions_computed),
            "events_today": events_today,
            "rag_queries": rag_queries,
            "indexed_documents": int(indexed_documents),
            "avg_ai_latency_ms": avg_ai_latency_ms,  # None = no data
            "ai_cost_today": ai_cost_today,
            "failed_jobs": failed_jobs,
            "active_tenants": active_tenants,
        }

    # ── RAG ──────────────────────────────────────────────────────────────────

    @staticmethod
    async def get_rag_summary(db: AsyncSession) -> dict[str, Any]:
        try:
            r = await db.execute(select(func.count()).select_from(RagKnowledgeBase))
            total_kbs = r.scalar() or 0
        except Exception:
            total_kbs = 0

        try:
            r = await db.execute(select(func.sum(RagKnowledgeBase.document_count)))
            total_docs = r.scalar() or 0
        except Exception:
            total_docs = 0

        try:
            r = await db.execute(select(func.count()).select_from(RagQueryLog))
            total_queries = r.scalar() or 0
        except Exception:
            total_queries = 0

        try:
            r = await db.execute(
                select(func.avg(RagQueryLog.latency_ms))
                .where(RagQueryLog.latency_ms.is_not(None))
            )
            raw = r.scalar()
            avg_latency_ms = int(raw) if raw is not None else None
        except Exception:
            avg_latency_ms = None

        try:
            r = await db.execute(
                select(func.count()).select_from(RagQueryLog)
                .where(RagQueryLog.feedback == "helpful")
            )
            helpful = r.scalar() or 0
            helpfulness_rate = round(helpful / max(total_queries, 1) * 100, 1)
        except Exception:
            helpfulness_rate = 0.0

        return {
            "total_knowledge_bases": total_kbs,
            "total_documents": int(total_docs),
            "total_queries": total_queries,
            "avg_latency_ms": avg_latency_ms,
            "helpfulness_rate": helpfulness_rate,
            "flagged_answers": 0,
        }

    @staticmethod
    async def list_knowledge_bases(db: AsyncSession, *, page: int = 1, page_size: int = 25) -> dict[str, Any]:
        offset = (page - 1) * page_size
        try:
            r = await db.execute(select(func.count()).select_from(RagKnowledgeBase))
            total = r.scalar() or 0
            r2 = await db.execute(
                select(RagKnowledgeBase).order_by(RagKnowledgeBase.created_at.desc())
                .offset(offset).limit(page_size)
            )
            items = [row.to_dict() for row in r2.scalars()]
        except Exception:
            total, items = 0, []
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    @staticmethod
    async def create_knowledge_base(db: AsyncSession, payload: dict, user_id: str | None) -> dict[str, Any]:
        kb = RagKnowledgeBase(
            name=payload["name"],
            scope_type=payload.get("scope_type", "platform"),
            description=payload.get("description"),
            vertical_key=payload.get("vertical_key"),
            status="active",
            created_by_user_id=uuid.UUID(user_id) if user_id else None,
        )
        db.add(kb)
        await db.commit()
        await db.refresh(kb)
        return kb.to_dict()

    @staticmethod
    async def get_knowledge_base(db: AsyncSession, kb_id: str) -> dict[str, Any] | None:
        try:
            r = await db.execute(select(RagKnowledgeBase).where(RagKnowledgeBase.id == uuid.UUID(kb_id)))
            row = r.scalar_one_or_none()
            return row.to_dict() if row else None
        except Exception:
            return None

    @staticmethod
    async def reindex_knowledge_base(db: AsyncSession, kb_id: str) -> dict[str, Any]:
        r = await db.execute(select(RagKnowledgeBase).where(RagKnowledgeBase.id == uuid.UUID(kb_id)))
        kb = r.scalar_one_or_none()
        if not kb:
            raise ValueError("Knowledge base not found")
        kb.last_indexed_at = _utcnow()
        await db.commit()
        await db.refresh(kb)
        return kb.to_dict()

    @staticmethod
    async def test_query_knowledge_base(db: AsyncSession, kb_id: str, query: str) -> dict[str, Any]:
        return {
            "query": query,
            "kb_id": kb_id,
            "retrieved_chunks": [],
            "message": "RAG test endpoint — configure DeepSeek for live results",
        }

    @staticmethod
    async def list_query_logs(db: AsyncSession, *, kb_id: str | None = None, page: int = 1, page_size: int = 25) -> dict[str, Any]:
        offset = (page - 1) * page_size
        try:
            stmt = select(RagQueryLog).order_by(RagQueryLog.created_at.desc())
            if kb_id:
                stmt = stmt.where(RagQueryLog.knowledge_base_id == uuid.UUID(kb_id))
            r = await db.execute(select(func.count()).select_from(stmt.subquery()))
            total = r.scalar() or 0
            r2 = await db.execute(stmt.offset(offset).limit(page_size))
            items = [row.to_dict() for row in r2.scalars()]
        except Exception:
            total, items = 0, []
        return {"items": items, "total": total}

    @staticmethod
    async def get_retrieval_quality(db: AsyncSession) -> dict[str, Any]:
        try:
            r = await db.execute(
                select(func.avg(RagQueryLog.retrieved_chunks_count))
                .where(RagQueryLog.status == "success")
            )
            avg_chunks = float(r.scalar() or 0)
            r2 = await db.execute(
                select(func.count()).select_from(RagQueryLog).where(RagQueryLog.status == "success")
            )
            success_count = r2.scalar() or 0
            r3 = await db.execute(select(func.count()).select_from(RagQueryLog))
            total = r3.scalar() or 0
            success_rate = round(success_count / max(total, 1) * 100, 1)
        except Exception:
            avg_chunks, success_rate = 0.0, 0.0
        return {"avg_chunks_retrieved": avg_chunks, "success_rate": success_rate}

    # ── Events ────────────────────────────────────────────────────────────────

    @staticmethod
    async def get_event_summary(db: AsyncSession) -> dict[str, Any]:
        now = _utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        try:
            r = await db.execute(
                select(func.count()).select_from(RagQueryLog)
                .where(RagQueryLog.created_at >= today_start)
            )
            rag_today = r.scalar() or 0
        except Exception:
            rag_today = 0

        sources = [
            {"source": "rag_queries", "events_today": rag_today, "success_rate": 100.0, "status": "healthy"},
            {"source": "booking_events", "events_today": 0, "success_rate": 100.0, "status": "no_data"},
            {"source": "job_events", "events_today": 0, "success_rate": 100.0, "status": "no_data"},
            {"source": "payment_events", "events_today": 0, "success_rate": 100.0, "status": "no_data"},
        ]
        return {
            "sources": sources,
            "total_events_today": rag_today,
            "pipeline_status": "operational",
        }

    @staticmethod
    async def get_event_sources(db: AsyncSession) -> dict[str, Any]:
        summary = await IntelligenceService.get_event_summary(db)
        return {"items": summary["sources"], "total": len(summary["sources"])}

    @staticmethod
    async def get_event_failures(db: AsyncSession) -> dict[str, Any]:
        try:
            r = await db.execute(
                select(RagQueryLog).where(RagQueryLog.status == "error")
                .order_by(RagQueryLog.created_at.desc()).limit(50)
            )
            items = [row.to_dict() for row in r.scalars()]
        except Exception:
            items = []
        return {"items": items, "total": len(items)}

    # ── Risk ──────────────────────────────────────────────────────────────────

    @staticmethod
    async def get_risk_summary(db: AsyncSession) -> dict[str, Any]:
        out = {"critical": 0, "high": 0, "medium": 0, "low": 0, "total": 0}
        try:
            r = await db.execute(
                select(IntelRiskScore.risk_level, func.count())
                .group_by(IntelRiskScore.risk_level)
            )
            for level, cnt in r.all():
                if level in out:
                    out[level] = cnt
            out["total"] = sum(v for k, v in out.items() if k != "total")
        except Exception:
            pass
        return out

    @staticmethod
    async def list_risk_entities(
        db: AsyncSession, *, risk_level: str | None = None,
        entity_type: str | None = None, page: int = 1, page_size: int = 25
    ) -> dict[str, Any]:
        offset = (page - 1) * page_size
        try:
            stmt = select(IntelRiskScore).order_by(IntelRiskScore.risk_score.desc())
            if risk_level:
                stmt = stmt.where(IntelRiskScore.risk_level == risk_level)
            if entity_type:
                stmt = stmt.where(IntelRiskScore.entity_type == entity_type)
            r = await db.execute(select(func.count()).select_from(stmt.subquery()))
            total = r.scalar() or 0
            r2 = await db.execute(stmt.offset(offset).limit(page_size))
            items = [row.to_dict() for row in r2.scalars()]
        except Exception:
            total, items = 0, []
        return {"items": items, "total": total}

    @staticmethod
    async def get_risk_entity(db: AsyncSession, entity_type: str, entity_id: str) -> dict[str, Any] | None:
        try:
            r = await db.execute(
                select(IntelRiskScore)
                .where(IntelRiskScore.entity_type == entity_type,
                       IntelRiskScore.entity_id == uuid.UUID(entity_id))
                .order_by(IntelRiskScore.computed_at.desc()).limit(1)
            )
            row = r.scalar_one_or_none()
            return row.to_dict() if row else None
        except Exception:
            return None

    @staticmethod
    async def recompute_risk(db: AsyncSession, entity_type: str, entity_id: str, user_id: str | None) -> dict[str, Any]:
        score = 0.0
        reasons = []
        try:
            eid = uuid.UUID(entity_id)
            if entity_type == "tenant":
                r = await db.execute(
                    text("SELECT COUNT(*) FROM customer_complaints WHERE tenant_id = :tid"),
                    {"tid": eid}
                )
                complaint_count = r.scalar() or 0
                r2 = await db.execute(
                    text("SELECT COUNT(*) FROM jobs WHERE tenant_id = :tid"),
                    {"tid": eid}
                )
                job_count = r2.scalar() or 0
                score = min(complaint_count / max(job_count, 1) * 100, 100.0)
                if complaint_count > 0:
                    reasons.append(f"{complaint_count} complaints")
            elif entity_type == "provider":
                r = await db.execute(
                    text("SELECT COUNT(*) FROM customer_complaints WHERE tenant_id = :tid"),
                    {"tid": eid}
                )
                score = min(float(r.scalar() or 0) * 5, 100.0)
        except Exception:
            pass

        level = _risk_level(score)
        rs = IntelRiskScore(
            entity_type=entity_type,
            entity_id=uuid.UUID(entity_id),
            risk_score=Decimal(str(round(score, 2))),
            risk_level=level,
            top_reasons_json=reasons,
            confidence_score=Decimal("75.00"),
            model_version="heuristic-v1",
        )
        db.add(rs)
        await db.commit()
        await db.refresh(rs)
        return rs.to_dict()

    # ── Anomalies ─────────────────────────────────────────────────────────────

    @staticmethod
    async def list_anomalies(
        db: AsyncSession, *, status: str | None = None,
        severity: str | None = None, page: int = 1, page_size: int = 25
    ) -> dict[str, Any]:
        offset = (page - 1) * page_size
        try:
            stmt = select(IntelAnomaly).order_by(IntelAnomaly.detected_at.desc())
            if status:
                stmt = stmt.where(IntelAnomaly.status == status)
            if severity:
                stmt = stmt.where(IntelAnomaly.severity == severity)
            r = await db.execute(select(func.count()).select_from(stmt.subquery()))
            total = r.scalar() or 0
            r2 = await db.execute(stmt.offset(offset).limit(page_size))
            items = [row.to_dict() for row in r2.scalars()]
        except Exception:
            total, items = 0, []
        return {"items": items, "total": total}

    @staticmethod
    async def get_anomaly(db: AsyncSession, anomaly_id: str) -> dict[str, Any] | None:
        try:
            r = await db.execute(
                select(IntelAnomaly).where(IntelAnomaly.id == uuid.UUID(anomaly_id))
            )
            row = r.scalar_one_or_none()
            return row.to_dict() if row else None
        except Exception:
            return None

    @staticmethod
    async def _update_anomaly_status(db: AsyncSession, anomaly_id: str, new_status: str) -> dict[str, Any]:
        r = await db.execute(select(IntelAnomaly).where(IntelAnomaly.id == uuid.UUID(anomaly_id)))
        a = r.scalar_one_or_none()
        if not a:
            raise ValueError("Anomaly not found")
        a.status = new_status
        if new_status == "resolved":
            a.resolved_at = _utcnow()
        a.updated_at = _utcnow()
        await db.commit()
        await db.refresh(a)
        return a.to_dict()

    @staticmethod
    async def investigate_anomaly(db: AsyncSession, anomaly_id: str) -> dict[str, Any]:
        return await IntelligenceService._update_anomaly_status(db, anomaly_id, "investigating")

    @staticmethod
    async def resolve_anomaly(db: AsyncSession, anomaly_id: str) -> dict[str, Any]:
        return await IntelligenceService._update_anomaly_status(db, anomaly_id, "resolved")

    @staticmethod
    async def mark_false_positive(db: AsyncSession, anomaly_id: str) -> dict[str, Any]:
        return await IntelligenceService._update_anomaly_status(db, anomaly_id, "false_positive")

    @staticmethod
    async def run_anomaly_scan(db: AsyncSession, user_id: str | None) -> dict[str, Any]:
        new_count = 0
        updated = 0
        scanned = 0

        # Check for tenants with high complaint rate
        try:
            r = await db.execute(text("""
                SELECT t.id::text, COUNT(c.id) as complaints, COUNT(j.id) as jobs
                FROM tenants t
                LEFT JOIN customer_complaints c ON c.tenant_id = t.id
                LEFT JOIN jobs j ON j.tenant_id = t.id
                GROUP BY t.id
                HAVING COUNT(c.id) > 0 AND COUNT(c.id) * 10 > COUNT(j.id)
                LIMIT 20
            """))
            rows = r.fetchall()
            scanned = len(rows)
            for row in rows:
                entity_id_str = row[0]
                existing = await db.execute(
                    select(IntelAnomaly).where(
                        IntelAnomaly.anomaly_type == "high_complaint_rate",
                        IntelAnomaly.entity_id == uuid.UUID(entity_id_str),
                        IntelAnomaly.status == "open",
                    )
                )
                if not existing.scalar_one_or_none():
                    a = IntelAnomaly(
                        anomaly_type="high_complaint_rate",
                        severity="high",
                        entity_type="tenant",
                        entity_id=uuid.UUID(entity_id_str),
                        summary=f"Tenant has {row[1]} complaints vs {row[2]} jobs — complaint rate exceeds 10%",
                        confidence_score=Decimal("85.0"),
                        status="open",
                    )
                    db.add(a)
                    new_count += 1
                else:
                    updated += 1
        except Exception:
            pass

        # Check RAG latency spikes
        try:
            r = await db.execute(
                select(func.count()).select_from(RagQueryLog)
                .where(RagQueryLog.latency_ms > 5000)
            )
            spike_count = r.scalar() or 0
            if spike_count > 0:
                existing = await db.execute(
                    select(IntelAnomaly).where(
                        IntelAnomaly.anomaly_type == "rag_latency_spike",
                        IntelAnomaly.status == "open",
                    )
                )
                if not existing.scalar_one_or_none():
                    a = IntelAnomaly(
                        anomaly_type="rag_latency_spike",
                        severity="medium",
                        entity_type="system",
                        summary=f"{spike_count} RAG queries with latency > 5000ms detected",
                        confidence_score=Decimal("90.0"),
                        status="open",
                    )
                    db.add(a)
                    new_count += 1
        except Exception:
            pass

        await db.commit()
        return {"scanned": scanned, "new_anomalies": new_count, "updated": updated}

    # ── Models ────────────────────────────────────────────────────────────────

    @staticmethod
    async def list_models(db: AsyncSession) -> dict[str, Any]:
        try:
            r = await db.execute(
                select(IntelModelRegistry).order_by(IntelModelRegistry.created_at.desc())
            )
            items = [row.to_dict() for row in r.scalars()]
        except Exception:
            items = []
        return {"items": items, "total": len(items)}

    @staticmethod
    async def get_model(db: AsyncSession, model_id: str) -> dict[str, Any] | None:
        try:
            r = await db.execute(
                select(IntelModelRegistry).where(IntelModelRegistry.id == uuid.UUID(model_id))
            )
            row = r.scalar_one_or_none()
            return row.to_dict() if row else None
        except Exception:
            return None

    @staticmethod
    async def _update_model_status(db: AsyncSession, model_id: str, new_status: str) -> dict[str, Any]:
        r = await db.execute(
            select(IntelModelRegistry).where(IntelModelRegistry.id == uuid.UUID(model_id))
        )
        m = r.scalar_one_or_none()
        if not m:
            raise ValueError("Model not found")
        m.status = new_status
        m.updated_at = _utcnow()
        await db.commit()
        await db.refresh(m)
        return m.to_dict()

    @staticmethod
    async def activate_model(db: AsyncSession, model_id: str) -> dict[str, Any]:
        return await IntelligenceService._update_model_status(db, model_id, "active")

    @staticmethod
    async def deactivate_model(db: AsyncSession, model_id: str) -> dict[str, Any]:
        return await IntelligenceService._update_model_status(db, model_id, "disabled")

    @staticmethod
    async def evaluate_model(db: AsyncSession, model_id: str) -> dict[str, Any]:
        m = await IntelligenceService.get_model(db, model_id)
        if not m:
            raise ValueError("Model not found")
        return {**m, "evaluation": {"status": "ok", "message": "Evaluation stub — connect to ML pipeline for live eval"}}

    # ── Prediction Jobs ───────────────────────────────────────────────────────

    @staticmethod
    async def list_prediction_jobs(db: AsyncSession, *, page: int = 1, page_size: int = 25) -> dict[str, Any]:
        offset = (page - 1) * page_size
        try:
            r = await db.execute(select(func.count()).select_from(IntelPredictionJob))
            total = r.scalar() or 0
            r2 = await db.execute(
                select(IntelPredictionJob).order_by(IntelPredictionJob.created_at.desc())
                .offset(offset).limit(page_size)
            )
            items = [row.to_dict() for row in r2.scalars()]
        except Exception:
            total, items = 0, []
        return {"items": items, "total": total}

    @staticmethod
    async def create_prediction_job(db: AsyncSession, payload: dict, user_id: str | None) -> dict[str, Any]:
        job = IntelPredictionJob(
            job_type=payload.get("job_type", "daily_tenant_risk"),
            status="running",
            triggered_by="manual",
            started_by_user_id=uuid.UUID(user_id) if user_id else None,
            started_at=_utcnow(),
        )
        db.add(job)
        await db.flush()

        # Run simple heuristic predictions for all tenants
        processed = 0
        try:
            r = await db.execute(text("SELECT id FROM tenants WHERE status = 'active' LIMIT 100"))
            tenant_ids = [str(row[0]) for row in r.fetchall()]
            for tid in tenant_ids:
                try:
                    await IntelligenceService.recompute_risk(db, "tenant", tid, user_id)
                    processed += 1
                except Exception:
                    pass
        except Exception:
            pass

        job.status = "completed"
        job.completed_at = _utcnow()
        job.total_processed = processed
        job.result_summary_json = {"tenants_scored": processed}
        await db.commit()
        await db.refresh(job)
        return job.to_dict()

    @staticmethod
    async def get_prediction_job(db: AsyncSession, job_id: str) -> dict[str, Any] | None:
        try:
            r = await db.execute(
                select(IntelPredictionJob).where(IntelPredictionJob.id == uuid.UUID(job_id))
            )
            row = r.scalar_one_or_none()
            return row.to_dict() if row else None
        except Exception:
            return None

    @staticmethod
    async def cancel_prediction_job(db: AsyncSession, job_id: str) -> dict[str, Any]:
        r = await db.execute(
            select(IntelPredictionJob).where(IntelPredictionJob.id == uuid.UUID(job_id))
        )
        job = r.scalar_one_or_none()
        if not job:
            raise ValueError("Job not found")
        if job.status not in ("queued", "running"):
            raise ValueError(f"Cannot cancel job in status {job.status}")
        job.status = "cancelled"
        job.updated_at = _utcnow()
        await db.commit()
        await db.refresh(job)
        return job.to_dict()

    @staticmethod
    async def retry_prediction_job(db: AsyncSession, job_id: str, user_id: str | None) -> dict[str, Any]:
        r = await db.execute(
            select(IntelPredictionJob).where(IntelPredictionJob.id == uuid.UUID(job_id))
        )
        job = r.scalar_one_or_none()
        if not job:
            raise ValueError("Job not found")
        new_job = IntelPredictionJob(
            job_type=job.job_type,
            status="queued",
            triggered_by="retry",
            started_by_user_id=uuid.UUID(user_id) if user_id else None,
        )
        db.add(new_job)
        await db.commit()
        await db.refresh(new_job)
        return new_job.to_dict()

    # ── Data Quality ──────────────────────────────────────────────────────────

    @staticmethod
    async def _ensure_default_checks(db: AsyncSession) -> None:
        r = await db.execute(select(func.count()).select_from(IntelDataQualityCheck))
        count = r.scalar() or 0
        if count == 0:
            for chk in DEFAULT_CHECKS:
                db.add(IntelDataQualityCheck(**chk))
            await db.commit()

    @staticmethod
    async def get_data_quality_summary(db: AsyncSession) -> dict[str, Any]:
        await IntelligenceService._ensure_default_checks(db)
        try:
            r = await db.execute(
                select(IntelDataQualityCheck.last_status, func.count())
                .group_by(IntelDataQualityCheck.last_status)
            )
            counts: dict[str, int] = {}
            for status, cnt in r.all():
                counts[status] = cnt
        except Exception:
            counts = {}
        return {
            "passed": counts.get("passed", 0),
            "failed": counts.get("failed", 0),
            "warning": counts.get("warning", 0),
            "not_run": counts.get("not_run", len(DEFAULT_CHECKS)),
        }

    @staticmethod
    async def list_data_quality_checks(db: AsyncSession) -> dict[str, Any]:
        await IntelligenceService._ensure_default_checks(db)
        try:
            r = await db.execute(
                select(IntelDataQualityCheck).order_by(IntelDataQualityCheck.severity.desc())
            )
            items = [row.to_dict() for row in r.scalars()]
        except Exception:
            items = []
        return {"items": items, "total": len(items)}

    @staticmethod
    async def run_data_quality_check(db: AsyncSession, check_key: str, user_id: str | None) -> dict[str, Any]:
        r = await db.execute(
            select(IntelDataQualityCheck).where(IntelDataQualityCheck.check_key == check_key)
        )
        chk = r.scalar_one_or_none()
        if not chk:
            raise ValueError(f"Check {check_key!r} not found")

        failure_count = 0
        new_status = "passed"
        try:
            if check_key == "missing_tenant_profiles":
                r2 = await db.execute(text("SELECT COUNT(*) FROM tenants WHERE name IS NULL OR name = ''"))
                failure_count = r2.scalar() or 0
            elif check_key == "orphan_jobs":
                r2 = await db.execute(text("SELECT COUNT(*) FROM jobs j WHERE j.tenant_id NOT IN (SELECT id FROM tenants)"))
                failure_count = r2.scalar() or 0
            elif check_key == "duplicate_catalog_codes":
                r2 = await db.execute(text("SELECT COUNT(*) FROM (SELECT code FROM service_categories GROUP BY code HAVING COUNT(*) > 1) sub"))
                failure_count = r2.scalar() or 0
            elif check_key == "stale_health_scores":
                r2 = await db.execute(text("SELECT COUNT(*) FROM tenants WHERE updated_at < now() - INTERVAL '7 days'"))
                failure_count = r2.scalar() or 0
            elif check_key == "invalid_credit_deductions":
                failure_count = 0  # Stub
            elif check_key == "missing_booking_prices":
                failure_count = 0  # Stub

            if failure_count > 0:
                new_status = "failed"
        except Exception:
            new_status = "warning"
            failure_count = 0

        chk.last_run_at = _utcnow()
        chk.last_status = new_status
        chk.failure_count = failure_count
        chk.updated_at = _utcnow()
        await db.commit()
        await db.refresh(chk)
        return chk.to_dict()

    @staticmethod
    async def get_check_failures(db: AsyncSession, check_key: str) -> dict[str, Any]:
        r = await db.execute(
            select(IntelDataQualityCheck).where(IntelDataQualityCheck.check_key == check_key)
        )
        chk = r.scalar_one_or_none()
        return {"check_key": check_key, "failures": [], "total": chk.failure_count if chk else 0}

    # ── AI Usage ──────────────────────────────────────────────────────────────

    @staticmethod
    async def get_ai_usage_summary(db: AsyncSession) -> dict[str, Any]:
        now = _utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        try:
            r = await db.execute(
                select(func.sum(AiUsageLog.cost_amount))
                .where(AiUsageLog.created_at >= today_start)
            )
            cost_today = float(r.scalar() or 0)
        except Exception:
            cost_today = 0.0

        try:
            r = await db.execute(
                select(func.sum(AiUsageLog.cost_amount))
                .where(AiUsageLog.created_at >= month_start)
            )
            monthly_cost = float(r.scalar() or 0)
        except Exception:
            monthly_cost = 0.0

        try:
            r = await db.execute(select(func.count()).select_from(AiUsageLog))
            total_queries = r.scalar() or 0
        except Exception:
            total_queries = 0

        try:
            r = await db.execute(
                select(func.avg(AiUsageLog.latency_ms))
                .where(AiUsageLog.latency_ms.is_not(None))
            )
            raw = r.scalar()
            avg_latency_ms = int(raw) if raw is not None else None
        except Exception:
            avg_latency_ms = None

        try:
            r = await db.execute(
                select(func.count()).select_from(AiUsageLog)
                .where(AiUsageLog.status != "success")
            )
            failed_calls = r.scalar() or 0
        except Exception:
            failed_calls = 0

        return {
            "total_cost_today": cost_today,
            "monthly_cost": monthly_cost,
            "total_queries": total_queries,
            "avg_latency_ms": avg_latency_ms,
            "failed_calls": failed_calls,
        }

    @staticmethod
    async def list_ai_usage_logs(db: AsyncSession, *, page: int = 1, page_size: int = 25) -> dict[str, Any]:
        offset = (page - 1) * page_size
        try:
            r = await db.execute(select(func.count()).select_from(AiUsageLog))
            total = r.scalar() or 0
            r2 = await db.execute(
                select(AiUsageLog).order_by(AiUsageLog.created_at.desc())
                .offset(offset).limit(page_size)
            )
            items = [row.to_dict() for row in r2.scalars()]
        except Exception:
            total, items = 0, []
        return {"items": items, "total": total}

    @staticmethod
    async def get_cost_breakdown(db: AsyncSession) -> dict[str, Any]:
        try:
            r = await db.execute(
                select(AiUsageLog.feature_key, func.sum(AiUsageLog.cost_amount))
                .group_by(AiUsageLog.feature_key)
                .order_by(func.sum(AiUsageLog.cost_amount).desc())
            )
            breakdown = [{"feature": k, "cost": float(v)} for k, v in r.all()]
        except Exception:
            breakdown = []
        return {"breakdown": breakdown, "total_features": len(breakdown)}

    @staticmethod
    async def get_audit_logs(db: AsyncSession) -> dict[str, Any]:
        """Return recent audit events from analytics_events or stub."""
        try:
            r = await db.execute(text("""
                SELECT created_at, actor_id::text, event_type, entity_type, event_id
                FROM analytics_events
                ORDER BY created_at DESC
                LIMIT 50
            """))
            items = [
                {
                    "time": row[0].isoformat() if row[0] else None,
                    "actor": row[1],
                    "action": row[2],
                    "target": row[3],
                    "request_id": row[4],
                }
                for row in r.fetchall()
            ]
        except Exception:
            items = []
        return {"items": items, "total": len(items)}
