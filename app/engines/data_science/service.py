"""Data Science Engine — DSService. All prediction logic with 4-phase cold-start."""
from __future__ import annotations
import random
import uuid
from datetime import datetime, timezone, timedelta, date
from decimal import Decimal

import structlog
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.data_science.constants import (
    DSPhase, JOB_THRESHOLD_OBSERVATION, JOB_THRESHOLD_PLATFORM_MODEL,
    JOB_THRESHOLD_TENANT_MODEL, CHURN_BANDS, CHURN_SIGNAL_WEIGHTS,
    STAFF_SIGNAL_WEIGHTS, ANOMALY_THRESHOLDS, LTV_HORIZON_MONTHS,
    ModelType, PredType, AnomalyType, FORECAST_HORIZON_DAYS,
    REDIS_CHURN_SCORE, REDIS_DEMAND_CAST, REDIS_DS_PHASE,
)
from app.engines.data_science.models import (
    PredictionRecord, ChurnSignal, DemandForecast,
    StaffPerformanceScore, CustomerLTVScore, AnomalyRecord, ModelVersion,
)
from app.exceptions import ServiceOSException, NotFoundException
from app.redis_client import get_redis, cache_set, cache_get, cache_delete
from app.schemas.base import encode_cursor, decode_cursor

logger = structlog.get_logger("ds.service")
utcnow = lambda: datetime.now(timezone.utc)
today  = lambda: utcnow().date()


class DSService:
    def __init__(self, db: AsyncSession, request_id: str = "—",
                 actor_id: uuid.UUID | None = None, actor_role: str | None = None,
                 actor_tenant_id: uuid.UUID | None = None):
        self.db = db
        self.redis = get_redis()
        self.request_id = request_id
        self.actor_id = actor_id
        self.actor_role = actor_role
        self.actor_tenant_id = actor_tenant_id

    def _require_trusted_tenant(self, requested_tenant_id: uuid.UUID) -> uuid.UUID:
        """Slice 2F-36: demand-forecast recompute, pricing-recommendation
        apply, and customer-LTV recompute accepted a client-supplied
        tenant_id path param with no comparison to the caller's own
        tenant. super_admin is exempt (platform-wide)."""
        if self.actor_role == "super_admin":
            return requested_tenant_id
        if self.actor_tenant_id is None:
            raise ServiceOSException(
                "PERMISSION_DENIED", "No tenant context.",
                blocking_rule="ds_mutation_requires_trusted_tenant_context")
        if requested_tenant_id != self.actor_tenant_id:
            raise ServiceOSException(
                "PERMISSION_DENIED", "You do not have access to this tenant's data science records.",
                blocking_rule="ds_mutation_cross_tenant_denied")
        return self.actor_tenant_id

    # ── Phase detection ───────────────────────────────────────────────────────
    async def _get_ds_phase(self, tenant_id: uuid.UUID) -> int:
        """Determine operational phase from job count."""
        cache_key = REDIS_DS_PHASE.format(tenant_id=tenant_id)
        try:
            cached = await self.redis.get(cache_key)
            if cached:
                return int(cached)
        except Exception:
            pass

        try:
            from app.engines.platform_commerce.models import CommissionRecord
            r = await self.db.execute(select(func.count(CommissionRecord.id)).where(
                CommissionRecord.tenant_id == tenant_id))
            job_count = r.scalar_one_or_none() or 0
        except Exception:
            job_count = 0

        if job_count >= JOB_THRESHOLD_TENANT_MODEL:
            phase = DSPhase.TENANT_MODEL
        elif job_count >= JOB_THRESHOLD_PLATFORM_MODEL:
            phase = DSPhase.PLATFORM_MODEL
        elif job_count >= JOB_THRESHOLD_OBSERVATION:
            phase = DSPhase.OBSERVATION
        else:
            phase = DSPhase.RULE_BASED

        try:
            await self.redis.setex(cache_key, 3600, str(phase))
        except Exception:
            pass
        return phase

    async def _get_active_model_version(self, model_type: str) -> str:
        r = await self.db.execute(select(ModelVersion).where(
            ModelVersion.model_type == model_type,
            ModelVersion.is_active == True))
        mv = r.scalar_one_or_none()
        return mv.version if mv else "rule_based_v1"

    async def _save_prediction(self, tenant_id: uuid.UUID | None, entity_id: str | None,
                                entity_type: str | None, prediction_type: str,
                                model_type: str, model_version: str, ds_phase: int,
                                inputs: dict, output: dict, confidence: float | None) -> PredictionRecord:
        rec = PredictionRecord(
            tenant_id=tenant_id, entity_id=entity_id, entity_type=entity_type,
            prediction_type=prediction_type, model_type=model_type,
            model_version=model_version, ds_phase=ds_phase,
            observation_mode=ds_phase < DSPhase.PLATFORM_MODEL,
            inputs=inputs, output=output, confidence=confidence,
        )
        self.db.add(rec)
        await self.db.flush()
        return rec

    async def _publish(self, event_type: str, tenant_id: str, entity_id: str, payload: dict):
        try:
            from app.core.events import get_event_bus
            bus = get_event_bus()
            await bus.publish_raw(event_type=event_type, engine_id="data_science",
                tenant_id=tenant_id, entity_type="ds", entity_id=entity_id,
                payload=payload, actor_id=str(self.actor_id) if self.actor_id else None)
        except Exception as e:
            logger.warning("ds.event_failed", error=str(e))

    def _churn_band(self, score: float) -> str:
        for band, (lo, hi) in CHURN_BANDS.items():
            if lo <= score <= hi:
                return band
        return "critical"

    # ── Churn Prediction (4 methods) ──────────────────────────────────────────
    async def get_churn_score(self, tenant_id: uuid.UUID) -> dict:
        phase = await self._get_ds_phase(tenant_id)
        mv    = await self._get_active_model_version(ModelType.CHURN_PLATFORM)

        # Load existing or compute fresh
        r = await self.db.execute(select(ChurnSignal).where(
            ChurnSignal.tenant_id == tenant_id))
        existing = r.scalar_one_or_none()

        # Rule-based score from tenant health (Phase 0/1)
        try:
            from app.engines.tenant_engine.models import Tenant
            tr = await self.db.execute(select(Tenant).where(Tenant.id == tenant_id))
            tenant = tr.scalar_one_or_none()
            health_score = float(tenant.health_score) if tenant else 80.0
            health_band  = tenant.health_band if tenant else "gold"
        except Exception:
            health_score = 80.0; health_band = "gold"

        # Signal computation (rule-based fallback)
        signals = {
            "days_since_last_job":    0.0,
            "wallet_balance_trend":   max(0.0, 100.0 - (100.0 - health_score)),
            "health_score_trend":     health_score,
            "complaint_rate":         0.0,
            "booking_frequency_drop": 0.0,
        }

        churn_score = max(0.0, min(100.0,
            100.0 - sum(signals[k] * w for k, w in CHURN_SIGNAL_WEIGHTS.items())))

        factors = sorted([
            {"signal": k, "value": signals[k], "weight": w,
             "contribution": round((100.0 - signals[k]) * w, 2)}
            for k, w in CHURN_SIGNAL_WEIGHTS.items()
        ], key=lambda x: x["contribution"], reverse=True)[:3]

        band = self._churn_band(churn_score)
        prev = float(existing.churn_score) if existing else None
        delta = round(churn_score - prev, 2) if prev is not None else None

        if existing:
            existing.churn_score = churn_score; existing.churn_band = band
            existing.signal_values = signals; existing.contributing_factors = factors
            existing.prev_score = prev; existing.score_delta = delta
            existing.ds_phase = phase; existing.model_version = mv
            existing.observation_mode = phase < DSPhase.PLATFORM_MODEL
            existing.computed_at = utcnow()
        else:
            self.db.add(ChurnSignal(
                tenant_id=tenant_id, churn_score=churn_score, churn_band=band,
                signal_values=signals, contributing_factors=factors,
                prev_score=prev, score_delta=delta, ds_phase=phase,
                model_version=mv, observation_mode=phase < DSPhase.PLATFORM_MODEL,
            ))

        await self._save_prediction(tenant_id, str(tenant_id), "tenant",
            PredType.CHURN, ModelType.CHURN_PLATFORM, mv, phase,
            inputs=signals, output={"churn_score": churn_score, "band": band},
            confidence=0.6 if phase >= DSPhase.PLATFORM_MODEL else None)

        await cache_delete(REDIS_CHURN_SCORE.format(tenant_id=tenant_id))
        await self._publish("ds.churn_score_updated", str(tenant_id), str(tenant_id),
                            {"churn_score": churn_score, "band": band, "phase": phase})

        return {
            "tenant_id": str(tenant_id), "churn_score": round(churn_score, 2),
            "churn_band": band, "contributing_factors": factors,
            "score_delta": delta, "prev_score": prev,
            "observation_mode": phase < DSPhase.PLATFORM_MODEL,
            "ds_phase": phase, "model_version": mv,
            "computed_at": utcnow().isoformat(),
            "interpretation": (
                "Platform benchmark — fewer than 500 jobs. Score improves with more data."
                if phase < DSPhase.PLATFORM_MODEL else
                f"Personalised prediction. Confidence: {60 if phase == DSPhase.PLATFORM_MODEL else 80}%"
            ),
        }

    async def list_at_risk_tenants(self, limit: int, cursor: str | None) -> dict:
        q = select(ChurnSignal).where(
            ChurnSignal.churn_band.in_(["high", "critical"])
        ).order_by(ChurnSignal.churn_score.desc())
        if cursor:
            try:
                c = decode_cursor(cursor)
                q = q.where(ChurnSignal.churn_score < float(c["churn_score"]))
            except Exception:
                pass
        q = q.limit(limit + 1)
        r = await self.db.execute(q)
        items = r.scalars().all()
        has_next = len(items) > limit; items = items[:limit]
        nc = encode_cursor({"churn_score": items[-1].churn_score}) if has_next and items else None
        return {
            "at_risk_tenants": [{
                "tenant_id": str(s.tenant_id), "churn_score": round(s.churn_score, 2),
                "churn_band": s.churn_band, "score_delta": s.score_delta,
                "observation_mode": s.observation_mode, "computed_at": s.computed_at.isoformat(),
            } for s in items],
            "has_next": has_next, "next_cursor": nc,
        }

    async def get_churn_factors(self, tenant_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(ChurnSignal).where(
            ChurnSignal.tenant_id == tenant_id))
        s = r.scalar_one_or_none()
        if not s:
            return await self.get_churn_score(tenant_id)
        return {
            "tenant_id": str(tenant_id), "churn_score": round(s.churn_score, 2),
            "churn_band": s.churn_band, "contributing_factors": s.contributing_factors,
            "signal_values": s.signal_values, "observation_mode": s.observation_mode,
            "recommended_actions": self._churn_actions(s.churn_band),
        }

    def _churn_actions(self, band: str) -> list:
        if band == "critical":
            return [{"action": "immediate_outreach", "priority": "urgent"},
                    {"action": "offer_credit_discount", "priority": "high"},
                    {"action": "escalate_to_account_manager", "priority": "high"}]
        if band == "high":
            return [{"action": "send_engagement_campaign", "priority": "high"},
                    {"action": "offer_plan_upgrade_discount", "priority": "medium"}]
        return [{"action": "monitor_weekly", "priority": "low"}]

    async def get_churn_history(self, tenant_id: uuid.UUID, days: int) -> dict:
        since = utcnow() - timedelta(days=days)
        r = await self.db.execute(select(PredictionRecord).where(
            PredictionRecord.tenant_id == tenant_id,
            PredictionRecord.prediction_type == PredType.CHURN,
            PredictionRecord.computed_at >= since,
        ).order_by(PredictionRecord.computed_at.desc()))
        records = r.scalars().all()
        return {
            "tenant_id": str(tenant_id), "days": days,
            "history": [{"score": r.output.get("churn_score"), "band": r.output.get("band"),
                         "ds_phase": r.ds_phase, "computed_at": r.computed_at.isoformat()}
                        for r in records],
        }

    # ── Demand Forecasting (3 methods) ────────────────────────────────────────
    async def get_demand_forecast(self, tenant_id: uuid.UUID) -> dict:
        phase = await self._get_ds_phase(tenant_id)
        mv    = await self._get_active_model_version(ModelType.DEMAND_PROPHET)

        # Check for fresh forecast (< 6h old)
        r = await self.db.execute(select(DemandForecast).where(
            DemandForecast.tenant_id == tenant_id,
            DemandForecast.forecast_date == today(),
        ))
        existing = r.scalar_one_or_none()
        if existing and (utcnow() - existing.computed_at).seconds < 21600:
            return self._forecast_dict(existing)

        # Rule-based forecast: flat average based on vertical + day-of-week pattern
        daily = []
        base = 3.0 if phase == DSPhase.RULE_BASED else 4.0
        for i in range(FORECAST_HORIZON_DAYS):
            d = today() + timedelta(days=i + 1)
            dow = d.weekday()
            multiplier = 1.4 if dow >= 5 else 1.0  # weekend surge
            predicted = round(base * multiplier, 1)
            daily.append({"date": str(d), "predicted_jobs": predicted,
                           "lower_bound": round(predicted * 0.7, 1),
                           "upper_bound": round(predicted * 1.3, 1)})

        peak = max(daily, key=lambda x: x["predicted_jobs"])
        total = sum(d["predicted_jobs"] for d in daily)

        if existing:
            existing.daily_forecasts = daily; existing.total_predicted = total
            existing.peak_day = peak["date"]; existing.ds_phase = phase
            existing.model_version = mv; existing.computed_at = utcnow()
            existing.observation_mode = phase < DSPhase.PLATFORM_MODEL
        else:
            self.db.add(DemandForecast(
                tenant_id=tenant_id, forecast_date=today(),
                daily_forecasts=daily, total_predicted=total,
                peak_day=peak["date"], ds_phase=phase, model_version=mv,
                observation_mode=phase < DSPhase.PLATFORM_MODEL,
            ))
        await self.db.flush()

        await self._save_prediction(tenant_id, str(tenant_id), "tenant",
            PredType.DEMAND, ModelType.DEMAND_PROPHET, mv, phase,
            inputs={"base_rate": base, "phase": phase},
            output={"total": total, "peak_day": peak["date"]}, confidence=None)

        r2 = await self.db.execute(select(DemandForecast).where(
            DemandForecast.tenant_id == tenant_id,
            DemandForecast.forecast_date == today()))
        fc = r2.scalar_one_or_none()
        return self._forecast_dict(fc) if fc else {"tenant_id": str(tenant_id), "daily_forecasts": daily}

    def _forecast_dict(self, fc: DemandForecast) -> dict:
        return {
            "tenant_id": str(fc.tenant_id), "forecast_date": str(fc.forecast_date),
            "horizon_days": fc.horizon_days, "total_predicted": round(fc.total_predicted, 1),
            "peak_day": fc.peak_day, "daily_forecasts": fc.daily_forecasts,
            "observation_mode": fc.observation_mode, "ds_phase": fc.ds_phase,
            "model_version": fc.model_version, "computed_at": fc.computed_at.isoformat(),
            "interpretation": (
                "Rule-based estimate. Personalises after 500+ jobs."
                if fc.observation_mode else "Data-driven forecast."
            ),
        }

    async def trigger_recompute(self, tenant_id: uuid.UUID) -> dict:
        tenant_id = self._require_trusted_tenant(tenant_id)
        r = await self.db.execute(select(DemandForecast).where(
            DemandForecast.tenant_id == tenant_id,
            DemandForecast.forecast_date == today()))
        existing = r.scalar_one_or_none()
        if existing:
            existing.computed_at = utcnow() - timedelta(hours=7)  # Force refresh
        result = await self.get_demand_forecast(tenant_id)
        await cache_delete(REDIS_DEMAND_CAST.format(tenant_id=tenant_id))
        return {**result, "recomputed": True}

    async def get_forecast_history(self, tenant_id: uuid.UUID, days: int) -> dict:
        since_date = today() - timedelta(days=days)
        r = await self.db.execute(select(DemandForecast).where(
            DemandForecast.tenant_id == tenant_id,
            DemandForecast.forecast_date >= since_date,
        ).order_by(DemandForecast.forecast_date.desc()))
        items = r.scalars().all()
        return {
            "tenant_id": str(tenant_id), "days": days,
            "forecasts": [{"forecast_date": str(f.forecast_date),
                           "total_predicted": round(f.total_predicted, 1),
                           "peak_day": f.peak_day, "model_version": f.model_version}
                          for f in items],
        }

    # ── Pricing Recommendations (3 methods) ───────────────────────────────────
    async def get_pricing_recommendations(self, tenant_id: uuid.UUID) -> dict:
        phase = await self._get_ds_phase(tenant_id)
        mv    = await self._get_active_model_version(ModelType.CHURN_PLATFORM)

        try:
            from app.engines.pricing.models import ServiceTypePrice
            r = await self.db.execute(select(ServiceTypePrice).where(
                ServiceTypePrice.tenant_id == tenant_id,
                ServiceTypePrice.valid_until == None))
            prices = r.scalars().all()
        except Exception:
            prices = []

        recommendations = []
        for p in prices:
            from app.engines.pricing.models import CityTierConfig
            floor_r = await self.db.execute(select(CityTierConfig).where(
                CityTierConfig.city_name == p.city_name,
                CityTierConfig.service_category == p.service_category,
                CityTierConfig.is_active == True))
            floor = floor_r.scalar_one_or_none()
            floor_price = float(floor.floor_price) if floor else float(p.base_price) * 0.8
            current = float(p.base_price)
            benchmark = floor_price * 1.4  # platform average estimate

            gap_pct = round((benchmark - current) / benchmark * 100, 1) if benchmark > 0 else 0
            recommendations.append({
                "service_type_id": p.service_type_id,
                "current_price": current,
                "benchmark_price": round(benchmark, 2),
                "floor_price": floor_price,
                "gap_pct": gap_pct,
                "action": "increase" if gap_pct > 15 else ("decrease" if gap_pct < -15 else "hold"),
                "potential_uplift": round(max(0.0, (benchmark - current)), 2),
            })

        await self._save_prediction(tenant_id, str(tenant_id), "tenant",
            PredType.PRICING, mv, mv, phase,
            inputs={"price_count": len(prices)},
            output={"recommendations": len(recommendations)}, confidence=None)

        return {
            "tenant_id": str(tenant_id), "recommendations": recommendations,
            "observation_mode": phase < DSPhase.PLATFORM_MODEL,
            "ds_phase": phase, "generated_at": utcnow().isoformat(),
        }

    async def apply_pricing_recommendation(self, tenant_id: uuid.UUID,
                                            service_type_id: str, target_price: float) -> dict:
        tenant_id = self._require_trusted_tenant(tenant_id)
        return {
            "tenant_id": str(tenant_id), "service_type_id": service_type_id,
            "applied_price": target_price, "applied": True,
            "note": "Price update delegated to Pricing Engine — POST /v1/pricing/tenants/{id}/prices/set",
        }

    async def get_pricing_history(self, tenant_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(PredictionRecord).where(
            PredictionRecord.tenant_id == tenant_id,
            PredictionRecord.prediction_type == PredType.PRICING,
        ).order_by(PredictionRecord.computed_at.desc()).limit(20))
        recs = r.scalars().all()
        return {"tenant_id": str(tenant_id),
                "history": [{"computed_at": r.computed_at.isoformat(),
                              "recommendations": r.output.get("recommendations")} for r in recs]}

    # ── Staff Performance (3 methods) ─────────────────────────────────────────
    async def get_staff_rankings(self, tenant_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(StaffPerformanceScore).where(
            StaffPerformanceScore.tenant_id == tenant_id
        ).order_by(StaffPerformanceScore.composite_score.desc()))
        scores = r.scalars().all()
        phase = await self._get_ds_phase(tenant_id)
        return {
            "tenant_id": str(tenant_id), "observation_mode": phase < DSPhase.OBSERVATION,
            "rankings": [{"staff_id": str(s.staff_id), "rank": s.rank_in_tenant,
                           "composite_score": round(s.composite_score, 2),
                           "jobs_completed": s.jobs_completed,
                           "avg_rating": round(s.avg_customer_rating, 2),
                           "sla_adherence": round(s.sla_adherence_rate, 1),
                           "computed_at": s.computed_at.isoformat()} for s in scores],
        }

    async def get_staff_score(self, staff_id: uuid.UUID, tenant_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(StaffPerformanceScore).where(
            StaffPerformanceScore.staff_id == staff_id,
            StaffPerformanceScore.tenant_id == tenant_id))
        s = r.scalar_one_or_none()
        if not s:
            raise NotFoundException("StaffPerformanceScore", str(staff_id))
        return {
            "staff_id": str(s.staff_id), "tenant_id": str(s.tenant_id),
            "composite_score": round(s.composite_score, 2), "rank": s.rank_in_tenant,
            "signal_values": s.signal_values, "jobs_completed": s.jobs_completed,
            "avg_customer_rating": round(s.avg_customer_rating, 2),
            "sla_adherence_rate": round(s.sla_adherence_rate, 1),
            "observation_mode": s.observation_mode, "computed_at": s.computed_at.isoformat(),
        }

    async def update_staff_signal(self, staff_id: uuid.UUID, tenant_id: uuid.UUID,
                                   signal: str, value: float) -> dict:
        if signal not in STAFF_SIGNAL_WEIGHTS:
            raise ServiceOSException("VALIDATION_ERROR",
                f"Unknown signal: {signal}. Valid: {list(STAFF_SIGNAL_WEIGHTS.keys())}")
        r = await self.db.execute(select(StaffPerformanceScore).where(
            StaffPerformanceScore.staff_id == staff_id,
            StaffPerformanceScore.tenant_id == tenant_id))
        existing = r.scalar_one_or_none()
        phase = await self._get_ds_phase(tenant_id)

        if existing:
            signals = dict(existing.signal_values)
            signals[signal] = value
            score = sum(signals.get(k, 50.0) * w for k, w in STAFF_SIGNAL_WEIGHTS.items())
            score = round(min(100.0, max(0.0, score)), 2)
            existing.signal_values = signals; existing.composite_score = score
            existing.observation_mode = phase < DSPhase.OBSERVATION
            existing.computed_at = utcnow()
        else:
            signals = {k: 50.0 for k in STAFF_SIGNAL_WEIGHTS}
            signals[signal] = value
            score = sum(signals[k] * w for k, w in STAFF_SIGNAL_WEIGHTS.items())
            score = round(min(100.0, max(0.0, score)), 2)
            self.db.add(StaffPerformanceScore(
                staff_id=staff_id, tenant_id=tenant_id, composite_score=score,
                signal_values=signals, observation_mode=phase < DSPhase.OBSERVATION,
            ))
        await self.db.flush()
        return {"staff_id": str(staff_id), "signal": signal, "value": value,
                "new_composite_score": score}

    # ── Customer LTV (3 methods) ───────────────────────────────────────────────
    async def get_customer_ltv(self, customer_id: uuid.UUID, tenant_id: uuid.UUID) -> dict:
        # Slice 2F-36: this is a "mutating GET" (lazy-creates a
        # CustomerLTVScore row on first access, same pattern as the 2F-26
        # commerce-deposit routes) -- tenant_id must be trusted, not
        # accepted from the client path unchecked.
        tenant_id = self._require_trusted_tenant(tenant_id)
        r = await self.db.execute(select(CustomerLTVScore).where(
            CustomerLTVScore.customer_id == customer_id,
            CustomerLTVScore.tenant_id == tenant_id))
        s = r.scalar_one_or_none()
        phase = await self._get_ds_phase(tenant_id)

        if not s:
            ltv = Decimal("5000.00"); band = "medium"
            s = CustomerLTVScore(customer_id=customer_id, tenant_id=tenant_id,
                predicted_ltv=ltv, ltv_band=band, booking_frequency=1.0,
                avg_job_value=Decimal("800.00"), churn_probability=0.3,
                observation_mode=phase < DSPhase.PLATFORM_MODEL)
            self.db.add(s); await self.db.flush()

        return {
            "customer_id": str(s.customer_id), "tenant_id": str(s.tenant_id),
            "predicted_ltv": float(s.predicted_ltv), "ltv_band": s.ltv_band,
            "booking_frequency_per_month": s.booking_frequency,
            "avg_job_value": float(s.avg_job_value),
            "churn_probability": round(s.churn_probability, 3),
            "ltv_horizon_months": LTV_HORIZON_MONTHS,
            "observation_mode": s.observation_mode, "computed_at": s.computed_at.isoformat(),
        }

    async def list_high_value_customers(self, tenant_id: uuid.UUID, limit: int) -> dict:
        r = await self.db.execute(select(CustomerLTVScore).where(
            CustomerLTVScore.tenant_id == tenant_id,
        ).order_by(CustomerLTVScore.predicted_ltv.desc()).limit(limit))
        items = r.scalars().all()
        return {
            "tenant_id": str(tenant_id),
            "high_value_customers": [{
                "customer_id": str(s.customer_id),
                "predicted_ltv": float(s.predicted_ltv),
                "ltv_band": s.ltv_band,
                "booking_frequency": s.booking_frequency,
                "churn_probability": round(s.churn_probability, 3),
            } for s in items],
        }

    async def recompute_ltv(self, customer_id: uuid.UUID, tenant_id: uuid.UUID) -> dict:
        tenant_id = self._require_trusted_tenant(tenant_id)
        r = await self.db.execute(select(CustomerLTVScore).where(
            CustomerLTVScore.customer_id == customer_id,
            CustomerLTVScore.tenant_id == tenant_id))
        s = r.scalar_one_or_none()
        if s:
            s.computed_at = utcnow()
        return await self.get_customer_ltv(customer_id, tenant_id)

    # ── Anomaly Detection (3 methods) ─────────────────────────────────────────
    async def list_anomalies(self, tenant_id: uuid.UUID | None,
                              status: str | None, limit: int, cursor: str | None) -> dict:
        q = select(AnomalyRecord).order_by(AnomalyRecord.created_at.desc())
        if tenant_id: q = q.where(AnomalyRecord.tenant_id == tenant_id)
        if status:    q = q.where(AnomalyRecord.status == status)
        if cursor:
            try:
                c = decode_cursor(cursor)
                q = q.where(AnomalyRecord.created_at < datetime.fromisoformat(c["created_at"]))
            except Exception: pass
        q = q.limit(limit + 1)
        r = await self.db.execute(q)
        items = r.scalars().all()
        has_next = len(items) > limit; items = items[:limit]
        nc = encode_cursor({"created_at": items[-1].created_at.isoformat()}) if has_next and items else None
        return {
            "anomalies": [self._anomaly_dict(a) for a in items],
            "has_next": has_next, "next_cursor": nc,
        }

    async def get_anomaly(self, anomaly_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(AnomalyRecord).where(AnomalyRecord.id == anomaly_id))
        a = r.scalar_one_or_none()
        if not a: raise NotFoundException("AnomalyRecord", str(anomaly_id))
        return self._anomaly_dict(a)

    async def acknowledge_anomaly(self, anomaly_id: uuid.UUID, notes: str | None) -> dict:
        r = await self.db.execute(select(AnomalyRecord).where(AnomalyRecord.id == anomaly_id))
        a = r.scalar_one_or_none()
        if not a: raise NotFoundException("AnomalyRecord", str(anomaly_id))
        if self.actor_role != "super_admin" and (
            self.actor_tenant_id is None or a.tenant_id != self.actor_tenant_id
        ):
            raise NotFoundException("AnomalyRecord", str(anomaly_id))
        if a.status == "acknowledged":
            raise ServiceOSException("CONFLICT", "Anomaly already acknowledged.")
        a.status = "acknowledged"; a.acknowledged_by = self.actor_id
        a.acknowledged_at = utcnow(); a.resolution_notes = notes
        return self._anomaly_dict(a)

    def _anomaly_dict(self, a: AnomalyRecord) -> dict:
        return {
            "anomaly_id": str(a.id), "tenant_id": str(a.tenant_id),
            "anomaly_type": a.anomaly_type, "severity": a.severity,
            "description": a.description, "detected_value": a.detected_value,
            "threshold_value": a.threshold_value, "context": a.context,
            "status": a.status, "notification_sent": a.notification_sent,
            "acknowledged_at": a.acknowledged_at.isoformat() if a.acknowledged_at else None,
            "resolution_notes": a.resolution_notes, "created_at": a.created_at.isoformat(),
        }

    async def detect_anomalies(self, tenant_id: uuid.UUID) -> dict:
        """Run anomaly detection for a tenant. Called by Celery beat."""
        detected = []
        try:
            from app.engines.platform_commerce.models import CommissionRecord
            r = await self.db.execute(select(func.count(CommissionRecord.id)).where(
                CommissionRecord.tenant_id == tenant_id,
                CommissionRecord.deducted_at >= utcnow() - timedelta(days=7)))
            recent_jobs = r.scalar_one_or_none() or 0
            if recent_jobs == 0:
                a = AnomalyRecord(
                    tenant_id=tenant_id, anomaly_type=AnomalyType.COMPLETION_DROP,
                    severity="high", description="No jobs completed in the last 7 days.",
                    detected_value=0.0, threshold_value=1.0,
                    context={"lookback_days": 7, "job_count": 0},
                )
                self.db.add(a); detected.append(AnomalyType.COMPLETION_DROP)
        except Exception:
            pass
        await self.db.flush()
        return {"tenant_id": str(tenant_id), "anomalies_detected": len(detected),
                "types": detected, "scan_at": utcnow().isoformat()}

    # ── Model Management (3 methods) ──────────────────────────────────────────
    async def get_model_versions(self, model_type: str | None) -> dict:
        q = select(ModelVersion).order_by(ModelVersion.training_date.desc())
        if model_type: q = q.where(ModelVersion.model_type == model_type)
        r = await self.db.execute(q.limit(50))
        items = r.scalars().all()
        return {
            "versions": [{
                "version_id": str(v.id), "model_type": v.model_type,
                "version": v.version, "is_active": v.is_active,
                "training_date": v.training_date.isoformat(),
                "training_rows": v.training_rows, "metrics": v.metrics,
            } for v in items],
        }

    async def trigger_retrain(self, model_type: str) -> dict:
        import secrets
        version = f"v{utcnow().strftime('%Y%m%d')}-{secrets.token_hex(3)}"
        mv = ModelVersion(
            model_type=model_type, version=version, is_active=False,
            training_rows=0, metrics={"status": "training"},
            trained_by="manual_trigger",
        )
        self.db.add(mv); await self.db.flush()
        return {"model_type": model_type, "version": version,
                "status": "training_queued",
                "message": "Training job queued in Celery. Poll GET /ds/models to check status."}

    async def get_business_performance(self, tenant_id: uuid.UUID, days: int = 30) -> dict:
        from app.engines.field_ops.models import Job, JobStatusHistory
        from app.engines.booking.models import Booking
        from app.engines.field_ops.constants import JS, JobType, TERMINAL_STATUSES
        from app.engines.auth.models import User

        cutoff = utcnow() - timedelta(days=days)
        tid = tenant_id

        # ── 1. Jobs by type ───────────────────────────────────────────────────
        type_rows = (await self.db.execute(
            select(Job.job_type, func.count(Job.id).label("cnt"))
            .where(Job.tenant_id == tid, Job.created_at >= cutoff)
            .group_by(Job.job_type)
        )).all()
        jobs_by_type = {r.job_type: r.cnt for r in type_rows}

        # ── 2. Consultation conversion rate ───────────────────────────────────
        # Numerator: consultations that spawned at least one child job
        conv_num_r = await self.db.execute(
            select(func.count(Job.id))
            .where(
                Job.tenant_id == tid,
                Job.job_type == JobType.CONSULTATION,
                Job.created_at >= cutoff,
                Job.id.in_(
                    select(Job.parent_job_id).where(
                        Job.tenant_id == tid,
                        Job.parent_job_id.isnot(None),
                    )
                ),
            )
        )
        conv_num = conv_num_r.scalar_one_or_none() or 0

        # Denominator: consultations that reached quote stage (approved or pending sign-off)
        conv_den_r = await self.db.execute(
            select(func.count(Job.id))
            .where(
                Job.tenant_id == tid,
                Job.job_type == JobType.CONSULTATION,
                Job.created_at >= cutoff,
                Job.status.in_([JS.QUOTE_APPROVED, JS.PENDING_SIGN_OFF, JS.CLOSED]),
            )
        )
        conv_den = conv_den_r.scalar_one_or_none() or 0
        consultation_conversion_rate = round(conv_num / conv_den, 4) if conv_den else None

        # ── 3. Average revenue per job type ──────────────────────────────────
        rev_rows = (await self.db.execute(
            select(Job.job_type, func.avg(Job.final_price).label("avg_rev"))
            .where(
                Job.tenant_id == tid,
                Job.status == JS.CLOSED,
                Job.final_price.isnot(None),
                Job.created_at >= cutoff,
            )
            .group_by(Job.job_type)
        )).all()
        avg_revenue_by_type = {r.job_type: round(float(r.avg_rev), 2) for r in rev_rows if r.avg_rev is not None}

        # ── 4. Repeat booking rate ────────────────────────────────────────────
        total_customers_r = await self.db.execute(
            select(func.count(func.distinct(Booking.customer_id)))
            .where(Booking.tenant_id == tid, Booking.created_at >= cutoff)
        )
        total_customers = total_customers_r.scalar_one_or_none() or 0

        repeat_customers_r = await self.db.execute(
            select(func.count(func.distinct(Booking.customer_id)))
            .where(
                Booking.tenant_id == tid,
                Booking.created_at >= cutoff,
                Booking.customer_id.in_(
                    select(Booking.customer_id)
                    .where(Booking.tenant_id == tid)
                    .group_by(Booking.customer_id)
                    .having(func.count(Booking.id) > 1)
                ),
            )
        )
        repeat_customers = repeat_customers_r.scalar_one_or_none() or 0
        repeat_booking_rate = round(repeat_customers / total_customers, 4) if total_customers else None

        # ── 5. Rework / quality-failure rate ─────────────────────────────────
        qc_jobs_r = await self.db.execute(
            select(func.count(func.distinct(JobStatusHistory.job_id)))
            .where(
                JobStatusHistory.tenant_id == tid,
                JobStatusHistory.to_status == JS.QUALITY_CHECK,
            )
        )
        qc_jobs = qc_jobs_r.scalar_one_or_none() or 0

        failed_jobs_r = await self.db.execute(
            select(func.count(func.distinct(JobStatusHistory.job_id)))
            .where(
                JobStatusHistory.tenant_id == tid,
                JobStatusHistory.to_status.in_([JS.QUALITY_FAILED, JS.REWORK_REQUIRED]),
            )
        )
        failed_jobs = failed_jobs_r.scalar_one_or_none() or 0
        rework_rate = round(failed_jobs / qc_jobs, 4) if qc_jobs else None

        # ── 6. SLA breach rate ───────────────────────────────────────────────
        total_jobs_r = await self.db.execute(
            select(func.count(Job.id))
            .where(Job.tenant_id == tid, Job.created_at >= cutoff)
        )
        total_jobs = total_jobs_r.scalar_one_or_none() or 0

        breach_jobs_r = await self.db.execute(
            select(func.count(Job.id))
            .where(Job.tenant_id == tid, Job.created_at >= cutoff, Job.sla_breach.is_(True))
        )
        breach_jobs = breach_jobs_r.scalar_one_or_none() or 0
        sla_breach_rate = round(breach_jobs / total_jobs, 4) if total_jobs else None

        # ── 7. Staff performance summary ─────────────────────────────────────
        staff_rows = (await self.db.execute(
            select(
                StaffPerformanceScore.staff_id,
                StaffPerformanceScore.composite_score,
                StaffPerformanceScore.jobs_completed,
                StaffPerformanceScore.avg_customer_rating,
                StaffPerformanceScore.computed_at,
            )
            .join(User, User.id == StaffPerformanceScore.staff_id)
            .where(StaffPerformanceScore.tenant_id == tid, User.tenant_id == tid)
            .order_by(StaffPerformanceScore.composite_score.desc())
            .limit(10)
        )).all()

        staff_name_ids = [r.staff_id for r in staff_rows]
        name_map: dict[uuid.UUID, str] = {}
        if staff_name_ids:
            name_rows = (await self.db.execute(
                select(User.id, User.full_name).where(User.id.in_(staff_name_ids))
            )).all()
            name_map = {r.id: r.full_name for r in name_rows}

        staff_performance = [
            {
                "staff_id": str(r.staff_id),
                "name": name_map.get(r.staff_id, "Unknown"),
                "score": float(r.composite_score) if r.composite_score is not None else None,
                "jobs_completed": r.jobs_completed,
                "avg_rating": float(r.avg_customer_rating) if r.avg_customer_rating is not None else None,
                "computed_at": r.computed_at.isoformat() if r.computed_at else None,
            }
            for r in staff_rows
        ]

        return {
            "period_days": days,
            "jobs_by_type": jobs_by_type,
            "consultation_conversion_rate": consultation_conversion_rate,
            "avg_revenue_by_type": avg_revenue_by_type,
            "repeat_booking_rate": repeat_booking_rate,
            "rework_quality_failure_rate": rework_rate,
            "sla_breach_rate": sla_breach_rate,
            "total_jobs": total_jobs,
            "sla_breaches": breach_jobs,
            "top_staff": staff_performance,
            "generated_at": utcnow().isoformat(),
        }

    async def get_platform_summary(self) -> dict:
        churn_r = await self.db.execute(select(func.count(ChurnSignal.id)).where(
            ChurnSignal.churn_band.in_(["high","critical"])))
        at_risk = churn_r.scalar_one_or_none() or 0

        anom_r = await self.db.execute(select(func.count(AnomalyRecord.id)).where(
            AnomalyRecord.status == "open"))
        open_anomalies = anom_r.scalar_one_or_none() or 0

        pred_r = await self.db.execute(select(func.count(PredictionRecord.id)))
        total_preds = pred_r.scalar_one_or_none() or 0

        return {
            "tenants_at_risk": at_risk, "open_anomalies": open_anomalies,
            "total_predictions_computed": total_preds,
            "models_active": 0, "generated_at": utcnow().isoformat(),
        }
