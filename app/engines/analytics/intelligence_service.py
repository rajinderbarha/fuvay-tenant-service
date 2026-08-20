"""Intelligence Command Center — Service Layer."""
from __future__ import annotations
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Any

import structlog
from sqlalchemy import String, and_, cast, text, select, func, update, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.analytics.models import AnalyticsEvent
from app.engines.analytics.intelligence_models import (
    RagKnowledgeBase, RagQueryLog, IntelRiskScore, IntelAnomaly,
    IntelModelRegistry, IntelPredictionJob, IntelDataQualityCheck, AiUsageLog,
)
from app.engines.security.models import PlatformAuditLog
from app.engines.tenant_engine.models import Tenant

logger = structlog.get_logger("intelligence_service")

DEFAULT_CHECKS = [
    {
        "check_key": "missing_tenant_profiles",
        "check_name": "Incomplete provider business profiles",
        "description": "Active Home Services providers missing a business name, email, or phone.",
        "severity": "high",
    },
    {
        "check_key": "orphan_jobs",
        "check_name": "Jobs without a provider",
        "description": "Jobs whose provider workspace no longer exists.",
        "severity": "critical",
    },
    {
        "check_key": "duplicate_catalog_codes",
        "check_name": "Duplicate service-group codes",
        "description": "Service-group codes that violate the globally unique catalog contract.",
        "severity": "high",
    },
    {
        "check_key": "invalid_credit_deductions",
        "check_name": "Invalid completion-credit ledger rows",
        "description": "Ledger arithmetic, sign, or idempotency violations in provider completion deductions.",
        "severity": "critical",
    },
    {
        "check_key": "missing_booking_prices",
        "check_name": "Confirmed bookings without a price",
        "description": "Non-draft bookings missing every authoritative price field.",
        "severity": "high",
    },
    {
        "check_key": "orphan_bookings",
        "check_name": "Bookings without a provider",
        "description": "Bookings whose provider workspace no longer exists.",
        "severity": "critical",
    },
]

RETIRED_CHECK_KEYS = {"stale_health_scores"}

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

        # Current provider scores.  Risk rows are now one-per-entity, so this
        # is not inflated by historical runs.
        try:
            r = await db.execute(
                select(func.count()).select_from(IntelRiskScore)
            )
            predictions_computed = r.scalar() or 0
        except Exception:
            predictions_computed = 0

        # Real cross-engine domain events, not RAG queries as a proxy.
        try:
            r = await db.execute(
                select(func.count()).select_from(AnalyticsEvent)
                .where(AnalyticsEvent.occurred_at >= today_start)
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

        # This workspace currently governs Home Services.  Do not mix future
        # verticals into its risk denominator.
        try:
            r = await db.execute(text("""
                SELECT COUNT(*) FROM tenants
                WHERE status = 'active' AND vertical = 'home_services'
            """))
            active_tenants = r.scalar() or 0
        except Exception:
            active_tenants = 0

        try:
            r = await db.execute(
                select(func.max(AnalyticsEvent.occurred_at))
            )
            last_event_at = r.scalar()
        except Exception:
            last_event_at = None

        try:
            r = await db.execute(
                select(IntelPredictionJob)
                .order_by(IntelPredictionJob.created_at.desc()).limit(1)
            )
            last_prediction = r.scalar_one_or_none()
        except Exception:
            last_prediction = None

        try:
            r = await db.execute(
                select(func.count()).select_from(IntelDataQualityCheck)
                .where(IntelDataQualityCheck.last_status.in_(["failed", "warning"]))
            )
            dq_issues = r.scalar() or 0
        except Exception:
            dq_issues = 0

        event_is_fresh = bool(last_event_at and last_event_at >= now - timedelta(hours=24))
        engine_health = [
            {
                "key": "events", "label": "Event pipeline",
                "status": "healthy" if event_is_fresh else "idle",
                "detail": "Events received in the last 24 hours" if event_is_fresh else "No events received in the last 24 hours",
            },
            {
                "key": "risk", "label": "Provider risk scoring",
                "status": (
                    "healthy" if last_prediction and last_prediction.status == "completed"
                    else "degraded" if last_prediction and last_prediction.status == "failed"
                    else "idle"
                ),
                "detail": (
                    f"Last run processed {last_prediction.total_processed or 0:,} providers"
                    if last_prediction else "No risk-scoring run has completed"
                ),
            },
            {
                "key": "quality", "label": "Data quality",
                "status": "degraded" if dq_issues else "healthy",
                "detail": f"{dq_issues} checks need attention" if dq_issues else "No failed checks",
            },
            {
                "key": "rag", "label": "Knowledge retrieval",
                "status": "healthy" if indexed_documents else "idle",
                "detail": f"{int(indexed_documents):,} indexed documents" if indexed_documents else "No indexed documents",
            },
        ]

        action_items = []
        if tenants_at_risk:
            action_items.append({"type": "risk", "count": tenants_at_risk, "label": "Providers need risk review", "tab": "risk"})
        if open_anomalies:
            action_items.append({"type": "anomaly", "count": open_anomalies, "label": "Open anomalies need investigation", "tab": "anomalies"})
        if dq_issues:
            action_items.append({"type": "quality", "count": dq_issues, "label": "Data-quality checks need attention", "tab": "data-quality"})
        if failed_jobs:
            action_items.append({"type": "prediction", "count": failed_jobs, "label": "Failed automation runs", "tab": "prediction-jobs"})

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
            "engine_health": engine_health,
            "action_items": action_items,
            "generated_at": now.isoformat(),
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
            r = await db.execute(text("""
                SELECT
                    COUNT(*) FILTER (WHERE occurred_at >= :today_start) AS events_today,
                    COUNT(*) FILTER (
                        WHERE occurred_at >= :today_start
                          AND event_type ~* '(failed|failure|error|dead_letter)'
                    ) AS failure_signals,
                    MAX(occurred_at) AS last_event_at,
                    COUNT(DISTINCT engine_id) FILTER (WHERE occurred_at >= :today_start) AS active_sources
                FROM analytics_events
            """), {"today_start": today_start})
            row = r.one()
            events_today = int(row.events_today or 0)
            failure_signals = int(row.failure_signals or 0)
            last_event_at = row.last_event_at
            active_sources = int(row.active_sources or 0)
        except Exception:
            events_today, failure_signals, last_event_at, active_sources = 0, 0, None, 0

        status = "healthy" if last_event_at and last_event_at >= now - timedelta(hours=24) else "idle"
        if failure_signals:
            status = "degraded"
        return {
            "total_events_today": events_today,
            "failure_signals_today": failure_signals,
            "active_sources_today": active_sources,
            "last_event_at": last_event_at.isoformat() if last_event_at else None,
            "pipeline_status": status,
        }

    @staticmethod
    async def get_event_sources(db: AsyncSession) -> dict[str, Any]:
        now = _utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        try:
            r = await db.execute(text("""
                SELECT
                    engine_id AS source,
                    COUNT(*) FILTER (WHERE occurred_at >= :today_start) AS events_today,
                    COUNT(*) FILTER (
                        WHERE occurred_at >= :today_start
                          AND event_type ~* '(failed|failure|error|dead_letter)'
                    ) AS failure_signals,
                    MAX(occurred_at) AS last_event_at,
                    COUNT(*) AS total_events
                FROM analytics_events
                GROUP BY engine_id
                ORDER BY events_today DESC, engine_id ASC
            """), {"today_start": today_start})
            items = []
            for row in r:
                if row.last_event_at and row.last_event_at >= now - timedelta(hours=24):
                    status = "degraded" if row.failure_signals else "healthy"
                else:
                    status = "idle"
                items.append({
                    "source": row.source,
                    "events_today": int(row.events_today or 0),
                    "failure_signals": int(row.failure_signals or 0),
                    "total_events": int(row.total_events or 0),
                    "last_event_at": row.last_event_at.isoformat() if row.last_event_at else None,
                    "status": status,
                })
        except Exception:
            items = []
        return {"items": items, "total": len(items)}

    @staticmethod
    async def get_event_failures(
        db: AsyncSession, *, engine_id: str | None = None, q: str | None = None,
        page: int = 1, page_size: int = 25,
    ) -> dict[str, Any]:
        offset = (page - 1) * page_size
        try:
            where = ["event_type ~* '(failed|failure|error|dead_letter)'"]
            params: dict[str, Any] = {"limit": page_size, "offset": offset}
            if engine_id:
                where.append("engine_id = :engine_id")
                params["engine_id"] = engine_id
            if q:
                where.append("(event_type ILIKE :q OR entity_type ILIKE :q OR entity_id ILIKE :q OR event_id ILIKE :q)")
                params["q"] = f"%{q}%"
            predicate = " AND ".join(where)
            total = (await db.execute(text(f"SELECT COUNT(*) FROM analytics_events WHERE {predicate}"), params)).scalar() or 0
            r = await db.execute(text(f"""
                SELECT event_id, event_type, engine_id, entity_type, entity_id,
                       tenant_id::text, occurred_at
                FROM analytics_events
                WHERE {predicate}
                ORDER BY occurred_at DESC, id DESC
                LIMIT :limit OFFSET :offset
            """), params)
            items = [{
                "event_id": row.event_id,
                "event_type": row.event_type,
                "engine_id": row.engine_id,
                "entity_type": row.entity_type,
                "entity_id": row.entity_id,
                "tenant_id": row.tenant_id,
                "occurred_at": row.occurred_at.isoformat() if row.occurred_at else None,
            } for row in r]
        except Exception:
            items, total = [], 0
        return {"items": items, "total": total, "page": page, "page_size": page_size}

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
        entity_type: str | None = None, q: str | None = None,
        page: int = 1, page_size: int = 25
    ) -> dict[str, Any]:
        offset = (page - 1) * page_size
        try:
            stmt = (
                select(IntelRiskScore, Tenant.tenant_name, Tenant.business_name, Tenant.tenant_code)
                .outerjoin(
                    Tenant,
                    and_(
                        IntelRiskScore.entity_type.in_(["tenant", "provider"]),
                        IntelRiskScore.entity_id == Tenant.id,
                    ),
                )
                .order_by(IntelRiskScore.risk_score.desc(), IntelRiskScore.computed_at.desc())
            )
            if risk_level:
                stmt = stmt.where(IntelRiskScore.risk_level == risk_level)
            if entity_type:
                stmt = stmt.where(IntelRiskScore.entity_type == entity_type)
            if q:
                pattern = f"%{q.strip()}%"
                stmt = stmt.where(or_(
                    Tenant.tenant_name.ilike(pattern),
                    Tenant.business_name.ilike(pattern),
                    Tenant.tenant_code.ilike(pattern),
                    cast(IntelRiskScore.entity_id, String).ilike(pattern),
                ))
            r = await db.execute(select(func.count()).select_from(stmt.order_by(None).subquery()))
            total = r.scalar() or 0
            r2 = await db.execute(stmt.offset(offset).limit(page_size))
            items = []
            for score, tenant_name, business_name, tenant_code in r2:
                item = score.to_dict()
                item["entity_label"] = business_name or tenant_name or str(score.entity_id)
                item["entity_code"] = tenant_code
                items.append(item)
        except Exception:
            total, items = 0, []
        return {"items": items, "total": total, "page": page, "page_size": page_size}

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
        if entity_type not in {"tenant", "provider"}:
            raise ValueError("Only Home Services providers can be risk-scored")
        score = 0.0
        reasons: list[str] = []
        contributions: dict[str, float] = {}
        try:
            eid = uuid.UUID(entity_id)
            r = await db.execute(text("""
                SELECT
                    (SELECT COUNT(*) FROM jobs WHERE tenant_id = :tid
                        AND created_at >= now() - interval '90 days') AS jobs_90d,
                    (SELECT COUNT(*) FROM jobs WHERE tenant_id = :tid
                        AND created_at >= now() - interval '90 days'
                        AND (sla_breach = true OR sla_breached = true)) AS sla_breaches_90d,
                    (SELECT COUNT(*) FROM customer_complaints WHERE tenant_id = :tid
                        AND created_at >= now() - interval '90 days') AS complaints_90d,
                    (SELECT COUNT(*) FROM customer_complaints WHERE tenant_id = :tid
                        AND status NOT IN ('resolved', 'closed', 'withdrawn')) AS open_complaints,
                    (SELECT COALESCE(credit_balance, 0) FROM tenant_billing
                        WHERE tenant_id = :tid ORDER BY updated_at DESC LIMIT 1) AS credit_balance
            """), {"tid": eid})
            row = r.one()
            job_count = int(row.jobs_90d or 0)
            complaint_count = int(row.complaints_90d or 0)
            open_complaints = int(row.open_complaints or 0)
            sla_breaches = int(row.sla_breaches_90d or 0)
            credit_balance = float(row.credit_balance or 0)

            complaint_component = min((complaint_count / max(job_count, 1)) * 250, 45.0)
            unresolved_component = min(open_complaints * 5.0, 20.0)
            sla_component = min((sla_breaches / max(job_count, 1)) * 100, 25.0)
            credit_component = 10.0 if credit_balance <= 0 else 5.0 if credit_balance < 1000 else 0.0
            contributions = {
                "complaint_rate": round(complaint_component, 2),
                "unresolved_complaints": round(unresolved_component, 2),
                "sla_breaches": round(sla_component, 2),
                "usage_credit_readiness": round(credit_component, 2),
            }
            score = min(sum(contributions.values()), 100.0)
            if complaint_count:
                reasons.append(f"{complaint_count} complaints in 90 days")
            if open_complaints:
                reasons.append(f"{open_complaints} unresolved complaints")
            if sla_breaches:
                reasons.append(f"{sla_breaches} SLA breaches in 90 days")
            if credit_component:
                reasons.append("Usage-credit balance needs attention")
        except Exception as exc:
            logger.exception("intelligence.risk.recompute_failed", entity_id=entity_id, error=str(exc))
            raise

        level = _risk_level(score)
        r = await db.execute(select(IntelRiskScore).where(
            IntelRiskScore.entity_type == entity_type,
            IntelRiskScore.entity_id == uuid.UUID(entity_id),
        ))
        rs = r.scalar_one_or_none()
        if rs is None:
            rs = IntelRiskScore(entity_type=entity_type, entity_id=uuid.UUID(entity_id))
            db.add(rs)
        rs.risk_score = Decimal(str(round(score, 2)))
        rs.risk_level = level
        rs.top_reasons_json = reasons[:4]
        rs.feature_contributions_json = contributions
        rs.confidence_score = Decimal("90.00" if contributions else "50.00")
        rs.model_version = "home-services-risk-v2"
        rs.computed_at = _utcnow()
        await db.commit()
        await db.refresh(rs)
        return rs.to_dict()

    # ── Anomalies ─────────────────────────────────────────────────────────────

    @staticmethod
    async def list_anomalies(
        db: AsyncSession, *, status: str | None = None,
        severity: str | None = None, entity_type: str | None = None,
        q: str | None = None, page: int = 1, page_size: int = 25
    ) -> dict[str, Any]:
        offset = (page - 1) * page_size
        try:
            stmt = select(IntelAnomaly).order_by(IntelAnomaly.detected_at.desc())
            if status:
                stmt = stmt.where(IntelAnomaly.status == status)
            if severity:
                stmt = stmt.where(IntelAnomaly.severity == severity)
            if entity_type:
                stmt = stmt.where(IntelAnomaly.entity_type == entity_type)
            if q:
                pattern = f"%{q.strip()}%"
                stmt = stmt.where(or_(
                    IntelAnomaly.summary.ilike(pattern),
                    IntelAnomaly.anomaly_type.ilike(pattern),
                    cast(IntelAnomaly.entity_id, String).ilike(pattern),
                ))
            r = await db.execute(select(func.count()).select_from(stmt.order_by(None).subquery()))
            total = r.scalar() or 0
            r2 = await db.execute(stmt.offset(offset).limit(page_size))
            items = [row.to_dict() for row in r2.scalars()]
        except Exception:
            total, items = 0, []
        return {"items": items, "total": total, "page": page, "page_size": page_size}

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
                WITH complaint_stats AS (
                    SELECT tenant_id, COUNT(*) AS complaints
                    FROM customer_complaints
                    WHERE created_at >= now() - interval '90 days' AND tenant_id IS NOT NULL
                    GROUP BY tenant_id
                ), job_stats AS (
                    SELECT tenant_id, COUNT(*) AS jobs
                    FROM jobs
                    WHERE created_at >= now() - interval '90 days'
                    GROUP BY tenant_id
                )
                SELECT t.id::text, c.complaints, COALESCE(j.jobs, 0) AS jobs
                FROM tenants t
                JOIN complaint_stats c ON c.tenant_id = t.id
                LEFT JOIN job_stats j ON j.tenant_id = t.id
                WHERE t.status = 'active' AND t.vertical = 'home_services'
                  AND c.complaints * 10 > GREATEST(COALESCE(j.jobs, 0), 1)
                ORDER BY (c.complaints::numeric / GREATEST(COALESCE(j.jobs, 0), 1)) DESC
                LIMIT 1000
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
        except Exception as exc:
            logger.exception("intelligence.anomaly.provider_scan_failed", error=str(exc))
            raise

        # Completion-credit arithmetic is a financial invariant.  Surface one
        # system anomaly without duplicating it on every scan.
        try:
            bad_credits = int((await db.execute(text("""
                SELECT COUNT(*) FROM usage_credit_ledger
                WHERE balance_after <> balance_before + credit_delta
                   OR (event_type = 'job_completion_deduction' AND credit_delta >= 0)
            """))).scalar() or 0)
            if bad_credits:
                existing = await db.execute(select(IntelAnomaly).where(
                    IntelAnomaly.anomaly_type == "credit_ledger_integrity",
                    IntelAnomaly.status.in_(["open", "investigating"]),
                ))
                if not existing.scalar_one_or_none():
                    db.add(IntelAnomaly(
                        anomaly_type="credit_ledger_integrity",
                        severity="critical",
                        entity_type="system",
                        summary=f"{bad_credits} usage-credit ledger rows violate completion-deduction invariants",
                        confidence_score=Decimal("100.0"),
                        status="open",
                    ))
                    new_count += 1
                else:
                    updated += 1
        except Exception as exc:
            logger.exception("intelligence.anomaly.credit_scan_failed", error=str(exc))
            raise

        # Check RAG latency spikes
        try:
            r = await db.execute(
                select(func.count()).select_from(RagQueryLog)
                .where(
                    RagQueryLog.latency_ms > 5000,
                    RagQueryLog.created_at >= _utcnow() - timedelta(hours=24),
                )
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
        except Exception as exc:
            logger.warning("intelligence.anomaly.rag_scan_failed", error=str(exc))

        await db.commit()
        return {"scanned": scanned, "new_anomalies": new_count, "updated": updated}

    # ── Models ────────────────────────────────────────────────────────────────

    @staticmethod
    async def list_models(
        db: AsyncSession, *, q: str | None = None, status: str | None = None,
        model_type: str | None = None, page: int = 1, page_size: int = 25,
    ) -> dict[str, Any]:
        offset = (page - 1) * page_size
        try:
            stmt = select(IntelModelRegistry)
            if q:
                pattern = f"%{q.strip()}%"
                stmt = stmt.where(or_(IntelModelRegistry.name.ilike(pattern), IntelModelRegistry.version.ilike(pattern)))
            if status:
                stmt = stmt.where(IntelModelRegistry.status == status)
            if model_type:
                stmt = stmt.where(IntelModelRegistry.model_type == model_type)
            total = int((await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar() or 0)
            r = await db.execute(
                stmt.order_by(IntelModelRegistry.created_at.desc()).offset(offset).limit(page_size)
            )
            items = [row.to_dict() for row in r.scalars()]
        except Exception:
            items, total = [], 0
        return {"items": items, "total": total, "page": page, "page_size": page_size}

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
        r = await db.execute(text("""
            SELECT COUNT(*) AS calls,
                   COUNT(*) FILTER (WHERE status = 'success') AS successful_calls,
                   AVG(latency_ms) FILTER (WHERE latency_ms IS NOT NULL) AS avg_latency_ms,
                   COALESCE(SUM(cost_amount), 0) AS cost,
                   MAX(created_at) AS last_used_at
            FROM ai_usage_logs
            WHERE model_name = :model_name
              AND created_at >= now() - interval '30 days'
        """), {"model_name": m["name"]})
        row = r.one()
        calls = int(row.calls or 0)
        success_rate = round(int(row.successful_calls or 0) / max(calls, 1) * 100, 2)
        evaluation_status = "healthy" if calls and success_rate >= 98 else "degraded" if calls else "no_data"
        return {**m, "evaluation": {
            "status": evaluation_status,
            "period_days": 30,
            "calls": calls,
            "success_rate": success_rate if calls else None,
            "avg_latency_ms": round(float(row.avg_latency_ms), 1) if row.avg_latency_ms is not None else None,
            "cost": float(row.cost or 0),
            "last_used_at": row.last_used_at.isoformat() if row.last_used_at else None,
        }}
        return {**m, "evaluation": {"status": "ok", "message": "Evaluation stub — connect to ML pipeline for live eval"}}

    # ── Prediction Jobs ───────────────────────────────────────────────────────

    @staticmethod
    async def list_prediction_jobs(
        db: AsyncSession, *, status: str | None = None, job_type: str | None = None,
        page: int = 1, page_size: int = 25,
    ) -> dict[str, Any]:
        offset = (page - 1) * page_size
        try:
            stmt = select(IntelPredictionJob)
            if status:
                stmt = stmt.where(IntelPredictionJob.status == status)
            if job_type:
                stmt = stmt.where(IntelPredictionJob.job_type == job_type)
            r = await db.execute(select(func.count()).select_from(stmt.subquery()))
            total = r.scalar() or 0
            r2 = await db.execute(
                stmt.order_by(IntelPredictionJob.created_at.desc())
                .offset(offset).limit(page_size)
            )
            items = [row.to_dict() for row in r2.scalars()]
        except Exception:
            total, items = 0, []
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    @staticmethod
    async def create_prediction_job(db: AsyncSession, payload: dict, user_id: str | None) -> dict[str, Any]:
        if payload.get("job_type", "daily_tenant_risk") != "daily_tenant_risk":
            raise ValueError("Unsupported prediction job type")
        job = IntelPredictionJob(
            job_type=payload.get("job_type", "daily_tenant_risk"),
            status="running",
            triggered_by="manual",
            started_by_user_id=uuid.UUID(user_id) if user_id else None,
            started_at=_utcnow(),
        )
        db.add(job)
        # Persist the run record before starting the scoring transaction. If
        # the set-based workload fails, the operator still gets an auditable
        # failed run instead of losing the record with the rolled-back work.
        await db.commit()
        await db.refresh(job)

        # One set-based upsert replaces the old Python loop (and its LIMIT
        # 100).  PostgreSQL can plan this over indexed aggregates and update
        # every active Home Services provider without N+1 queries.
        try:
            r = await db.execute(text("""
                WITH job_stats AS (
                    SELECT tenant_id,
                           COUNT(*) FILTER (WHERE created_at >= now() - interval '90 days') AS jobs_90d,
                           COUNT(*) FILTER (
                               WHERE created_at >= now() - interval '90 days'
                                 AND (sla_breach = true OR sla_breached = true)
                           ) AS sla_breaches_90d
                    FROM jobs GROUP BY tenant_id
                ), complaint_stats AS (
                    SELECT tenant_id,
                           COUNT(*) FILTER (WHERE created_at >= now() - interval '90 days') AS complaints_90d,
                           COUNT(*) FILTER (WHERE status NOT IN ('resolved', 'closed', 'withdrawn')) AS open_complaints
                    FROM customer_complaints
                    WHERE tenant_id IS NOT NULL
                    GROUP BY tenant_id
                ), inputs AS (
                    SELECT t.id AS tenant_id,
                           COALESCE(j.jobs_90d, 0) AS jobs_90d,
                           COALESCE(j.sla_breaches_90d, 0) AS sla_breaches_90d,
                           COALESCE(c.complaints_90d, 0) AS complaints_90d,
                           COALESCE(c.open_complaints, 0) AS open_complaints,
                           COALESCE(b.credit_balance, 0) AS credit_balance
                    FROM tenants t
                    LEFT JOIN job_stats j ON j.tenant_id = t.id
                    LEFT JOIN complaint_stats c ON c.tenant_id = t.id
                    LEFT JOIN tenant_billing b ON b.tenant_id = t.id
                    WHERE t.status = 'active' AND t.vertical = 'home_services'
                ), scored AS (
                    SELECT *, LEAST(100.0,
                        LEAST((complaints_90d::numeric / GREATEST(jobs_90d, 1)) * 250.0, 45.0)
                        + LEAST(open_complaints * 5.0, 20.0)
                        + LEAST((sla_breaches_90d::numeric / GREATEST(jobs_90d, 1)) * 100.0, 25.0)
                        + CASE WHEN credit_balance <= 0 THEN 10.0 WHEN credit_balance < 1000 THEN 5.0 ELSE 0.0 END
                    ) AS score
                    FROM inputs
                )
                INSERT INTO intel_risk_scores (
                    entity_type, entity_id, risk_score, risk_level,
                    top_reasons_json, feature_contributions_json,
                    confidence_score, model_version, computed_at
                )
                SELECT 'tenant', tenant_id, ROUND(score, 2),
                       CASE WHEN score > 75 THEN 'critical'
                            WHEN score > 50 THEN 'high'
                            WHEN score > 25 THEN 'medium' ELSE 'low' END,
                       to_jsonb(array_remove(ARRAY[
                           CASE WHEN complaints_90d > 0 THEN complaints_90d || ' complaints in 90 days' END,
                           CASE WHEN open_complaints > 0 THEN open_complaints || ' unresolved complaints' END,
                           CASE WHEN sla_breaches_90d > 0 THEN sla_breaches_90d || ' SLA breaches in 90 days' END,
                           CASE WHEN credit_balance < 1000 THEN 'Usage-credit balance needs attention' END
                       ]::text[], NULL)),
                       jsonb_build_object(
                           'complaint_rate', ROUND(LEAST((complaints_90d::numeric / GREATEST(jobs_90d, 1)) * 250.0, 45.0), 2),
                           'unresolved_complaints', ROUND(LEAST(open_complaints * 5.0, 20.0), 2),
                           'sla_breaches', ROUND(LEAST((sla_breaches_90d::numeric / GREATEST(jobs_90d, 1)) * 100.0, 25.0), 2),
                           'usage_credit_readiness', CASE WHEN credit_balance <= 0 THEN 10.0 WHEN credit_balance < 1000 THEN 5.0 ELSE 0.0 END
                       ),
                       90.0, 'home-services-risk-v2', now()
                FROM scored
                ON CONFLICT (entity_type, entity_id) DO UPDATE SET
                    risk_score = EXCLUDED.risk_score,
                    risk_level = EXCLUDED.risk_level,
                    top_reasons_json = EXCLUDED.top_reasons_json,
                    feature_contributions_json = EXCLUDED.feature_contributions_json,
                    confidence_score = EXCLUDED.confidence_score,
                    model_version = EXCLUDED.model_version,
                    computed_at = EXCLUDED.computed_at,
                    updated_at = now()
                RETURNING entity_id
            """))
            processed = len(r.fetchall())
            job.status = "completed"
            job.total_processed = processed
            job.total_failed = 0
            job.result_summary_json = {
                "providers_scored": processed,
                "scope": "active_home_services",
                "model_version": "home-services-risk-v2",
            }
        except Exception as exc:
            logger.exception("intelligence.prediction.failed", job_id=str(job.id), error=str(exc))
            await db.rollback()
            r = await db.execute(
                select(IntelPredictionJob).where(IntelPredictionJob.id == job.id)
            )
            job = r.scalar_one()
            job.status = "failed"
            job.total_processed = 0
            job.total_failed = 1
            job.error_message = str(exc)[:1000]
        job.completed_at = _utcnow()
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
        await db.execute(text("DELETE FROM intel_data_quality_checks WHERE check_key = 'stale_health_scores'"))
        r = await db.execute(select(IntelDataQualityCheck))
        existing = {row.check_key: row for row in r.scalars()}
        for definition in DEFAULT_CHECKS:
            row = existing.get(definition["check_key"])
            if row is None:
                db.add(IntelDataQualityCheck(**definition))
                continue
            row.check_name = definition["check_name"]
            row.description = definition["description"]
            row.severity = definition["severity"]
            row.is_enabled = True
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
                r2 = await db.execute(text("""
                    SELECT COUNT(*) FROM tenants
                    WHERE status = 'active' AND vertical = 'home_services'
                      AND (COALESCE(NULLIF(TRIM(business_name), ''), NULLIF(TRIM(tenant_name), '')) IS NULL
                           OR email IS NULL OR TRIM(email) = ''
                           OR phone IS NULL OR TRIM(phone) = '')
                """))
                failure_count = r2.scalar() or 0
            elif check_key == "orphan_jobs":
                r2 = await db.execute(text("SELECT COUNT(*) FROM jobs j WHERE NOT EXISTS (SELECT 1 FROM tenants t WHERE t.id = j.tenant_id)"))
                failure_count = r2.scalar() or 0
            elif check_key == "duplicate_catalog_codes":
                r2 = await db.execute(text("SELECT COUNT(*) FROM (SELECT code FROM service_groups GROUP BY code HAVING COUNT(*) > 1) sub"))
                failure_count = r2.scalar() or 0
            elif check_key == "invalid_credit_deductions":
                r2 = await db.execute(text("""
                    SELECT COUNT(*) FROM usage_credit_ledger
                    WHERE balance_after <> balance_before + credit_delta
                       OR (event_type = 'job_completion_deduction' AND credit_delta >= 0)
                       OR (idempotency_key IS NOT NULL AND idempotency_key IN (
                            SELECT idempotency_key FROM usage_credit_ledger
                            WHERE idempotency_key IS NOT NULL
                            GROUP BY idempotency_key HAVING COUNT(*) > 1
                       ))
                """))
                failure_count = r2.scalar() or 0
            elif check_key == "missing_booking_prices":
                r2 = await db.execute(text("""
                    SELECT COUNT(*) FROM bookings
                    WHERE status NOT IN ('draft', 'cancelled', 'rejected')
                      AND quoted_price IS NULL AND estimated_price IS NULL
                      AND final_price IS NULL AND payable_amount IS NULL
                """))
                failure_count = r2.scalar() or 0
            elif check_key == "orphan_bookings":
                r2 = await db.execute(text("SELECT COUNT(*) FROM bookings b WHERE NOT EXISTS (SELECT 1 FROM tenants t WHERE t.id = b.tenant_id)"))
                failure_count = r2.scalar() or 0

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
    async def get_check_failures(
        db: AsyncSession, check_key: str, *, page: int = 1, page_size: int = 25,
    ) -> dict[str, Any]:
        r = await db.execute(
            select(IntelDataQualityCheck).where(IntelDataQualityCheck.check_key == check_key)
        )
        chk = r.scalar_one_or_none()
        if not chk:
            raise ValueError(f"Check {check_key!r} not found")
        offset = (page - 1) * page_size
        queries = {
            "missing_tenant_profiles": """
                SELECT id::text AS entity_id, 'provider' AS entity_type,
                       tenant_name AS label, 'Business name, email, or phone is missing' AS reason
                FROM tenants
                WHERE status = 'active' AND vertical = 'home_services'
                  AND (COALESCE(NULLIF(TRIM(business_name), ''), NULLIF(TRIM(tenant_name), '')) IS NULL
                       OR email IS NULL OR TRIM(email) = '' OR phone IS NULL OR TRIM(phone) = '')
                ORDER BY created_at DESC
            """,
            "orphan_jobs": """
                SELECT j.id::text AS entity_id, 'job' AS entity_type,
                       j.job_number AS label, 'Provider workspace does not exist' AS reason
                FROM jobs j WHERE NOT EXISTS (SELECT 1 FROM tenants t WHERE t.id = j.tenant_id)
                ORDER BY j.created_at DESC
            """,
            "duplicate_catalog_codes": """
                SELECT (array_agg(id ORDER BY id))[1]::text AS entity_id, 'service_group' AS entity_type,
                       code AS label, COUNT(*) || ' rows use this code' AS reason
                FROM service_groups GROUP BY code HAVING COUNT(*) > 1
                ORDER BY COUNT(*) DESC, code
            """,
            "invalid_credit_deductions": """
                SELECT id::text AS entity_id, 'usage_credit_ledger' AS entity_type,
                       COALESCE(request_id, id::text) AS label,
                       CASE
                         WHEN balance_after <> balance_before + credit_delta THEN 'Ledger arithmetic does not balance'
                         WHEN event_type = 'job_completion_deduction' AND credit_delta >= 0 THEN 'Completion deduction has a non-negative delta'
                         ELSE 'Idempotency key is duplicated'
                       END AS reason
                FROM usage_credit_ledger u
                WHERE balance_after <> balance_before + credit_delta
                   OR (event_type = 'job_completion_deduction' AND credit_delta >= 0)
                   OR (idempotency_key IS NOT NULL AND idempotency_key IN (
                        SELECT idempotency_key FROM usage_credit_ledger
                        WHERE idempotency_key IS NOT NULL GROUP BY idempotency_key HAVING COUNT(*) > 1))
                ORDER BY created_at DESC
            """,
            "missing_booking_prices": """
                SELECT id::text AS entity_id, 'booking' AS entity_type,
                       booking_number AS label, 'Confirmed booking has no authoritative price' AS reason
                FROM bookings
                WHERE status NOT IN ('draft', 'cancelled', 'rejected')
                  AND quoted_price IS NULL AND estimated_price IS NULL
                  AND final_price IS NULL AND payable_amount IS NULL
                ORDER BY created_at DESC
            """,
            "orphan_bookings": """
                SELECT b.id::text AS entity_id, 'booking' AS entity_type,
                       b.booking_number AS label, 'Provider workspace does not exist' AS reason
                FROM bookings b WHERE NOT EXISTS (SELECT 1 FROM tenants t WHERE t.id = b.tenant_id)
                ORDER BY b.created_at DESC
            """,
        }
        base_query = queries.get(check_key)
        if not base_query:
            return {"check_key": check_key, "items": [], "total": 0, "page": page, "page_size": page_size}
        total = int((await db.execute(text(f"SELECT COUNT(*) FROM ({base_query}) failures"))).scalar() or 0)
        rows = await db.execute(text(f"{base_query} LIMIT :limit OFFSET :offset"), {"limit": page_size, "offset": offset})
        items = [{
            "entity_id": row.entity_id,
            "entity_type": row.entity_type,
            "label": row.label,
            "reason": row.reason,
        } for row in rows]
        return {"check_key": check_key, "items": items, "total": total, "page": page, "page_size": page_size}

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
    async def list_ai_usage_logs(
        db: AsyncSession, *, feature_key: str | None = None, status: str | None = None,
        model_name: str | None = None, q: str | None = None,
        date_from: datetime | None = None, date_to: datetime | None = None,
        page: int = 1, page_size: int = 25,
    ) -> dict[str, Any]:
        offset = (page - 1) * page_size
        try:
            stmt = select(AiUsageLog)
            if feature_key:
                stmt = stmt.where(AiUsageLog.feature_key == feature_key)
            if status:
                stmt = stmt.where(AiUsageLog.status == status)
            if model_name:
                stmt = stmt.where(AiUsageLog.model_name == model_name)
            if date_from:
                stmt = stmt.where(AiUsageLog.created_at >= date_from)
            if date_to:
                stmt = stmt.where(AiUsageLog.created_at <= date_to)
            if q:
                pattern = f"%{q.strip()}%"
                stmt = stmt.where(or_(
                    AiUsageLog.feature_key.ilike(pattern),
                    AiUsageLog.model_name.ilike(pattern),
                    AiUsageLog.error_code.ilike(pattern),
                ))
            r = await db.execute(select(func.count()).select_from(stmt.subquery()))
            total = r.scalar() or 0
            r2 = await db.execute(
                stmt.order_by(AiUsageLog.created_at.desc())
                .offset(offset).limit(page_size)
            )
            items = [row.to_dict() for row in r2.scalars()]
        except Exception:
            total, items = 0, []
        return {"items": items, "total": total, "page": page, "page_size": page_size}

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
    async def get_audit_logs(
        db: AsyncSession, *, q: str | None = None, engine_id: str | None = None,
        operation: str | None = None, high_risk: bool | None = None,
        page: int = 1, page_size: int = 25,
    ) -> dict[str, Any]:
        """Return the append-only platform audit trail for intelligence engines."""
        offset = (page - 1) * page_size
        try:
            intelligence_engines = ["analytics", "intelligence", "rag", "ai_conversation", "data_science"]
            stmt = select(PlatformAuditLog).where(PlatformAuditLog.engine_id.in_(intelligence_engines))
            if q:
                pattern = f"%{q.strip()}%"
                stmt = stmt.where(or_(
                    PlatformAuditLog.operation.ilike(pattern),
                    PlatformAuditLog.entity_type.ilike(pattern),
                    PlatformAuditLog.entity_id.ilike(pattern),
                    PlatformAuditLog.request_id.ilike(pattern),
                    cast(PlatformAuditLog.actor_id, String).ilike(pattern),
                ))
            if engine_id:
                stmt = stmt.where(PlatformAuditLog.engine_id == engine_id)
            if operation:
                stmt = stmt.where(PlatformAuditLog.operation == operation)
            if high_risk is not None:
                stmt = stmt.where(PlatformAuditLog.is_high_risk == high_risk)
            total = int((await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar() or 0)
            r = await db.execute(
                stmt.order_by(PlatformAuditLog.created_at.desc()).offset(offset).limit(page_size)
            )
            items = [{
                "id": str(row.id),
                "time": row.created_at.isoformat() if row.created_at else None,
                "actor": str(row.actor_id) if row.actor_id else None,
                "actor_role": row.actor_role,
                "action": row.operation,
                "engine_id": row.engine_id,
                "target": row.entity_type,
                "target_id": row.entity_id,
                "request_id": row.request_id,
                "is_high_risk": row.is_high_risk,
            } for row in r.scalars()]
        except Exception:
            items, total = [], 0
        return {"items": items, "total": total, "page": page, "page_size": page_size}
