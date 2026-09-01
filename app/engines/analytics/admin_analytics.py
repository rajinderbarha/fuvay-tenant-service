"""Sprint 28 — AdminAnalyticsService.

All queries use sqlalchemy text() to avoid importing every domain model.
Each metric is wrapped to fail gracefully — one card failure never breaks the dashboard.
"""
from __future__ import annotations
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.analytics.helpers import (
    resolve_date_range, date_range_to_datetimes, safe_metric, analytics_ok,
)


_utcnow = lambda: datetime.now(timezone.utc)


class AdminAnalyticsService:
    """Read-only analytics for platform admins.

    All methods accept optional date_from / date_to strings (ISO-8601 date).
    tenant_id filter is optional for admin (admin sees all).
    """

    # ── Platform Summary ──────────────────────────────────────────────────────

    async def get_platform_summary(
        self, db: AsyncSession,
        date_from: str | None = None,
        date_to: str | None = None,
        category_id: str | None = None,
        tenant_id: str | None = None,
    ) -> dict:
        df, dt = resolve_date_range(date_from, date_to)
        from_dt, to_dt = date_range_to_datetimes(df, dt)

        p = {
            "from_dt": from_dt,
            "to_dt":   to_dt,
            "category_id": uuid.UUID(category_id) if category_id else None,
            "tenant_id":   uuid.UUID(tenant_id)   if tenant_id   else None,
        }

        summary = {}

        # Tenant counts (lifetime)
        summary["total_tenants"]              = await safe_metric(_scalar(db, "SELECT COUNT(*) FROM tenants"))
        summary["active_tenants"]             = await safe_metric(_scalar(db, "SELECT COUNT(*) FROM tenants WHERE status = 'active'"))
        summary["pending_verification_tenants"] = await safe_metric(_scalar(db, "SELECT COUNT(*) FROM tenants WHERE verification_status IN ('pending','under_review')"))
        summary["suspended_tenants"]          = await safe_metric(_scalar(db, "SELECT COUNT(*) FROM tenants WHERE status = 'suspended'"))

        # Bookings / Jobs / Appointments / Leads in period
        summary["total_bookings_period"]      = await safe_metric(_scalar(db, """
            SELECT COUNT(*) FROM service_bookings
            WHERE created_at BETWEEN :from_dt AND :to_dt
            {tenant_clause}
        """.format(tenant_clause="AND tenant_id = :tenant_id" if tenant_id else ""), p))

        summary["total_jobs_period"]          = await safe_metric(_scalar(db, """
            SELECT COUNT(*) FROM service_jobs
            WHERE created_at BETWEEN :from_dt AND :to_dt
            {tenant_clause}
        """.format(tenant_clause="AND tenant_id = :tenant_id" if tenant_id else ""), p))

        summary["total_appointments_period"]  = await safe_metric(_scalar(db, """
            SELECT COUNT(*) FROM coaching_appointments
            WHERE created_at BETWEEN :from_dt AND :to_dt
            {tenant_clause}
        """.format(tenant_clause="AND tenant_id = :tenant_id" if tenant_id else ""), p))

        summary["total_leads_period"]         = await safe_metric(_scalar(db, """
            SELECT COUNT(*) FROM real_estate_leads
            WHERE created_at BETWEEN :from_dt AND :to_dt
            {tenant_clause}
        """.format(tenant_clause="AND tenant_id = :tenant_id" if tenant_id else ""), p))

        summary["total_invoices_period"]      = await safe_metric(_scalar(db, """
            SELECT COUNT(*) FROM service_invoices
            WHERE created_at BETWEEN :from_dt AND :to_dt
            {tenant_clause}
        """.format(tenant_clause="AND tenant_id = :tenant_id" if tenant_id else ""), p))

        # Financial totals in period
        summary["total_payment_collected"]    = await safe_metric(_scalar(db, """
            SELECT COALESCE(SUM(collected_amount), 0) FROM service_payment_records
            WHERE payment_status = 'collected'
            AND created_at BETWEEN :from_dt AND :to_dt
            {tenant_clause}
        """.format(tenant_clause="AND tenant_id = :tenant_id" if tenant_id else ""), p))

        summary["total_commission_deducted"]  = await safe_metric(_scalar(db, """
            SELECT COALESCE(SUM(commission_amount), 0) FROM svc_commission_records
            WHERE status = 'deducted'
            AND created_at BETWEEN :from_dt AND :to_dt
            {tenant_clause}
        """.format(tenant_clause="AND tenant_id = :tenant_id" if tenant_id else ""), p))

        summary["total_wallet_balance"]       = await safe_metric(_scalar(db,
            "SELECT COALESCE(SUM(credit_balance), 0) FROM tenant_billing"))

        # Quality
        summary["average_rating"]             = await safe_metric(_scalar(db, """
            SELECT ROUND(AVG(overall_rating)::numeric, 2) FROM customer_reviews
            WHERE status = 'approved'
            AND created_at BETWEEN :from_dt AND :to_dt
        """, p))

        summary["open_complaints"]            = await safe_metric(_scalar(db,
            "SELECT COUNT(*) FROM customer_complaints WHERE status IN ('open','investigating','awaiting_provider')"))

        summary["pending_refunds"]            = await safe_metric(_scalar(db,
            "SELECT COUNT(*) FROM refund_requests WHERE status IN ('pending','approved')"))

        summary["unread_critical_notifications"] = await safe_metric(_scalar(db,
            "SELECT COUNT(*) FROM in_app_notifications WHERE read_status = 'unread' AND severity = 'critical'"))

        return analytics_ok(
            summary=summary,
            filters_applied={
                "date_from": str(df), "date_to": str(dt),
                "category_id": category_id, "tenant_id": tenant_id,
            },
            date_from=df, date_to=dt,
        )

    # ── Category Performance ──────────────────────────────────────────────────

    async def get_category_performance(
        self, db: AsyncSession,
        date_from: str | None = None,
        date_to: str | None = None,
        category_id: str | None = None,
    ) -> dict:
        df, dt = resolve_date_range(date_from, date_to)
        from_dt, to_dt = date_range_to_datetimes(df, dt)
        p = {"from_dt": from_dt, "to_dt": to_dt}

        # Category-level booking distribution
        rows = await safe_metric(_rows(db, """
            SELECT
                sb.category_id::text,
                COUNT(*) AS booking_count,
                COUNT(CASE WHEN sb.status = 'completed' THEN 1 END) AS completed_count,
                COUNT(CASE WHEN sb.status = 'cancelled' THEN 1 END) AS cancelled_count
            FROM service_bookings sb
            WHERE sb.created_at BETWEEN :from_dt AND :to_dt
            GROUP BY sb.category_id
            ORDER BY booking_count DESC
            LIMIT 20
        """, p), [])

        coaching_rows = await safe_metric(_rows(db, """
            SELECT
                ca.category_id::text,
                COUNT(*) AS appt_count,
                COUNT(CASE WHEN ca.status = 'completed' THEN 1 END) AS completed_count
            FROM coaching_appointments ca
            WHERE ca.created_at BETWEEN :from_dt AND :to_dt
            GROUP BY ca.category_id
            ORDER BY appt_count DESC
            LIMIT 10
        """, p), [])

        re_rows = await safe_metric(_rows(db, """
            SELECT
                rl.category_id::text,
                COUNT(*) AS lead_count,
                COUNT(CASE WHEN rl.status = 'converted' THEN 1 END) AS converted_count
            FROM real_estate_leads rl
            WHERE rl.created_at BETWEEN :from_dt AND :to_dt
            GROUP BY rl.category_id
            ORDER BY lead_count DESC
            LIMIT 10
        """, p), [])

        breakdown = [
            {**dict(r), "record_type": "booking"} for r in rows
        ] + [
            {**dict(r), "record_type": "appointment"} for r in coaching_rows
        ] + [
            {**dict(r), "record_type": "lead"} for r in re_rows
        ]

        return analytics_ok(
            summary={"total_categories_with_activity": len(breakdown)},
            breakdown=breakdown,
            filters_applied={"date_from": str(df), "date_to": str(dt), "category_id": category_id},
            date_from=df, date_to=dt,
        )

    # ── Provider Performance ──────────────────────────────────────────────────

    async def get_provider_performance(
        self, db: AsyncSession,
        date_from: str | None = None,
        date_to: str | None = None,
        category_id: str | None = None,
        tenant_id: str | None = None,
    ) -> dict:
        df, dt = resolve_date_range(date_from, date_to)
        from_dt, to_dt = date_range_to_datetimes(df, dt)

        p: dict = {"from_dt": from_dt, "to_dt": to_dt}
        tenant_clause = ""
        if tenant_id:
            tenant_clause = "AND sj.tenant_id = :tenant_id"
            p["tenant_id"] = uuid.UUID(tenant_id)

        provider_rows = await safe_metric(_rows(db, f"""
            SELECT
                sj.tenant_id::text,
                COUNT(*) AS total_jobs,
                COUNT(CASE WHEN sj.status = 'completed' THEN 1 END) AS completed_jobs,
                COUNT(CASE WHEN sj.status = 'cancelled' THEN 1 END) AS cancelled_jobs
            FROM service_jobs sj
            WHERE sj.created_at BETWEEN :from_dt AND :to_dt
            {tenant_clause}
            GROUP BY sj.tenant_id
            ORDER BY completed_jobs DESC
            LIMIT 50
        """, p), [])

        # Enrich with rating
        enriched = []
        for row in provider_rows:
            tid = row["tenant_id"]
            avg_rating = await safe_metric(_scalar(db, """
                SELECT ROUND(AVG(overall_rating)::numeric, 2)
                FROM customer_reviews
                WHERE tenant_id = :tid AND status = 'approved'
                AND created_at BETWEEN :from_dt AND :to_dt
            """, {"tid": uuid.UUID(tid), **p}))
            enriched.append({**dict(row), "average_rating": avg_rating})

        top_providers = sorted(enriched, key=lambda x: x.get("completed_jobs", 0) or 0, reverse=True)[:10]
        low_performers = [p for p in enriched if (p.get("completed_jobs", 0) or 0) == 0][:10]

        return analytics_ok(
            summary={"provider_count": len(provider_rows)},
            breakdown=enriched,
            top_items=top_providers,
            filters_applied={"date_from": str(df), "date_to": str(dt),
                             "category_id": category_id, "tenant_id": tenant_id},
            date_from=df, date_to=dt,
            extra={"low_performing_providers": low_performers},
        )

    # ── Financial Summary ─────────────────────────────────────────────────────

    async def get_financial_summary(
        self, db: AsyncSession,
        date_from: str | None = None,
        date_to: str | None = None,
        tenant_id: str | None = None,
    ) -> dict:
        df, dt = resolve_date_range(date_from, date_to)
        from_dt, to_dt = date_range_to_datetimes(df, dt)
        p: dict = {"from_dt": from_dt, "to_dt": to_dt}
        if tenant_id:
            p["tenant_id"] = uuid.UUID(tenant_id)

        tc = "AND tenant_id = :tenant_id" if tenant_id else ""
        summary = {}

        summary["total_invoice_amount"]       = await safe_metric(_scalar(db, f"""
            SELECT COALESCE(SUM(total_amount), 0) FROM service_invoices
            WHERE created_at BETWEEN :from_dt AND :to_dt {tc}
        """, p))

        summary["total_payment_collected"]    = await safe_metric(_scalar(db, f"""
            SELECT COALESCE(SUM(collected_amount), 0) FROM service_payment_records
            WHERE payment_status = 'collected'
            AND created_at BETWEEN :from_dt AND :to_dt {tc}
        """, p))

        summary["total_commission_calculated"] = await safe_metric(_scalar(db, f"""
            SELECT COALESCE(SUM(commission_amount), 0) FROM svc_commission_records
            WHERE status IN ('calculated','deducted')
            AND created_at BETWEEN :from_dt AND :to_dt {tc}
        """, p))

        summary["total_commission_deducted"]  = await safe_metric(_scalar(db, f"""
            SELECT COALESCE(SUM(commission_amount), 0) FROM svc_commission_records
            WHERE status = 'deducted'
            AND created_at BETWEEN :from_dt AND :to_dt {tc}
        """, p))

        summary["total_commission_failed"]    = await safe_metric(_scalar(db, f"""
            SELECT COUNT(*) FROM svc_commission_records
            WHERE status IN ('failed','insufficient_credit')
            AND created_at BETWEEN :from_dt AND :to_dt {tc}
        """, p))

        summary["total_wallet_balance"]       = await safe_metric(_scalar(db,
            "SELECT COALESCE(SUM(credit_balance), 0) FROM tenant_billing"))

        summary["low_wallet_providers"]       = await safe_metric(_scalar(db,
            "SELECT COUNT(*) FROM tenant_billing WHERE credit_balance < 500"))

        summary["exhausted_wallet_providers"] = await safe_metric(_scalar(db,
            "SELECT COUNT(*) FROM tenant_billing WHERE credit_balance <= 0"))

        summary["refund_requested_amount"]    = await safe_metric(_scalar(db, f"""
            SELECT COALESCE(SUM(requested_amount), 0) FROM refund_requests
            WHERE created_at BETWEEN :from_dt AND :to_dt {tc}
        """, p))

        summary["refund_approved_amount"]     = await safe_metric(_scalar(db, f"""
            SELECT COALESCE(SUM(approved_amount), 0) FROM refund_requests
            WHERE status IN ('approved','recorded')
            AND created_at BETWEEN :from_dt AND :to_dt {tc}
        """, p))

        # Breakdown by payment status
        breakdown = await safe_metric(_rows(db, f"""
            SELECT payment_status, COUNT(*) AS count,
                   COALESCE(SUM(collected_amount), 0) AS total_amount
            FROM service_payment_records
            WHERE created_at BETWEEN :from_dt AND :to_dt {tc}
            GROUP BY payment_status
            ORDER BY count DESC
        """, p), [])

        return analytics_ok(
            summary={k: str(v) if v is not None and not isinstance(v, (int, type(None))) else v
                     for k, v in summary.items()},
            breakdown=[dict(r) for r in breakdown],
            filters_applied={"date_from": str(df), "date_to": str(dt), "tenant_id": tenant_id},
            date_from=df, date_to=dt,
        )

    # ── Quality Summary ───────────────────────────────────────────────────────

    async def get_quality_summary(
        self, db: AsyncSession,
        date_from: str | None = None,
        date_to: str | None = None,
        tenant_id: str | None = None,
    ) -> dict:
        df, dt = resolve_date_range(date_from, date_to)
        from_dt, to_dt = date_range_to_datetimes(df, dt)
        p: dict = {"from_dt": from_dt, "to_dt": to_dt}
        if tenant_id:
            p["tenant_id"] = uuid.UUID(tenant_id)
        tc = "AND tenant_id = :tenant_id" if tenant_id else ""

        summary = {}
        summary["average_rating"]      = await safe_metric(_scalar(db, f"""
            SELECT ROUND(AVG(overall_rating)::numeric, 2) FROM customer_reviews
            WHERE status = 'approved' AND created_at BETWEEN :from_dt AND :to_dt {tc}
        """, p))
        summary["total_reviews"]       = await safe_metric(_scalar(db, f"""
            SELECT COUNT(*) FROM customer_reviews
            WHERE created_at BETWEEN :from_dt AND :to_dt {tc}
        """, p))
        summary["approved_reviews"]    = await safe_metric(_scalar(db, f"""
            SELECT COUNT(*) FROM customer_reviews
            WHERE status = 'approved' AND created_at BETWEEN :from_dt AND :to_dt {tc}
        """, p))
        summary["pending_reviews"]     = await safe_metric(_scalar(db, f"""
            SELECT COUNT(*) FROM customer_reviews
            WHERE status = 'pending' AND created_at BETWEEN :from_dt AND :to_dt {tc}
        """, p))

        rating_dist = await safe_metric(_rows(db, f"""
            SELECT overall_rating AS rating, COUNT(*) AS count
            FROM customer_reviews
            WHERE status = 'approved' AND created_at BETWEEN :from_dt AND :to_dt {tc}
            GROUP BY overall_rating ORDER BY overall_rating DESC
        """, p), [])

        summary["rating_distribution"] = {str(r["rating"]): r["count"] for r in rating_dist}

        summary["reply_count"]         = await safe_metric(_scalar(db, f"""
            SELECT COUNT(*) FROM review_replies
            WHERE status = 'approved' AND created_at BETWEEN :from_dt AND :to_dt
        """, p))

        return analytics_ok(
            summary=summary,
            breakdown=[dict(r) for r in rating_dist],
            filters_applied={"date_from": str(df), "date_to": str(dt), "tenant_id": tenant_id},
            date_from=df, date_to=dt,
        )

    # ── Complaint Summary ─────────────────────────────────────────────────────

    async def get_complaint_summary(
        self, db: AsyncSession,
        date_from: str | None = None,
        date_to: str | None = None,
        tenant_id: str | None = None,
    ) -> dict:
        df, dt = resolve_date_range(date_from, date_to)
        from_dt, to_dt = date_range_to_datetimes(df, dt)
        p: dict = {"from_dt": from_dt, "to_dt": to_dt}
        if tenant_id:
            p["tenant_id"] = uuid.UUID(tenant_id)
        tc = "AND tenant_id = :tenant_id" if tenant_id else ""

        summary = {}
        summary["total_complaints"]    = await safe_metric(_scalar(db, f"""
            SELECT COUNT(*) FROM customer_complaints
            WHERE created_at BETWEEN :from_dt AND :to_dt {tc}
        """, p))
        summary["open_complaints"]     = await safe_metric(_scalar(db, f"""
            SELECT COUNT(*) FROM customer_complaints
            WHERE status IN ('open','investigating','awaiting_provider')
            AND created_at BETWEEN :from_dt AND :to_dt {tc}
        """, p))
        summary["resolved_complaints"] = await safe_metric(_scalar(db, f"""
            SELECT COUNT(*) FROM customer_complaints
            WHERE status IN ('resolved','closed')
            AND created_at BETWEEN :from_dt AND :to_dt {tc}
        """, p))
        summary["total_refund_requests"] = await safe_metric(_scalar(db, f"""
            SELECT COUNT(*) FROM refund_requests
            WHERE created_at BETWEEN :from_dt AND :to_dt {tc}
        """, p))
        summary["total_rework_requests"] = await safe_metric(_scalar(db, f"""
            SELECT COUNT(*) FROM service_rework_requests
            WHERE created_at BETWEEN :from_dt AND :to_dt {tc}
        """, p))

        status_breakdown = await safe_metric(_rows(db, f"""
            SELECT status, COUNT(*) AS count
            FROM customer_complaints
            WHERE created_at BETWEEN :from_dt AND :to_dt {tc}
            GROUP BY status ORDER BY count DESC
        """, p), [])

        return analytics_ok(
            summary=summary,
            breakdown=[dict(r) for r in status_breakdown],
            filters_applied={"date_from": str(df), "date_to": str(dt), "tenant_id": tenant_id},
            date_from=df, date_to=dt,
        )

    # ── Operational Alerts ────────────────────────────────────────────────────

    async def get_operational_alerts(self, db: AsyncSession) -> dict:
        alerts = []

        low_wallet = await safe_metric(_rows(db,
            "SELECT tenant_id::text, credit_balance FROM tenant_billing "
            "WHERE credit_balance < 500 LIMIT 20"), [])
        for r in low_wallet:
            alerts.append({"type": "low_wallet", "tenant_id": r["tenant_id"],
                           "balance": str(r["credit_balance"]), "severity": "warning"})

        exhausted = await safe_metric(_rows(db,
            "SELECT tenant_id::text FROM tenant_billing "
            "WHERE credit_balance <= 0 LIMIT 20"), [])
        for r in exhausted:
            alerts.append({"type": "exhausted_wallet", "tenant_id": r["tenant_id"],
                           "severity": "critical"})

        open_complaints = await safe_metric(_scalar(db,
            "SELECT COUNT(*) FROM customer_complaints WHERE status = 'open'"))
        if open_complaints:
            alerts.append({"type": "open_complaints", "count": open_complaints, "severity": "warning"})

        pending_refunds = await safe_metric(_scalar(db,
            "SELECT COUNT(*) FROM refund_requests WHERE status = 'pending'"))
        if pending_refunds:
            alerts.append({"type": "pending_refunds", "count": pending_refunds, "severity": "warning"})

        notif_failures = await safe_metric(_scalar(db,
            "SELECT COUNT(*) FROM notification_outbox WHERE delivery_status = 'failed'"))
        if notif_failures:
            alerts.append({"type": "notification_failures", "count": notif_failures, "severity": "warning"})

        return analytics_ok(
            summary={"alert_count": len(alerts)},
            top_items=alerts,
            filters_applied={},
        )

    # ── Staff Performance ─────────────────────────────────────────────────────

    async def get_staff_performance(
        self, db: AsyncSession,
        date_from: str | None = None,
        date_to: str | None = None,
        tenant_id: str | None = None,
    ) -> dict:
        df, dt = resolve_date_range(date_from, date_to)
        from_dt, to_dt = date_range_to_datetimes(df, dt)
        p: dict = {"from_dt": from_dt, "to_dt": to_dt}
        if tenant_id:
            p["tenant_id"] = uuid.UUID(tenant_id)
        tc = "AND sja.tenant_id = :tenant_id" if tenant_id else ""

        rows = await safe_metric(_rows(db, f"""
            SELECT
                sja.assigned_staff_member_id::text AS staff_id,
                COUNT(*) AS total_assignments,
                COUNT(CASE WHEN sja.assignment_status = 'accepted' THEN 1 END) AS accepted,
                COUNT(CASE WHEN sja.assignment_status = 'rejected' THEN 1 END) AS rejected,
                COUNT(CASE WHEN sja.assignment_status = 'completed' THEN 1 END) AS completed
            FROM service_job_assignments sja
            WHERE sja.created_at BETWEEN :from_dt AND :to_dt
            {tc}
            GROUP BY sja.assigned_staff_member_id
            ORDER BY completed DESC
            LIMIT 50
        """, p), [])

        return analytics_ok(
            summary={"staff_count": len(rows)},
            breakdown=[dict(r) for r in rows],
            top_items=[dict(r) for r in rows[:10]],
            filters_applied={"date_from": str(df), "date_to": str(dt), "tenant_id": tenant_id},
            date_from=df, date_to=dt,
        )

    # ── Top / Low Performing Providers ────────────────────────────────────────

    async def get_top_providers(
        self, db: AsyncSession,
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int = 10,
    ) -> list:
        df, dt = resolve_date_range(date_from, date_to)
        from_dt, to_dt = date_range_to_datetimes(df, dt)
        rows = await safe_metric(_rows(db, """
            SELECT sj.tenant_id::text,
                   COUNT(CASE WHEN sj.status = 'completed' THEN 1 END) AS completed_jobs
            FROM service_jobs sj
            WHERE sj.created_at BETWEEN :from_dt AND :to_dt
            GROUP BY sj.tenant_id
            ORDER BY completed_jobs DESC
            LIMIT :limit
        """, {"from_dt": from_dt, "to_dt": to_dt, "limit": limit}), [])
        return [dict(r) for r in rows]

    async def get_low_performing_providers(
        self, db: AsyncSession,
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int = 10,
    ) -> list:
        df, dt = resolve_date_range(date_from, date_to)
        from_dt, to_dt = date_range_to_datetimes(df, dt)
        rows = await safe_metric(_rows(db, """
            SELECT sj.tenant_id::text,
                   COUNT(*) AS total_jobs,
                   COUNT(CASE WHEN sj.status = 'completed' THEN 1 END) AS completed_jobs,
                   COUNT(CASE WHEN sj.status = 'cancelled' THEN 1 END) AS cancelled_jobs
            FROM service_jobs sj
            WHERE sj.created_at BETWEEN :from_dt AND :to_dt
            GROUP BY sj.tenant_id
            HAVING COUNT(CASE WHEN sj.status = 'completed' THEN 1 END) = 0
            ORDER BY total_jobs DESC
            LIMIT :limit
        """, {"from_dt": from_dt, "to_dt": to_dt, "limit": limit}), [])
        return [dict(r) for r in rows]


# ── SQL helpers ───────────────────────────────────────────────────────────────

async def _scalar(db: AsyncSession, sql: str, params: dict | None = None):
    """Execute sql and return first scalar (or None)."""
    result = await db.execute(text(sql), params or {})
    return result.scalar_one_or_none()


async def _rows(db: AsyncSession, sql: str, params: dict | None = None):
    """Execute sql and return all rows as mappings."""
    result = await db.execute(text(sql), params or {})
    return result.mappings().all()
