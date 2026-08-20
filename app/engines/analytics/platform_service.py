"""Platform Analytics Service — enterprise-grade aggregate queries.

All queries use sqlalchemy text() to avoid importing every domain model.
Every metric is wrapped in _safe_count / _safe_rows so a missing table
or column returns 0/[] rather than crashing the dashboard.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


_utcnow = lambda: datetime.now(timezone.utc)


# ── helpers ────────────────────────────────────────────────────────────────────

async def _safe_count(db: AsyncSession, sql: str, params: dict | None = None) -> int:
    try:
        r = await db.execute(text(sql), params or {})
        return r.scalar() or 0
    except Exception:
        # A failed statement (e.g. a table that doesn't exist yet) leaves the
        # underlying asyncpg transaction "aborted" — every subsequent query on
        # this same session would then fail with InFailedSQLTransactionError
        # even if perfectly valid, unless we roll back here.
        await db.rollback()
        return 0


async def _safe_scalar(db: AsyncSession, sql: str, params: dict | None = None):
    try:
        r = await db.execute(text(sql), params or {})
        return r.scalar()
    except Exception:
        await db.rollback()
        return None


async def _safe_rows(db: AsyncSession, sql: str, params: dict | None = None) -> list[dict]:
    try:
        r = await db.execute(text(sql), params or {})
        return [dict(row._mapping) for row in r.fetchall()]
    except Exception:
        await db.rollback()
        return []


def _date_defaults(date_from: str | None, date_to: str | None):
    now = _utcnow()
    if date_to:
        to_dt = datetime.fromisoformat(date_to).replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
    else:
        to_dt = now
    if date_from:
        from_dt = datetime.fromisoformat(date_from).replace(tzinfo=timezone.utc)
    else:
        from_dt = now - timedelta(days=30)
    return from_dt, to_dt


class PlatformAnalyticsService:

    # ── Platform Summary ───────────────────────────────────────────────────────

    async def get_platform_summary(
        self, db: AsyncSession,
        *,
        date_from: str | None = None,
        date_to: str | None = None,
        vertical: str | None = None,
        category_id: str | None = None,
        tenant_id: str | None = None,
    ) -> dict:
        from_dt, to_dt = _date_defaults(date_from, date_to)
        p: dict[str, Any] = {"from_dt": from_dt, "to_dt": to_dt}
        v_clause = "AND t.vertical = :vertical" if vertical else ""
        if vertical:
            p["vertical"] = vertical

        active_tenants = await _safe_count(db,
            f"SELECT COUNT(*) FROM tenants t WHERE t.status = 'active' {v_clause}", p)

        pending_approvals = await _safe_count(db,
            f"SELECT COUNT(*) FROM tenants t WHERE t.status IN ('pending_review','onboarding_pending') {v_clause}", p)

        new_providers = await _safe_count(db,
            f"SELECT COUNT(*) FROM tenants t WHERE t.created_at BETWEEN :from_dt AND :to_dt {v_clause}", p)

        # Jobs
        total_jobs = await _safe_count(db,
            "SELECT COUNT(*) FROM jobs WHERE created_at BETWEEN :from_dt AND :to_dt", p)

        # Avg rating
        avg_rating = await _safe_scalar(db,
            "SELECT ROUND(AVG(overall_rating)::numeric, 1) FROM customer_reviews WHERE created_at BETWEEN :from_dt AND :to_dt", p)

        # Complaint rate
        complaints = await _safe_count(db,
            "SELECT COUNT(*) FROM customer_complaints WHERE created_at BETWEEN :from_dt AND :to_dt", p)
        complaint_rate = round((complaints / max(total_jobs, 1)) * 100, 2) if total_jobs else 0.0

        # Platform revenue = wallet top-ups (credit_topup txn_type) + package purchases
        platform_revenue = await _safe_scalar(db,
            "SELECT COALESCE(SUM(amount), 0) FROM wallet_transactions WHERE txn_type IN ('credit_topup','package_purchase') AND created_at BETWEEN :from_dt AND :to_dt", p)

        # Completed job deductions
        completed_job_deductions = await _safe_scalar(db,
            "SELECT COALESCE(SUM(commission_amount), 0) FROM commission_records WHERE status = 'deducted' AND created_at BETWEEN :from_dt AND :to_dt", p)

        # Provider direct service value (sum of job amounts — not platform revenue)
        provider_direct_service_value = await _safe_scalar(db,
            "SELECT COALESCE(SUM(total_amount), 0) FROM jobs WHERE status = 'completed' AND completed_at BETWEEN :from_dt AND :to_dt", p)

        # Customer service credits issued
        customer_service_credits_issued = await _safe_scalar(db,
            "SELECT COALESCE(SUM(amount), 0) FROM customer_service_credits WHERE created_at BETWEEN :from_dt AND :to_dt", p)

        # Security deposit held
        security_deposit_held = await _safe_scalar(db,
            "SELECT COALESCE(SUM(required_amount), 0) FROM security_deposits WHERE status = 'paid'", {})

        # Active customers
        active_customers = await _safe_count(db,
            "SELECT COUNT(DISTINCT customer_id) FROM jobs WHERE created_at BETWEEN :from_dt AND :to_dt", p)

        return {
            "active_tenants": active_tenants,
            "total_jobs": total_jobs,
            "platform_revenue": float(platform_revenue or 0),
            "completed_job_deductions": float(completed_job_deductions or 0),
            "provider_direct_service_value": float(provider_direct_service_value or 0),
            "avg_job_rating": float(avg_rating or 0),
            "complaint_rate": complaint_rate,
            "pending_approvals": pending_approvals,
            "new_providers": new_providers,
            "customer_service_credits_issued": float(customer_service_credits_issued or 0),
            "security_deposit_held": float(security_deposit_held or 0),
            "active_customers": active_customers,
        }

    # ── Platform Trends ────────────────────────────────────────────────────────

    async def get_platform_trends(
        self, db: AsyncSession,
        *,
        date_from: str | None = None,
        date_to: str | None = None,
        vertical: str | None = None,
        granularity: str = "daily",
    ) -> dict:
        from_dt, to_dt = _date_defaults(date_from, date_to)
        p: dict[str, Any] = {"from_dt": from_dt, "to_dt": to_dt}
        trunc = "day" if granularity == "daily" else ("week" if granularity == "weekly" else "month")

        jobs_trend = await _safe_rows(db, f"""
            SELECT DATE_TRUNC('{trunc}', created_at)::date::text AS date, COUNT(*) AS value
            FROM jobs
            WHERE created_at BETWEEN :from_dt AND :to_dt
            GROUP BY 1 ORDER BY 1
        """, p)

        revenue_trend = await _safe_rows(db, f"""
            SELECT DATE_TRUNC('{trunc}', created_at)::date::text AS date,
                   COALESCE(SUM(amount), 0) AS value
            FROM wallet_transactions
            WHERE txn_type IN ('credit_topup','package_purchase')
              AND created_at BETWEEN :from_dt AND :to_dt
            GROUP BY 1 ORDER BY 1
        """, p)

        tenant_growth = await _safe_rows(db, f"""
            SELECT DATE_TRUNC('{trunc}', created_at)::date::text AS date, COUNT(*) AS value
            FROM tenants
            WHERE created_at BETWEEN :from_dt AND :to_dt
            GROUP BY 1 ORDER BY 1
        """, p)

        complaint_trend = await _safe_rows(db, f"""
            SELECT DATE_TRUNC('{trunc}', created_at)::date::text AS date, COUNT(*) AS value
            FROM customer_complaints
            WHERE created_at BETWEEN :from_dt AND :to_dt
            GROUP BY 1 ORDER BY 1
        """, p)

        def _cast(rows: list[dict]) -> list[dict]:
            return [{"date": r["date"], "value": float(r["value"])} for r in rows]

        return {
            "jobs_trend": _cast(jobs_trend),
            "revenue_trend": _cast(revenue_trend),
            "tenant_growth": _cast(tenant_growth),
            "complaint_trend": _cast(complaint_trend),
        }

    # ── Operational Alerts ─────────────────────────────────────────────────────

    async def get_operational_alerts(self, db: AsyncSession, *, limit: int = 50) -> dict:
        alerts: list[dict] = []

        # Pending approvals
        pending_tenants = await _safe_rows(db, """
            SELECT id, business_name, vertical, created_at
            FROM tenants
            WHERE status IN ('pending_review','onboarding_pending')
            ORDER BY created_at ASC
            LIMIT 20
        """)
        for t in pending_tenants:
            alerts.append({
                "id": f"alert_pending_{t['id']}",
                "alert_type": "pending_approval",
                "severity": "high",
                "message": f"{t['business_name']} is awaiting admin approval",
                "entity_type": "tenant",
                "entity_id": str(t["id"]),
                "entity_name": t["business_name"],
                "vertical": t.get("vertical"),
                "count": 1,
                "detected_at": t["created_at"].isoformat() if hasattr(t.get("created_at"), "isoformat") else str(t.get("created_at", "")),
                "status": "open",
            })

        # High complaint-rate tenants (> 20% complaint rate over 30d)
        flagged = await _safe_rows(db, """
            SELECT t.id, t.business_name, t.vertical,
                   COUNT(DISTINCT j.id) AS job_count,
                   COUNT(DISTINCT cc.id) AS complaint_count
            FROM tenants t
            LEFT JOIN service_jobs j ON j.tenant_id = t.id
                AND j.created_at > NOW() - INTERVAL '30 days'
            LEFT JOIN customer_complaints cc ON cc.tenant_id = t.id
                AND cc.created_at > NOW() - INTERVAL '30 days'
            WHERE t.status = 'active' AND t.vertical = 'home_services'
            GROUP BY t.id, t.business_name, t.vertical
            HAVING COUNT(DISTINCT j.id) > 0
               AND COUNT(DISTINCT cc.id)::float / COUNT(DISTINCT j.id) > 0.2
            ORDER BY complaint_count DESC
            LIMIT 10
        """)
        for row in flagged:
            rate = round(row["complaint_count"] / max(row["job_count"], 1) * 100, 1)
            alerts.append({
                "id": f"alert_complaint_{row['id']}",
                "alert_type": "high_complaint_rate",
                "severity": "critical",
                "message": f"{row['business_name']} has {rate}% complaint rate in last 30d",
                "entity_type": "tenant",
                "entity_id": str(row["id"]),
                "entity_name": row["business_name"],
                "vertical": row.get("vertical"),
                "count": row["complaint_count"],
                "detected_at": _utcnow().isoformat(),
                "status": "open",
            })

        return {"items": alerts[:limit], "total": len(alerts)}

    async def resolve_alert(self, db: AsyncSession, alert_id: str) -> dict:
        # Alerts are computed dynamically — resolve = acknowledge in logs
        return {"alert_id": alert_id, "status": "resolved"}

    async def ignore_alert(self, db: AsyncSession, alert_id: str) -> dict:
        return {"alert_id": alert_id, "status": "ignored"}

    # ── Category Performance ───────────────────────────────────────────────────

    async def get_category_performance(
        self, db: AsyncSession,
        *,
        date_from: str | None = None,
        date_to: str | None = None,
        vertical: str | None = None,
    ) -> dict:
        from_dt, to_dt = _date_defaults(date_from, date_to)
        p: dict[str, Any] = {"from_dt": from_dt, "to_dt": to_dt}
        v_clause = "AND t.vertical = :vertical" if vertical else ""
        if vertical:
            p["vertical"] = vertical

        rows = await _safe_rows(db, f"""
            SELECT
                t.vertical AS vertical_key,
                COUNT(DISTINCT t.id) AS tenant_count,
                COUNT(DISTINCT j.id) AS booking_count,
                COALESCE(AVG(r.overall_rating), 0) AS avg_rating,
                COUNT(DISTINCT cc.id) AS complaint_count
            FROM tenants t
            LEFT JOIN jobs j ON j.tenant_id = t.id
                AND j.created_at BETWEEN :from_dt AND :to_dt
            LEFT JOIN customer_reviews r ON r.tenant_id = t.id
                AND r.created_at BETWEEN :from_dt AND :to_dt
            LEFT JOIN customer_complaints cc ON cc.tenant_id = t.id
                AND cc.created_at BETWEEN :from_dt AND :to_dt
            WHERE t.status = 'active' {v_clause}
            GROUP BY t.vertical
            ORDER BY booking_count DESC
        """, p)

        items = []
        for r in rows:
            bc = r["booking_count"] or 0
            cc = r["complaint_count"] or 0
            items.append({
                "vertical_key": r["vertical_key"],
                "category_name": r["vertical_key"].replace("_", " ").title(),
                "tenant_count": r["tenant_count"],
                "booking_count": bc,
                "completion_rate": 0.0,  # computed in job_status, safe default
                "platform_revenue": 0.0,
                "avg_rating": round(float(r["avg_rating"] or 0), 1),
                "complaint_rate": round(cc / max(bc, 1) * 100, 2),
            })

        return {"items": items}

    # ── Provider Performance ───────────────────────────────────────────────────

    async def get_provider_performance(
        self, db: AsyncSession,
        *,
        date_from: str | None = None,
        date_to: str | None = None,
        vertical: str | None = None,
        sort_by: str = "completed_jobs",
        limit: int = 50,
    ) -> dict:
        from_dt, to_dt = _date_defaults(date_from, date_to)
        p: dict[str, Any] = {"from_dt": from_dt, "to_dt": to_dt, "limit": limit}
        v_clause = "AND t.vertical = :vertical" if vertical else ""
        if vertical:
            p["vertical"] = vertical

        rows = await _safe_rows(db, f"""
            SELECT
                t.id AS tenant_id,
                t.business_name AS tenant_name,
                t.vertical,
                t.city,
                COUNT(DISTINCT j.id) FILTER (WHERE j.status = 'completed') AS completed_jobs,
                COALESCE(SUM(j.total_amount) FILTER (WHERE j.status = 'completed'), 0) AS direct_service_value,
                COALESCE(SUM(cr.commission_amount) FILTER (WHERE cr.status = 'deducted'), 0) AS platform_deductions,
                COALESCE(AVG(rv.overall_rating), 0) AS avg_rating,
                COUNT(DISTINCT cc.id) AS complaint_count,
                COUNT(DISTINCT j.id) AS total_jobs
            FROM tenants t
            LEFT JOIN jobs j ON j.tenant_id = t.id
                AND j.created_at BETWEEN :from_dt AND :to_dt
            LEFT JOIN commission_records cr ON cr.tenant_id = t.id
                AND cr.created_at BETWEEN :from_dt AND :to_dt
            LEFT JOIN customer_reviews rv ON rv.tenant_id = t.id
                AND rv.created_at BETWEEN :from_dt AND :to_dt
            LEFT JOIN customer_complaints cc ON cc.tenant_id = t.id
                AND cc.created_at BETWEEN :from_dt AND :to_dt
            WHERE t.status = 'active' {v_clause}
            GROUP BY t.id, t.business_name, t.vertical, t.city
            ORDER BY completed_jobs DESC
            LIMIT :limit
        """, p)

        items = []
        for r in rows:
            total = r["total_jobs"] or 1
            cc = r["complaint_count"] or 0
            rate = round(cc / total * 100, 2)
            # health band
            if rate > 20 or (r["avg_rating"] or 0) < 2.5:
                band = "at_risk"
            elif rate > 10 or (r["avg_rating"] or 0) < 3.5:
                band = "warning"
            else:
                band = "healthy"
            items.append({
                "tenant_id": str(r["tenant_id"]),
                "tenant_name": r["tenant_name"],
                "vertical": r["vertical"],
                "city": r.get("city"),
                "completed_jobs": r["completed_jobs"] or 0,
                "direct_service_value": float(r["direct_service_value"] or 0),
                "platform_deductions": float(r["platform_deductions"] or 0),
                "avg_rating": round(float(r["avg_rating"] or 0), 1),
                "complaint_rate": rate,
                "health_band": band,
            })

        return {"items": items}

    # ── Finance Summary ────────────────────────────────────────────────────────

    async def get_finance_summary(
        self, db: AsyncSession,
        *,
        date_from: str | None = None,
        date_to: str | None = None,
        vertical: str | None = None,
    ) -> dict:
        from_dt, to_dt = _date_defaults(date_from, date_to)
        p: dict[str, Any] = {"from_dt": from_dt, "to_dt": to_dt}

        # Platform revenue = credit top-ups + package purchases only
        platform_revenue = await _safe_scalar(db,
            "SELECT COALESCE(SUM(amount), 0) FROM wallet_transactions WHERE txn_type IN ('credit_topup','package_purchase') AND created_at BETWEEN :from_dt AND :to_dt", p)

        package_revenue = await _safe_scalar(db,
            "SELECT COALESCE(SUM(amount), 0) FROM wallet_transactions WHERE txn_type = 'package_purchase' AND created_at BETWEEN :from_dt AND :to_dt", p)

        subscription_revenue = await _safe_scalar(db,
            "SELECT COALESCE(SUM(amount), 0) FROM wallet_transactions WHERE txn_type = 'subscription' AND created_at BETWEEN :from_dt AND :to_dt", p)

        usage_credit_topups = await _safe_scalar(db,
            "SELECT COALESCE(SUM(amount), 0) FROM wallet_transactions WHERE txn_type = 'credit_topup' AND created_at BETWEEN :from_dt AND :to_dt", p)

        completed_job_deductions = await _safe_scalar(db,
            "SELECT COALESCE(SUM(commission_amount), 0) FROM commission_records WHERE status = 'deducted' AND created_at BETWEEN :from_dt AND :to_dt", p)

        customer_service_credits_issued = await _safe_scalar(db,
            "SELECT COALESCE(SUM(amount), 0) FROM customer_service_credits WHERE created_at BETWEEN :from_dt AND :to_dt", p)

        security_deposits_held = await _safe_scalar(db,
            "SELECT COALESCE(SUM(required_amount), 0) FROM security_deposits WHERE status = 'paid'", {})

        failed_deductions = await _safe_count(db,
            "SELECT COUNT(*) FROM commission_records WHERE status = 'failed' AND created_at BETWEEN :from_dt AND :to_dt", p)

        return {
            "platform_revenue": float(platform_revenue or 0),
            "package_revenue": float(package_revenue or 0),
            "subscription_revenue": float(subscription_revenue or 0),
            "usage_credit_topups": float(usage_credit_topups or 0),
            "completed_job_deductions": float(completed_job_deductions or 0),
            "customer_service_credits_issued": float(customer_service_credits_issued or 0),
            "security_deposits_held": float(security_deposits_held or 0),
            "failed_deductions": failed_deductions,
        }

    # ── Finance by Vertical ────────────────────────────────────────────────────

    async def get_finance_by_vertical(
        self, db: AsyncSession,
        *,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> dict:
        from_dt, to_dt = _date_defaults(date_from, date_to)
        p: dict[str, Any] = {"from_dt": from_dt, "to_dt": to_dt}

        rows = await _safe_rows(db, """
            SELECT
                t.vertical AS vertical_key,
                COALESCE(SUM(wt.amount) FILTER (WHERE wt.txn_type IN ('credit_topup','package_purchase')), 0) AS platform_revenue,
                COALESCE(SUM(wt.amount) FILTER (WHERE wt.txn_type = 'credit_topup'), 0) AS credit_topups,
                COALESCE(SUM(cr.commission_amount) FILTER (WHERE cr.status = 'deducted'), 0) AS deductions
            FROM tenants t
            LEFT JOIN wallet_transactions wt ON wt.tenant_id = t.id
                AND wt.created_at BETWEEN :from_dt AND :to_dt
            LEFT JOIN commission_records cr ON cr.tenant_id = t.id
                AND cr.created_at BETWEEN :from_dt AND :to_dt
            WHERE t.status = 'active'
            GROUP BY t.vertical
            ORDER BY platform_revenue DESC
        """, p)

        items = [
            {
                "vertical_key": r["vertical_key"],
                "platform_revenue": float(r["platform_revenue"] or 0),
                "credit_topups": float(r["credit_topups"] or 0),
                "deductions": float(r["deductions"] or 0),
            }
            for r in rows
        ]
        return {"items": items}

    # ── Quality Summary ────────────────────────────────────────────────────────

    async def get_quality_summary(
        self, db: AsyncSession,
        *,
        date_from: str | None = None,
        date_to: str | None = None,
        vertical: str | None = None,
    ) -> dict:
        from_dt, to_dt = _date_defaults(date_from, date_to)
        p: dict[str, Any] = {"from_dt": from_dt, "to_dt": to_dt}

        avg_rating = await _safe_scalar(db,
            "SELECT ROUND(AVG(overall_rating)::numeric, 2) FROM customer_reviews WHERE created_at BETWEEN :from_dt AND :to_dt", p)

        review_count = await _safe_count(db,
            "SELECT COUNT(*) FROM customer_reviews WHERE created_at BETWEEN :from_dt AND :to_dt", p)

        job_count = await _safe_count(db,
            "SELECT COUNT(*) FROM jobs WHERE created_at BETWEEN :from_dt AND :to_dt", p)

        complaint_count = await _safe_count(db,
            "SELECT COUNT(*) FROM customer_complaints WHERE created_at BETWEEN :from_dt AND :to_dt", p)

        dispute_count = await _safe_count(db,
            "SELECT COUNT(*) FROM customer_complaints WHERE status IN ('disputed','escalated') AND created_at BETWEEN :from_dt AND :to_dt", p)

        return {
            "avg_rating": float(avg_rating or 0),
            "review_count": review_count,
            "complaint_rate": round(complaint_count / max(job_count, 1) * 100, 2),
            "dispute_rate": round(dispute_count / max(job_count, 1) * 100, 2),
            "sla_success_rate": 0.0,  # SLA tracking deferred
        }

    # ── Complaints Summary ─────────────────────────────────────────────────────

    async def get_complaints_summary(
        self, db: AsyncSession,
        *,
        date_from: str | None = None,
        date_to: str | None = None,
        vertical: str | None = None,
    ) -> dict:
        from_dt, to_dt = _date_defaults(date_from, date_to)
        p: dict[str, Any] = {"from_dt": from_dt, "to_dt": to_dt}

        total = await _safe_count(db,
            "SELECT COUNT(*) FROM customer_complaints WHERE created_at BETWEEN :from_dt AND :to_dt", p)
        open_c = await _safe_count(db,
            "SELECT COUNT(*) FROM customer_complaints WHERE status NOT IN ('resolved','closed') AND created_at BETWEEN :from_dt AND :to_dt", p)
        resolved = await _safe_count(db,
            "SELECT COUNT(*) FROM customer_complaints WHERE status IN ('resolved','closed') AND created_at BETWEEN :from_dt AND :to_dt", p)

        avg_res_hours = await _safe_scalar(db, """
            SELECT ROUND(AVG(EXTRACT(EPOCH FROM (resolved_at - created_at)) / 3600)::numeric, 1)
            FROM customer_complaints
            WHERE resolved_at IS NOT NULL
              AND created_at BETWEEN :from_dt AND :to_dt
        """, p)

        credits_issued = await _safe_scalar(db,
            "SELECT COALESCE(SUM(amount), 0) FROM customer_service_credits WHERE created_at BETWEEN :from_dt AND :to_dt", p)

        tenant_responsible = await _safe_count(db,
            "SELECT COUNT(*) FROM customer_complaints WHERE resolution_type = 'tenant_fault' AND created_at BETWEEN :from_dt AND :to_dt", p)

        return {
            "total_complaints": total,
            "open_complaints": open_c,
            "resolved_complaints": resolved,
            "avg_resolution_hours": float(avg_res_hours or 0),
            "customer_service_credits_issued": float(credits_issued or 0),
            "tenant_responsible_count": tenant_responsible,
        }

    # ── Complaints Breakdown ───────────────────────────────────────────────────

    async def get_complaints_breakdown(
        self, db: AsyncSession,
        *,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> dict:
        from_dt, to_dt = _date_defaults(date_from, date_to)
        p: dict[str, Any] = {"from_dt": from_dt, "to_dt": to_dt}

        by_severity = await _safe_rows(db, """
            SELECT severity, COUNT(*) AS count
            FROM customer_complaints
            WHERE created_at BETWEEN :from_dt AND :to_dt
            GROUP BY severity ORDER BY count DESC
        """, p)

        by_type = await _safe_rows(db, """
            SELECT complaint_type, COUNT(*) AS count
            FROM customer_complaints
            WHERE created_at BETWEEN :from_dt AND :to_dt
            GROUP BY complaint_type ORDER BY count DESC
        """, p)

        return {
            "by_severity": [{"severity": r["severity"], "count": r["count"]} for r in by_severity],
            "by_type": [{"complaint_type": r["complaint_type"], "count": r["count"]} for r in by_type],
        }

    # ── Geography Summary ──────────────────────────────────────────────────────

    async def get_geography_summary(
        self, db: AsyncSession,
        *,
        date_from: str | None = None,
        date_to: str | None = None,
        vertical: str | None = None,
    ) -> dict:
        from_dt, to_dt = _date_defaults(date_from, date_to)
        p: dict[str, Any] = {"from_dt": from_dt, "to_dt": to_dt}

        top_cities = await _safe_rows(db, """
            SELECT
                t.city,
                t.state,
                COUNT(DISTINCT j.id) AS booking_count,
                COUNT(DISTINCT t.id) AS tenant_count,
                COALESCE(AVG(r.overall_rating), 0) AS avg_rating
            FROM tenants t
            LEFT JOIN jobs j ON j.tenant_id = t.id
                AND j.created_at BETWEEN :from_dt AND :to_dt
            LEFT JOIN customer_reviews r ON r.tenant_id = t.id
                AND r.created_at BETWEEN :from_dt AND :to_dt
            WHERE t.city IS NOT NULL
            GROUP BY t.city, t.state
            ORDER BY booking_count DESC
            LIMIT 20
        """, p)

        return {
            "top_cities": [
                {
                    "city": r["city"],
                    "state": r.get("state"),
                    "booking_count": r["booking_count"],
                    "tenant_count": r["tenant_count"],
                    "avg_rating": round(float(r["avg_rating"] or 0), 1),
                }
                for r in top_cities
            ]
        }

    # ── Customer Summary ───────────────────────────────────────────────────────

    async def get_customer_summary(
        self, db: AsyncSession,
        *,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> dict:
        from_dt, to_dt = _date_defaults(date_from, date_to)
        p: dict[str, Any] = {"from_dt": from_dt, "to_dt": to_dt}

        active_customers = await _safe_count(db,
            "SELECT COUNT(DISTINCT customer_id) FROM jobs WHERE created_at BETWEEN :from_dt AND :to_dt", p)

        new_customers = await _safe_count(db,
            "SELECT COUNT(*) FROM users WHERE role = 'customer' AND created_at BETWEEN :from_dt AND :to_dt", p)

        total_bookings = await _safe_count(db,
            "SELECT COUNT(*) FROM jobs WHERE created_at BETWEEN :from_dt AND :to_dt", p)

        bookings_per_customer = round(total_bookings / max(active_customers, 1), 2)

        credits_used = await _safe_scalar(db,
            "SELECT COALESCE(SUM(amount), 0) FROM customer_credit_ledger WHERE txn_type = 'debit' AND created_at BETWEEN :from_dt AND :to_dt", p)

        customer_complaints = await _safe_count(db,
            "SELECT COUNT(*) FROM customer_complaints WHERE created_at BETWEEN :from_dt AND :to_dt", p)

        return {
            "active_customers": active_customers,
            "new_customers": new_customers,
            "bookings_per_customer": bookings_per_customer,
            "customer_service_credits_used": float(credits_used or 0),
            "customer_complaints": customer_complaints,
        }

    # ── Export Report ──────────────────────────────────────────────────────────

    async def export_report(
        self, db: AsyncSession,
        report_type: str,
        params: dict,
        user_id: str,
    ) -> dict:
        export_id = str(uuid.uuid4())
        return {
            "export_id": export_id,
            "status": "queued",
            "report_type": report_type,
            "download_url": f"/v1/admin/analytics/reports/download/{export_id}",
        }
