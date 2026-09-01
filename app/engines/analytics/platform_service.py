"""Platform Analytics Service — enterprise-grade aggregate queries.

All queries use sqlalchemy text() to avoid importing every domain model.
Every metric is wrapped in _safe_count / _safe_rows so a missing table
or column returns 0/[] rather than crashing the dashboard.
"""
from __future__ import annotations

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

        # Canonical field-operations jobs.  The generic `jobs` table is a
        # retired pre-Home-Services projection and is intentionally empty.
        total_jobs = await _safe_count(db,
            f"SELECT COUNT(*) FROM service_jobs sj JOIN tenants t ON t.id=sj.tenant_id "
            f"WHERE sj.created_at BETWEEN :from_dt AND :to_dt {v_clause}", p)

        # Avg rating
        avg_rating = await _safe_scalar(db,
            f"SELECT ROUND(AVG(cr.overall_rating)::numeric, 1) "
            f"FROM customer_reviews cr JOIN tenants t ON t.id=cr.tenant_id "
            f"WHERE cr.created_at BETWEEN :from_dt AND :to_dt {v_clause}", p)

        # Complaint rate
        complaints = await _safe_count(db,
            f"SELECT COUNT(*) FROM customer_complaints cc "
            f"JOIN tenants t ON t.id=cc.tenant_id "
            f"WHERE cc.created_at BETWEEN :from_dt AND :to_dt {v_clause}", p)
        complaint_rate = round((complaints / max(total_jobs, 1)) * 100, 2) if total_jobs else 0.0

        # Platform cash receipts are usage-credit top-ups only. Packages and
        # subscriptions were retired; provider service payments remain direct.
        platform_revenue = await _safe_scalar(db,
            f"SELECT COALESCE(SUM(cto.amount_paid-COALESCE(cto.refunded_amount,0)),0) "
            f"FROM credit_topup_orders cto JOIN tenants t ON t.id=cto.tenant_id "
            f"WHERE cto.payment_status IN ('credited','partially_refunded') "
            f"AND cto.created_at BETWEEN :from_dt AND :to_dt {v_clause}", p)

        # Completed job deductions
        completed_job_deductions = await _safe_scalar(db,
            f"SELECT COALESCE(SUM(-ucl.credit_delta),0) FROM usage_credit_ledger ucl "
            f"JOIN tenants t ON t.id=ucl.tenant_id WHERE ucl.event_type IN "
            f"('completed_job_deduction','customer_platform_charge_recovery') "
            f"AND ucl.created_at BETWEEN :from_dt AND :to_dt {v_clause}", p)

        # Provider direct service value (sum of job amounts — not platform revenue)
        provider_direct_service_value = await _safe_scalar(db,
            f"SELECT COALESCE(SUM(si.total_amount),0) FROM service_invoices si "
            f"JOIN tenants t ON t.id=si.tenant_id WHERE si.status <> 'cancelled' "
            f"AND si.payment_status IN ('collected','verified','paid') "
            f"AND si.created_at BETWEEN :from_dt AND :to_dt {v_clause}", p)

        # Customer service credits issued
        customer_service_credits_issued = await _safe_scalar(db,
            f"SELECT COALESCE(SUM(csc.amount),0) FROM customer_service_credits csc "
            f"LEFT JOIN tenants t ON t.id=csc.tenant_id "
            f"WHERE csc.created_at BETWEEN :from_dt AND :to_dt {v_clause}", p)

        # Active customers
        active_customers = await _safe_count(db,
            f"SELECT COUNT(DISTINCT sj.customer_id) FROM service_jobs sj "
            f"JOIN tenants t ON t.id=sj.tenant_id "
            f"WHERE sj.created_at BETWEEN :from_dt AND :to_dt {v_clause}", p)

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
            "security_deposit_held": 0.0,
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
        v_clause = "AND t.vertical = :vertical" if vertical else ""
        if vertical:
            p["vertical"] = vertical

        jobs_trend = await _safe_rows(db, f"""
            SELECT DATE_TRUNC('{trunc}', created_at)::date::text AS date, COUNT(*) AS value
            FROM service_jobs sj JOIN tenants t ON t.id=sj.tenant_id
            WHERE sj.created_at BETWEEN :from_dt AND :to_dt {v_clause}
            GROUP BY 1 ORDER BY 1
        """, p)

        revenue_trend = await _safe_rows(db, f"""
            SELECT DATE_TRUNC('{trunc}', cto.created_at)::date::text AS date,
                   COALESCE(SUM(cto.amount_paid-COALESCE(cto.refunded_amount,0)), 0) AS value
            FROM credit_topup_orders cto JOIN tenants t ON t.id=cto.tenant_id
            WHERE cto.payment_status IN ('credited','partially_refunded')
              AND cto.created_at BETWEEN :from_dt AND :to_dt {v_clause}
            GROUP BY 1 ORDER BY 1
        """, p)

        tenant_growth = await _safe_rows(db, f"""
            SELECT DATE_TRUNC('{trunc}', t.created_at)::date::text AS date, COUNT(*) AS value
            FROM tenants t
            WHERE t.created_at BETWEEN :from_dt AND :to_dt {v_clause}
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
            WITH job_metrics AS (
              SELECT tenant_id,
                     COUNT(*) AS booking_count,
                     COUNT(*) FILTER (WHERE status='completed') AS completed_count
              FROM service_jobs
              WHERE created_at BETWEEN :from_dt AND :to_dt
              GROUP BY tenant_id
            ), review_metrics AS (
              SELECT tenant_id, AVG(overall_rating) AS avg_rating
              FROM customer_reviews
              WHERE created_at BETWEEN :from_dt AND :to_dt
              GROUP BY tenant_id
            ), complaint_metrics AS (
              SELECT tenant_id, COUNT(*) AS complaint_count
              FROM customer_complaints
              WHERE created_at BETWEEN :from_dt AND :to_dt
              GROUP BY tenant_id
            ), topup_metrics AS (
              SELECT tenant_id,
                     SUM(amount_paid-COALESCE(refunded_amount,0)) AS platform_revenue
              FROM credit_topup_orders
              WHERE payment_status IN ('credited','partially_refunded')
                AND created_at BETWEEN :from_dt AND :to_dt
              GROUP BY tenant_id
            )
            SELECT
                t.vertical AS vertical_key,
                COUNT(*) AS tenant_count,
                COALESCE(SUM(jm.booking_count),0) AS booking_count,
                COALESCE(SUM(jm.completed_count),0) AS completed_count,
                COALESCE(AVG(rm.avg_rating) FILTER (WHERE rm.avg_rating IS NOT NULL),0) AS avg_rating,
                COALESCE(SUM(cm.complaint_count),0) AS complaint_count,
                COALESCE(SUM(tm.platform_revenue),0) AS platform_revenue
            FROM tenants t
            LEFT JOIN job_metrics jm ON jm.tenant_id=t.id
            LEFT JOIN review_metrics rm ON rm.tenant_id=t.id
            LEFT JOIN complaint_metrics cm ON cm.tenant_id=t.id
            LEFT JOIN topup_metrics tm ON tm.tenant_id=t.id
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
                "tenant_count": int(r["tenant_count"] or 0),
                "booking_count": int(bc),
                "completion_rate": round(float(r["completed_count"] or 0) / max(float(bc), 1.0) * 100, 2),
                "platform_revenue": float(r["platform_revenue"] or 0),
                "avg_rating": round(float(r["avg_rating"] or 0), 1),
                "complaint_rate": round(float(cc) / max(float(bc), 1.0) * 100, 2),
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
        health_band: str | None = None,
        limit: int = 50,
    ) -> dict:
        from_dt, to_dt = _date_defaults(date_from, date_to)
        p: dict[str, Any] = {"from_dt": from_dt, "to_dt": to_dt, "limit": limit}
        v_clause = "AND t.vertical = :vertical" if vertical else ""
        if vertical:
            p["vertical"] = vertical
        health_clause = "WHERE health_band=:health_band" if health_band else ""
        if health_band:
            p["health_band"] = health_band
        order_by = {
            "completed_jobs": "completed_jobs DESC",
            "direct_service_value": "direct_service_value DESC",
            "platform_deductions": "platform_deductions DESC",
            "avg_rating": "avg_rating DESC",
            "complaint_count": "complaint_count DESC",
        }.get(sort_by, "completed_jobs DESC")

        rows = await _safe_rows(db, f"""
            WITH job_metrics AS (
              SELECT tenant_id,
                     COUNT(*) AS total_jobs,
                     COUNT(*) FILTER (WHERE status='completed') AS completed_jobs
              FROM service_jobs
              WHERE created_at BETWEEN :from_dt AND :to_dt
              GROUP BY tenant_id
            ), invoice_metrics AS (
              SELECT tenant_id, COALESCE(SUM(total_amount),0) AS direct_service_value
              FROM service_invoices
              WHERE status <> 'cancelled'
                AND payment_status IN ('collected','verified','paid')
                AND created_at BETWEEN :from_dt AND :to_dt
              GROUP BY tenant_id
            ), deduction_metrics AS (
              SELECT tenant_id, COALESCE(SUM(-credit_delta),0) AS platform_deductions
              FROM usage_credit_ledger
              WHERE event_type IN ('completed_job_deduction','customer_platform_charge_recovery')
                AND created_at BETWEEN :from_dt AND :to_dt
              GROUP BY tenant_id
            ), review_metrics AS (
              SELECT tenant_id,
                     COALESCE(AVG(overall_rating),0) AS avg_rating,
                     COUNT(*) AS review_count
              FROM customer_reviews
              WHERE created_at BETWEEN :from_dt AND :to_dt
              GROUP BY tenant_id
            ), complaint_metrics AS (
              SELECT tenant_id, COUNT(*) AS complaint_count
              FROM customer_complaints
              WHERE created_at BETWEEN :from_dt AND :to_dt
              GROUP BY tenant_id
            ), provider_metrics AS (
              SELECT
                t.id AS tenant_id,
                t.business_name AS tenant_name,
                t.vertical,
                t.city,
                COALESCE(jm.completed_jobs,0) AS completed_jobs,
                COALESCE(im.direct_service_value,0) AS direct_service_value,
                COALESCE(dm.platform_deductions,0) AS platform_deductions,
                COALESCE(rm.avg_rating,0) AS avg_rating,
                COALESCE(rm.review_count,0) AS review_count,
                COALESCE(cm.complaint_count,0) AS complaint_count,
                COALESCE(jm.total_jobs,0) AS total_jobs
              FROM tenants t
              LEFT JOIN job_metrics jm ON jm.tenant_id=t.id
              LEFT JOIN invoice_metrics im ON im.tenant_id=t.id
              LEFT JOIN deduction_metrics dm ON dm.tenant_id=t.id
              LEFT JOIN review_metrics rm ON rm.tenant_id=t.id
              LEFT JOIN complaint_metrics cm ON cm.tenant_id=t.id
              WHERE t.status='active' {v_clause}
            ), scored AS (
              SELECT *,
                CASE
                  WHEN (CASE WHEN total_jobs>0 THEN complaint_count*100.0/total_jobs ELSE 0 END)>20
                    OR (review_count>0 AND avg_rating<2.5) THEN 'at_risk'
                  WHEN (CASE WHEN total_jobs>0 THEN complaint_count*100.0/total_jobs ELSE 0 END)>10
                    OR (review_count>0 AND avg_rating<3.5) THEN 'warning'
                  WHEN review_count=0 THEN 'not_enough_data'
                  ELSE 'healthy'
                END AS health_band
              FROM provider_metrics
            )
            SELECT * FROM scored
            {health_clause}
            ORDER BY {order_by}, tenant_name ASC
            LIMIT :limit
        """, p)

        items = []
        for r in rows:
            total = r["total_jobs"] or 0
            cc = r["complaint_count"] or 0
            review_count = r["review_count"] or 0
            rate = round(cc / max(total, 1) * 100, 2)
            items.append({
                "tenant_id": str(r["tenant_id"]),
                "tenant_name": r["tenant_name"],
                "vertical": r["vertical"],
                "city": r.get("city"),
                "completed_jobs": r["completed_jobs"] or 0,
                "direct_service_value": float(r["direct_service_value"] or 0),
                "platform_deductions": float(r["platform_deductions"] or 0),
                "avg_rating": round(float(r["avg_rating"] or 0), 1),
                "review_count": review_count,
                "complaint_rate": rate,
                "health_band": r["health_band"],
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
        if vertical:
            p["vertical"] = vertical

        def tenant_filter(alias: str) -> str:
            return (
                f"AND EXISTS (SELECT 1 FROM tenants t "
                f"WHERE t.id={alias}.tenant_id AND t.vertical=:vertical)"
                if vertical else ""
            )

        usage_credit_topups = await _safe_scalar(db, f"""
            SELECT COALESCE(SUM(amount_paid-COALESCE(refunded_amount,0)),0)
            FROM credit_topup_orders cto
            WHERE cto.payment_status IN ('credited','partially_refunded')
              AND cto.created_at BETWEEN :from_dt AND :to_dt
              {tenant_filter('cto')}
        """, p)

        completed_job_deductions = await _safe_scalar(db, f"""
            SELECT COALESCE(SUM(-credit_delta),0)
            FROM usage_credit_ledger ucl
            WHERE ucl.event_type IN ('completed_job_deduction','customer_platform_charge_recovery')
              AND ucl.created_at BETWEEN :from_dt AND :to_dt
              {tenant_filter('ucl')}
        """, p)

        provider_direct_service_value = await _safe_scalar(db, f"""
            SELECT COALESCE(SUM(total_amount),0)
            FROM service_invoices si
            WHERE si.status <> 'cancelled'
              AND si.payment_status IN ('collected','verified','paid')
              AND si.created_at BETWEEN :from_dt AND :to_dt
              {tenant_filter('si')}
        """, p)

        customer_service_credits_issued = await _safe_scalar(db, f"""
            SELECT COALESCE(SUM(csc.amount),0)
            FROM customer_service_credits csc
            WHERE csc.created_at BETWEEN :from_dt AND :to_dt
              {tenant_filter('csc')}
        """, p)

        failed_deductions = await _safe_count(db, f"""
            SELECT COUNT(*) FROM service_jobs sj
            LEFT JOIN usage_credit_ledger ucl
              ON ucl.job_id=sj.id AND ucl.event_type='completed_job_deduction'
            WHERE sj.status='completed' AND sj.updated_at BETWEEN :from_dt AND :to_dt
              AND ucl.id IS NULL
              {tenant_filter('sj')}
        """, p)

        return {
            "platform_revenue": float(usage_credit_topups or 0),
            "usage_credit_topups": float(usage_credit_topups or 0),
            "completed_job_deductions": float(completed_job_deductions or 0),
            "provider_direct_service_value": float(provider_direct_service_value or 0),
            "customer_service_credits_issued": float(customer_service_credits_issued or 0),
            "security_deposits_held": 0.0,
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
            WITH topups AS (
              SELECT tenant_id,
                     COALESCE(SUM(amount_paid-COALESCE(refunded_amount,0)),0) AS credit_topups
              FROM credit_topup_orders
              WHERE payment_status IN ('credited','partially_refunded')
                AND created_at BETWEEN :from_dt AND :to_dt
              GROUP BY tenant_id
            ), deductions AS (
              SELECT tenant_id, COALESCE(SUM(-credit_delta),0) AS deductions
              FROM usage_credit_ledger
              WHERE event_type IN ('completed_job_deduction','customer_platform_charge_recovery')
                AND created_at BETWEEN :from_dt AND :to_dt
              GROUP BY tenant_id
            )
            SELECT
                t.vertical AS vertical_key,
                COALESCE(SUM(tu.credit_topups),0) AS platform_revenue,
                COALESCE(SUM(tu.credit_topups),0) AS credit_topups,
                COALESCE(SUM(d.deductions),0) AS deductions
            FROM tenants t
            LEFT JOIN topups tu ON tu.tenant_id=t.id
            LEFT JOIN deductions d ON d.tenant_id=t.id
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
        v_clause = "AND t.vertical=:vertical" if vertical else ""
        if vertical:
            p["vertical"] = vertical

        avg_rating = await _safe_scalar(db,
            f"SELECT ROUND(AVG(cr.overall_rating)::numeric,2) "
            f"FROM customer_reviews cr JOIN tenants t ON t.id=cr.tenant_id "
            f"WHERE cr.created_at BETWEEN :from_dt AND :to_dt {v_clause}", p)

        review_count = await _safe_count(db,
            f"SELECT COUNT(*) FROM customer_reviews cr JOIN tenants t ON t.id=cr.tenant_id "
            f"WHERE cr.created_at BETWEEN :from_dt AND :to_dt {v_clause}", p)

        job_count = await _safe_count(db,
            f"SELECT COUNT(*) FROM service_jobs sj JOIN tenants t ON t.id=sj.tenant_id "
            f"WHERE sj.created_at BETWEEN :from_dt AND :to_dt {v_clause}", p)

        complaint_count = await _safe_count(db,
            f"SELECT COUNT(*) FROM customer_complaints cc JOIN tenants t ON t.id=cc.tenant_id "
            f"WHERE cc.created_at BETWEEN :from_dt AND :to_dt {v_clause}", p)

        dispute_count = await _safe_count(db,
            f"SELECT COUNT(*) FROM customer_complaints cc JOIN tenants t ON t.id=cc.tenant_id "
            f"WHERE cc.status IN ('disputed','escalated') "
            f"AND cc.created_at BETWEEN :from_dt AND :to_dt {v_clause}", p)

        return {
            "avg_rating": float(avg_rating or 0),
            "review_count": review_count,
            "complaint_rate": round(complaint_count / max(job_count, 1) * 100, 2),
            "dispute_rate": round(dispute_count / max(job_count, 1) * 100, 2),
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
        v_clause = "AND t.vertical=:vertical" if vertical else ""
        if vertical:
            p["vertical"] = vertical

        total = await _safe_count(db,
            f"SELECT COUNT(*) FROM customer_complaints cc JOIN tenants t ON t.id=cc.tenant_id "
            f"WHERE cc.created_at BETWEEN :from_dt AND :to_dt {v_clause}", p)
        open_c = await _safe_count(db,
            f"SELECT COUNT(*) FROM customer_complaints cc JOIN tenants t ON t.id=cc.tenant_id "
            f"WHERE cc.status NOT IN ('resolved','closed') "
            f"AND cc.created_at BETWEEN :from_dt AND :to_dt {v_clause}", p)
        resolved = await _safe_count(db,
            f"SELECT COUNT(*) FROM customer_complaints cc JOIN tenants t ON t.id=cc.tenant_id "
            f"WHERE cc.status IN ('resolved','closed') "
            f"AND cc.created_at BETWEEN :from_dt AND :to_dt {v_clause}", p)

        avg_res_hours = await _safe_scalar(db, f"""
            SELECT ROUND(AVG(EXTRACT(EPOCH FROM (cc.resolved_at-cc.created_at))/3600)::numeric,1)
            FROM customer_complaints cc JOIN tenants t ON t.id=cc.tenant_id
            WHERE cc.resolved_at IS NOT NULL
              AND cc.created_at BETWEEN :from_dt AND :to_dt {v_clause}
        """, p)

        credits_issued = await _safe_scalar(db,
            f"SELECT COALESCE(SUM(csc.amount),0) FROM customer_service_credits csc "
            f"JOIN tenants t ON t.id=csc.tenant_id "
            f"WHERE csc.created_at BETWEEN :from_dt AND :to_dt {v_clause}", p)

        tenant_responsible = await _safe_count(db,
            f"SELECT COUNT(*) FROM customer_complaints cc JOIN tenants t ON t.id=cc.tenant_id "
            f"WHERE cc.resolution_type='tenant_fault' "
            f"AND cc.created_at BETWEEN :from_dt AND :to_dt {v_clause}", p)

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
        vertical: str | None = None,
    ) -> dict:
        from_dt, to_dt = _date_defaults(date_from, date_to)
        p: dict[str, Any] = {"from_dt": from_dt, "to_dt": to_dt}
        v_clause = "AND t.vertical=:vertical" if vertical else ""
        if vertical:
            p["vertical"] = vertical

        by_severity = await _safe_rows(db, f"""
            SELECT cc.severity, COUNT(*) AS count
            FROM customer_complaints cc JOIN tenants t ON t.id=cc.tenant_id
            WHERE cc.created_at BETWEEN :from_dt AND :to_dt {v_clause}
            GROUP BY cc.severity ORDER BY count DESC
        """, p)

        by_type = await _safe_rows(db, f"""
            SELECT cc.complaint_type, COUNT(*) AS count
            FROM customer_complaints cc JOIN tenants t ON t.id=cc.tenant_id
            WHERE cc.created_at BETWEEN :from_dt AND :to_dt {v_clause}
            GROUP BY cc.complaint_type ORDER BY count DESC
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
        city: str | None = None,
        state: str | None = None,
    ) -> dict:
        from_dt, to_dt = _date_defaults(date_from, date_to)
        p: dict[str, Any] = {"from_dt": from_dt, "to_dt": to_dt}
        filters = ["t.status='active'", "t.city IS NOT NULL"]
        if vertical:
            filters.append("t.vertical=:vertical")
            p["vertical"] = vertical
        if city:
            filters.append("LOWER(t.city)=LOWER(:city)")
            p["city"] = city
        if state:
            filters.append("LOWER(t.state)=LOWER(:state)")
            p["state"] = state
        where_clause = " AND ".join(filters)

        top_cities = await _safe_rows(db, f"""
            WITH job_metrics AS (
              SELECT tenant_id, COUNT(*) AS booking_count
              FROM service_jobs
              WHERE created_at BETWEEN :from_dt AND :to_dt
              GROUP BY tenant_id
            ), review_metrics AS (
              SELECT tenant_id, AVG(overall_rating) AS avg_rating
              FROM customer_reviews
              WHERE created_at BETWEEN :from_dt AND :to_dt
              GROUP BY tenant_id
            )
            SELECT
                t.city,
                t.state,
                COALESCE(SUM(jm.booking_count),0) AS booking_count,
                COUNT(*) AS tenant_count,
                COALESCE(AVG(rm.avg_rating) FILTER (WHERE rm.avg_rating IS NOT NULL),0) AS avg_rating
            FROM tenants t
            LEFT JOIN job_metrics jm ON jm.tenant_id=t.id
            LEFT JOIN review_metrics rm ON rm.tenant_id=t.id
            WHERE {where_clause}
            GROUP BY t.city, t.state
            ORDER BY booking_count DESC
            LIMIT 20
        """, p)

        return {
            "top_cities": [
                {
                    "city": r["city"],
                    "state": r.get("state"),
                    "booking_count": int(r["booking_count"] or 0),
                    "tenant_count": int(r["tenant_count"] or 0),
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
        vertical: str | None = None,
    ) -> dict:
        from_dt, to_dt = _date_defaults(date_from, date_to)
        p: dict[str, Any] = {"from_dt": from_dt, "to_dt": to_dt}
        v_clause = "AND t.vertical=:vertical" if vertical else ""
        if vertical:
            p["vertical"] = vertical

        active_customers = await _safe_count(db,
            f"SELECT COUNT(DISTINCT sj.customer_id) FROM service_jobs sj "
            f"JOIN tenants t ON t.id=sj.tenant_id "
            f"WHERE sj.created_at BETWEEN :from_dt AND :to_dt {v_clause}", p)

        if vertical:
            new_customers = await _safe_count(db, f"""
                SELECT COUNT(DISTINCT u.id)
                FROM users u
                JOIN service_jobs sj ON sj.customer_id=u.id
                JOIN tenants t ON t.id=sj.tenant_id
                WHERE u.role='customer'
                  AND u.created_at BETWEEN :from_dt AND :to_dt {v_clause}
            """, p)
        else:
            new_customers = await _safe_count(db,
                "SELECT COUNT(*) FROM users WHERE role='customer' AND created_at BETWEEN :from_dt AND :to_dt", p)

        total_bookings = await _safe_count(db,
            f"SELECT COUNT(*) FROM service_jobs sj JOIN tenants t ON t.id=sj.tenant_id "
            f"WHERE sj.created_at BETWEEN :from_dt AND :to_dt {v_clause}", p)

        bookings_per_customer = round(total_bookings / max(active_customers, 1), 2)

        credits_used = await _safe_scalar(db, f"""
            SELECT COALESCE(SUM(ccl.amount),0)
            FROM customer_credit_ledger ccl
            LEFT JOIN service_jobs sj ON sj.booking_id=ccl.booking_id
            LEFT JOIN tenants t ON t.id=sj.tenant_id
            WHERE ccl.transaction_type IN ('used','partially_used')
              AND ccl.created_at BETWEEN :from_dt AND :to_dt {v_clause}
        """, p)

        customer_complaints = await _safe_count(db,
            f"SELECT COUNT(*) FROM customer_complaints cc JOIN tenants t ON t.id=cc.tenant_id "
            f"WHERE cc.created_at BETWEEN :from_dt AND :to_dt {v_clause}", p)

        return {
            "active_customers": active_customers,
            "new_customers": new_customers,
            "bookings_per_customer": bookings_per_customer,
            "customer_service_credits_used": float(credits_used or 0),
            "customer_complaints": customer_complaints,
        }
