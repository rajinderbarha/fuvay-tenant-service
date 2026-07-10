"""Analytics Engine — AnalyticsService."""
from __future__ import annotations
import uuid
from datetime import datetime, timezone, timedelta, date
from decimal import Decimal
import structlog
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.engines.analytics.models import AnalyticsEvent, DailyMetric
from app.exceptions import ServiceOSException, NotFoundException
from app.redis_client import get_redis
from app.schemas.base import encode_cursor, decode_cursor

logger = structlog.get_logger("analytics.service")
utcnow = lambda: datetime.now(timezone.utc)
today = lambda: utcnow().date()


class AnalyticsService:
    def __init__(self, db: AsyncSession, request_id: str = "—",
                 actor_id: uuid.UUID | None = None):
        self.db = db; self.redis = get_redis()
        self.request_id = request_id; self.actor_id = actor_id

    async def ingest_event(self, event_id: str, tenant_id: uuid.UUID | None,
                            event_type: str, engine_id: str, entity_type: str | None,
                            entity_id: str | None, actor_id: uuid.UUID | None,
                            payload: dict, occurred_at: datetime | None) -> dict:
        """Idempotent on event_id."""
        ex = await self.db.execute(select(AnalyticsEvent).where(
            AnalyticsEvent.event_id == event_id))
        if ex.scalar_one_or_none():
            return {"event_id": event_id, "idempotent": True, "status": "already_ingested"}
        ev = AnalyticsEvent(event_id=event_id, tenant_id=tenant_id, event_type=event_type,
            engine_id=engine_id, entity_type=entity_type, entity_id=entity_id,
            actor_id=actor_id, payload=payload,
            occurred_at=occurred_at or utcnow())
        self.db.add(ev); await self.db.flush()
        return {"event_id": event_id, "status": "ingested", "idempotent": False}

    async def get_platform_summary(self) -> dict:
        """Real-time platform KPIs from Redis signals + DB counts."""
        try:
            keys = await self.redis.keys("serviceos:health:*:credit_wallet_health")
            active_tenants = len(keys)
        except Exception:
            active_tenants = 0

        today_start = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        ev_r = await self.db.execute(select(func.count(AnalyticsEvent.id)).where(
            AnalyticsEvent.occurred_at >= today_start))
        events_today = ev_r.scalar_one_or_none() or 0

        return {
            "active_tenants_estimate": active_tenants,
            "events_today": events_today,
            "generated_at": utcnow().isoformat(),
            "_note": "Full aggregates computed by Celery beat — daily_metrics table in Phase 7."
        }

    async def get_tenant_metrics(self, tenant_id: uuid.UUID, days: int) -> dict:
        since = utcnow() - timedelta(days=days)
        r = await self.db.execute(select(AnalyticsEvent.event_type,
                                          func.count(AnalyticsEvent.id)).where(
            AnalyticsEvent.tenant_id == tenant_id,
            AnalyticsEvent.occurred_at >= since
        ).group_by(AnalyticsEvent.event_type))
        rows = r.all()
        return {"tenant_id": str(tenant_id), "period_days": days,
                "event_counts": {row[0]: row[1] for row in rows},
                "generated_at": utcnow().isoformat()}

    async def get_event_stream(self, tenant_id: uuid.UUID | None, event_type: str | None,
                                limit: int, cursor: str | None) -> dict:
        q = select(AnalyticsEvent).order_by(AnalyticsEvent.occurred_at.desc())
        if tenant_id: q = q.where(AnalyticsEvent.tenant_id == tenant_id)
        if event_type: q = q.where(AnalyticsEvent.event_type == event_type)
        if cursor:
            try:
                c = decode_cursor(cursor)
                q = q.where(AnalyticsEvent.occurred_at < datetime.fromisoformat(c["occurred_at"]))
            except Exception: pass
        q = q.limit(limit + 1)
        r = await self.db.execute(q)
        items = r.scalars().all()
        has_next = len(items) > limit; items = items[:limit]
        nc = encode_cursor({"occurred_at": items[-1].occurred_at.isoformat()}) if has_next and items else None
        return {"events": [{"event_id": e.event_id, "event_type": e.event_type,
                "engine_id": e.engine_id, "entity_type": e.entity_type,
                "payload": e.payload, "occurred_at": e.occurred_at.isoformat()}
               for e in items], "has_next": has_next, "next_cursor": nc}

    async def get_daily_metrics(self, tenant_id: uuid.UUID | None,
                                 metric_key: str, days: int) -> dict:
        since = today() - timedelta(days=days)
        q = select(DailyMetric).where(DailyMetric.metric_date >= since,
                                       DailyMetric.metric_key == metric_key)
        if tenant_id: q = q.where(DailyMetric.tenant_id == tenant_id)
        else: q = q.where(DailyMetric.tenant_id == None)
        q = q.order_by(DailyMetric.metric_date.desc())
        r = await self.db.execute(q)
        items = r.scalars().all()
        return {"metric_key": metric_key, "period_days": days,
                "data": [{"date": str(m.metric_date),
                          "value": float(m.value_num) if m.value_num else m.value_json}
                         for m in items]}

    async def upsert_daily_metric(self, tenant_id: uuid.UUID | None, metric_date: date,
                                   metric_key: str, value_num: Decimal | None,
                                   value_json: dict | None) -> dict:
        r = await self.db.execute(select(DailyMetric).where(
            DailyMetric.tenant_id == tenant_id,
            DailyMetric.metric_date == metric_date,
            DailyMetric.metric_key == metric_key))
        existing = r.scalar_one_or_none()
        if existing:
            existing.value_num = value_num; existing.value_json = value_json
            existing.computed_at = utcnow()
        else:
            self.db.add(DailyMetric(tenant_id=tenant_id, metric_date=metric_date,
                metric_key=metric_key, value_num=value_num, value_json=value_json))
        return {"metric_key": metric_key, "metric_date": str(metric_date), "updated": True}
