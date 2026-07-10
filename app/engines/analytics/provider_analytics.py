"""Sprint 28 — ProviderAnalyticsService.

All methods enforce tenant_id from token — never trust query param.
Provider cannot pass a different tenant_id to see another provider's data.
"""
from __future__ import annotations
import uuid
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.analytics.helpers import (
    resolve_date_range, date_range_to_datetimes, safe_metric, analytics_ok,
)

_utcnow = lambda: datetime.now(timezone.utc)


class ProviderAnalyticsService:
    """Read-only analytics scoped strictly to the provider's own tenant_id."""

    # ── Provider Dashboard ────────────────────────────────────────────────────

    async def get_provider_dashboard(
        self, db: AsyncSession, tenant_id: uuid.UUID,
        date_from: str | None = None, date_to: str | None = None,
    ) -> dict:
        df, dt = resolve_date_range(date_from, date_to)
        from_dt, to_dt = date_range_to_datetimes(df, dt)
        p = {"tenant_id": tenant_id, "from_dt": from_dt, "to_dt": to_dt}

        summary = {}
        summary["total_bookings"]   = await safe_metric(_scalar(db, """
            SELECT COUNT(*) FROM service_bookings
            WHERE tenant_id = :tenant_id AND created_at BETWEEN :from_dt AND :to_dt
        """, p))
        summary["active_jobs"]      = await safe_metric(_scalar(db, """
            SELECT COUNT(*) FROM service_jobs
            WHERE tenant_id = :tenant_id
            AND status IN ('accepted','in_progress','on_the_way','reached_site','inspection')
        """, p))
        summary["completed_jobs"]   = await safe_metric(_scalar(db, """
            SELECT COUNT(*) FROM service_jobs
            WHERE tenant_id = :tenant_id AND status = 'completed'
            AND created_at BETWEEN :from_dt AND :to_dt
        """, p))
        summary["cancelled_jobs"]   = await safe_metric(_scalar(db, """
            SELECT COUNT(*) FROM service_jobs
            WHERE tenant_id = :tenant_id AND status = 'cancelled'
            AND created_at BETWEEN :from_dt AND :to_dt
        """, p))
        summary["total_appointments"] = await safe_metric(_scalar(db, """
            SELECT COUNT(*) FROM coaching_appointments
            WHERE tenant_id = :tenant_id AND created_at BETWEEN :from_dt AND :to_dt
        """, p))
        summary["total_leads"]      = await safe_metric(_scalar(db, """
            SELECT COUNT(*) FROM real_estate_leads
            WHERE tenant_id = :tenant_id AND created_at BETWEEN :from_dt AND :to_dt
        """, p))
        summary["invoice_total"]    = await safe_metric(_scalar(db, """
            SELECT COALESCE(SUM(total_amount), 0) FROM service_invoices
            WHERE tenant_id = :tenant_id AND created_at BETWEEN :from_dt AND :to_dt
        """, p))
        summary["payment_collected"] = await safe_metric(_scalar(db, """
            SELECT COALESCE(SUM(collected_amount), 0) FROM service_payment_records
            WHERE tenant_id = :tenant_id AND payment_status = 'collected'
            AND created_at BETWEEN :from_dt AND :to_dt
        """, p))
        summary["commission_deducted"] = await safe_metric(_scalar(db, """
            SELECT COALESCE(SUM(commission_amount), 0) FROM svc_commission_records
            WHERE tenant_id = :tenant_id AND status = 'deducted'
            AND created_at BETWEEN :from_dt AND :to_dt
        """, p))
        summary["wallet_balance"]   = await safe_metric(_scalar(db, """
            SELECT credit_balance FROM tenant_wallets
            WHERE tenant_id = :tenant_id AND is_active = true
        """, p))
        summary["average_rating"]   = await safe_metric(_scalar(db, """
            SELECT ROUND(AVG(overall_rating)::numeric, 2)
            FROM customer_reviews
            WHERE tenant_id = :tenant_id AND status = 'approved'
            AND created_at BETWEEN :from_dt AND :to_dt
        """, p))
        summary["open_complaints"]  = await safe_metric(_scalar(db, """
            SELECT COUNT(*) FROM customer_complaints
            WHERE tenant_id = :tenant_id AND status IN ('open','investigating','awaiting_provider')
        """, p))
        summary["unread_notifications"] = await safe_metric(_scalar(db, """
            SELECT COUNT(*) FROM in_app_notifications
            WHERE tenant_id = :tenant_id AND read_status = 'unread'
        """, p))

        return analytics_ok(
            summary={k: str(v) if hasattr(v, "__round__") and v is not None and isinstance(v, float) else v
                     for k, v in summary.items()},
            filters_applied={"date_from": str(df), "date_to": str(dt)},
            date_from=df, date_to=dt,
        )

    # ── Provider Financial Summary ────────────────────────────────────────────

    async def get_provider_financial_summary(
        self, db: AsyncSession, tenant_id: uuid.UUID,
        date_from: str | None = None, date_to: str | None = None,
    ) -> dict:
        df, dt = resolve_date_range(date_from, date_to)
        from_dt, to_dt = date_range_to_datetimes(df, dt)
        p = {"tenant_id": tenant_id, "from_dt": from_dt, "to_dt": to_dt}

        summary = {}
        summary["invoice_total"]      = await safe_metric(_scalar(db, """
            SELECT COALESCE(SUM(total_amount), 0) FROM service_invoices
            WHERE tenant_id = :tenant_id AND created_at BETWEEN :from_dt AND :to_dt
        """, p))
        summary["payment_collected"]  = await safe_metric(_scalar(db, """
            SELECT COALESCE(SUM(collected_amount), 0) FROM service_payment_records
            WHERE tenant_id = :tenant_id AND payment_status = 'collected'
            AND created_at BETWEEN :from_dt AND :to_dt
        """, p))
        summary["commission_deducted"] = await safe_metric(_scalar(db, """
            SELECT COALESCE(SUM(commission_amount), 0) FROM svc_commission_records
            WHERE tenant_id = :tenant_id AND status = 'deducted'
            AND created_at BETWEEN :from_dt AND :to_dt
        """, p))
        summary["commission_failed"]  = await safe_metric(_scalar(db, """
            SELECT COUNT(*) FROM svc_commission_records
            WHERE tenant_id = :tenant_id AND status IN ('failed','insufficient_credit')
            AND created_at BETWEEN :from_dt AND :to_dt
        """, p))
        summary["wallet_balance"]     = await safe_metric(_scalar(db, """
            SELECT credit_balance FROM tenant_wallets
            WHERE tenant_id = :tenant_id AND is_active = true
        """, p))
        summary["wallet_total_purchased"] = await safe_metric(_scalar(db, """
            SELECT lifetime_purchased FROM tenant_wallets
            WHERE tenant_id = :tenant_id AND is_active = true
        """, p))
        summary["wallet_total_consumed"]  = await safe_metric(_scalar(db, """
            SELECT lifetime_consumed FROM tenant_wallets
            WHERE tenant_id = :tenant_id AND is_active = true
        """, p))
        summary["refund_requested"]   = await safe_metric(_scalar(db, """
            SELECT COALESCE(SUM(requested_amount), 0) FROM refund_requests
            WHERE tenant_id = :tenant_id AND created_at BETWEEN :from_dt AND :to_dt
        """, p))
        summary["refund_recorded"]    = await safe_metric(_scalar(db, """
            SELECT COALESCE(SUM(recorded_amount), 0) FROM refund_requests
            WHERE tenant_id = :tenant_id AND status = 'recorded'
            AND created_at BETWEEN :from_dt AND :to_dt
        """, p))

        # Wallet transaction breakdown
        wallet_breakdown = await safe_metric(_rows(db, """
            SELECT txn_type, COUNT(*) AS count,
                   COALESCE(SUM(amount), 0) AS total_amount
            FROM wallet_transactions
            WHERE tenant_id = :tenant_id AND created_at BETWEEN :from_dt AND :to_dt
            GROUP BY txn_type ORDER BY count DESC
        """, p), [])

        return analytics_ok(
            summary={k: str(v) if v is not None and hasattr(v, "__float__") and not isinstance(v, (int, bool)) else v
                     for k, v in summary.items()},
            breakdown=[dict(r) for r in wallet_breakdown],
            filters_applied={"date_from": str(df), "date_to": str(dt)},
            date_from=df, date_to=dt,
        )

    # ── Provider Staff Performance ────────────────────────────────────────────

    async def get_provider_staff_performance(
        self, db: AsyncSession, tenant_id: uuid.UUID,
        date_from: str | None = None, date_to: str | None = None,
        staff_member_id: str | None = None,
    ) -> dict:
        df, dt = resolve_date_range(date_from, date_to)
        from_dt, to_dt = date_range_to_datetimes(df, dt)
        p: dict = {"tenant_id": tenant_id, "from_dt": from_dt, "to_dt": to_dt}

        staff_clause = ""
        if staff_member_id:
            staff_clause = "AND sja.assigned_staff_member_id = :staff_member_id"
            p["staff_member_id"] = uuid.UUID(staff_member_id)

        rows = await safe_metric(_rows(db, f"""
            SELECT
                sja.assigned_staff_member_id::text AS staff_id,
                COUNT(*) AS total_assignments,
                COUNT(CASE WHEN sja.assignment_status = 'accepted' THEN 1 END) AS accepted,
                COUNT(CASE WHEN sja.assignment_status = 'rejected' THEN 1 END) AS rejected,
                COUNT(CASE WHEN sja.assignment_status = 'completed' THEN 1 END) AS completed
            FROM service_job_assignments sja
            WHERE sja.tenant_id = :tenant_id
            AND sja.created_at BETWEEN :from_dt AND :to_dt
            {staff_clause}
            GROUP BY sja.assigned_staff_member_id
            ORDER BY completed DESC
            LIMIT 50
        """, p), [])

        # Enrich with team member names
        enriched = []
        for row in rows:
            sid = row["staff_id"]
            name_row = await safe_metric(_rows(db, """
                SELECT full_name, designation, status FROM provider_team_members
                WHERE id = :sid AND tenant_id = :tenant_id
            """, {"sid": uuid.UUID(sid), "tenant_id": tenant_id}), [])
            info = dict(name_row[0]) if name_row else {}
            enriched.append({**dict(row), **info})

        return analytics_ok(
            summary={"staff_count": len(enriched)},
            breakdown=enriched,
            top_items=enriched[:5],
            filters_applied={"date_from": str(df), "date_to": str(dt),
                             "staff_member_id": staff_member_id},
            date_from=df, date_to=dt,
        )

    # ── Provider Quality Summary ──────────────────────────────────────────────

    async def get_provider_quality_summary(
        self, db: AsyncSession, tenant_id: uuid.UUID,
        date_from: str | None = None, date_to: str | None = None,
    ) -> dict:
        df, dt = resolve_date_range(date_from, date_to)
        from_dt, to_dt = date_range_to_datetimes(df, dt)
        p = {"tenant_id": tenant_id, "from_dt": from_dt, "to_dt": to_dt}

        summary = {}
        summary["average_rating"]    = await safe_metric(_scalar(db, """
            SELECT ROUND(AVG(overall_rating)::numeric, 2) FROM customer_reviews
            WHERE tenant_id = :tenant_id AND status = 'approved'
            AND created_at BETWEEN :from_dt AND :to_dt
        """, p))
        summary["review_count"]      = await safe_metric(_scalar(db, """
            SELECT COUNT(*) FROM customer_reviews
            WHERE tenant_id = :tenant_id AND status = 'approved'
            AND created_at BETWEEN :from_dt AND :to_dt
        """, p))
        summary["reply_count"]       = await safe_metric(_scalar(db, """
            SELECT COUNT(*) FROM review_replies
            WHERE tenant_id = :tenant_id AND status = 'approved'
            AND created_at BETWEEN :from_dt AND :to_dt
        """, p))

        rating_dist = await safe_metric(_rows(db, """
            SELECT overall_rating AS rating, COUNT(*) AS count
            FROM customer_reviews
            WHERE tenant_id = :tenant_id AND status = 'approved'
            AND created_at BETWEEN :from_dt AND :to_dt
            GROUP BY overall_rating ORDER BY overall_rating DESC
        """, p), [])

        summary["rating_distribution"] = {str(r["rating"]): r["count"] for r in rating_dist}

        return analytics_ok(
            summary=summary,
            breakdown=[dict(r) for r in rating_dist],
            filters_applied={"date_from": str(df), "date_to": str(dt)},
            date_from=df, date_to=dt,
        )

    # ── Provider Complaint Summary ────────────────────────────────────────────

    async def get_provider_complaint_summary(
        self, db: AsyncSession, tenant_id: uuid.UUID,
        date_from: str | None = None, date_to: str | None = None,
    ) -> dict:
        df, dt = resolve_date_range(date_from, date_to)
        from_dt, to_dt = date_range_to_datetimes(df, dt)
        p = {"tenant_id": tenant_id, "from_dt": from_dt, "to_dt": to_dt}

        summary = {}
        summary["total_complaints"]    = await safe_metric(_scalar(db, """
            SELECT COUNT(*) FROM customer_complaints
            WHERE tenant_id = :tenant_id AND created_at BETWEEN :from_dt AND :to_dt
        """, p))
        summary["open_complaints"]     = await safe_metric(_scalar(db, """
            SELECT COUNT(*) FROM customer_complaints
            WHERE tenant_id = :tenant_id AND status IN ('open','investigating','awaiting_provider')
        """, p))
        summary["resolved_complaints"] = await safe_metric(_scalar(db, """
            SELECT COUNT(*) FROM customer_complaints
            WHERE tenant_id = :tenant_id AND status IN ('resolved','closed')
            AND created_at BETWEEN :from_dt AND :to_dt
        """, p))
        summary["pending_response"]    = await safe_metric(_scalar(db, """
            SELECT COUNT(*) FROM customer_complaints
            WHERE tenant_id = :tenant_id
            AND provider_response_required = true
            AND status = 'awaiting_provider'
        """, p))
        summary["rework_requests"]     = await safe_metric(_scalar(db, """
            SELECT COUNT(*) FROM service_rework_requests
            WHERE tenant_id = :tenant_id AND created_at BETWEEN :from_dt AND :to_dt
        """, p))
        summary["refund_requests"]     = await safe_metric(_scalar(db, """
            SELECT COUNT(*) FROM refund_requests
            WHERE tenant_id = :tenant_id AND created_at BETWEEN :from_dt AND :to_dt
        """, p))

        return analytics_ok(
            summary=summary,
            filters_applied={"date_from": str(df), "date_to": str(dt)},
            date_from=df, date_to=dt,
        )

    # ── Provider Operational Alerts ───────────────────────────────────────────

    async def get_provider_alerts(
        self, db: AsyncSession, tenant_id: uuid.UUID,
    ) -> dict:
        p = {"tenant_id": tenant_id}
        alerts = []

        wallet_balance = await safe_metric(_scalar(db, """
            SELECT credit_balance FROM tenant_wallets
            WHERE tenant_id = :tenant_id AND is_active = true
        """, p))
        if wallet_balance is not None:
            if float(wallet_balance) <= 0:
                alerts.append({"type": "wallet_exhausted", "balance": str(wallet_balance),
                               "severity": "critical"})
            elif float(wallet_balance) < 500:
                alerts.append({"type": "low_wallet", "balance": str(wallet_balance),
                               "severity": "warning"})

        open_complaints = await safe_metric(_scalar(db, """
            SELECT COUNT(*) FROM customer_complaints
            WHERE tenant_id = :tenant_id AND status IN ('open','investigating','awaiting_provider')
        """, p))
        if open_complaints:
            alerts.append({"type": "open_complaints", "count": open_complaints, "severity": "warning"})

        pending_assignments = await safe_metric(_scalar(db, """
            SELECT COUNT(*) FROM service_jobs
            WHERE tenant_id = :tenant_id AND assignment_status = 'unassigned'
            AND status = 'pending_assignment'
        """, p))
        if pending_assignments:
            alerts.append({"type": "pending_assignments", "count": pending_assignments,
                           "severity": "info"})

        pending_refunds = await safe_metric(_scalar(db, """
            SELECT COUNT(*) FROM refund_requests
            WHERE tenant_id = :tenant_id AND status = 'pending'
        """, p))
        if pending_refunds:
            alerts.append({"type": "pending_refunds", "count": pending_refunds, "severity": "warning"})

        unread_critical = await safe_metric(_scalar(db, """
            SELECT COUNT(*) FROM in_app_notifications
            WHERE tenant_id = :tenant_id AND read_status = 'unread' AND severity = 'critical'
        """, p))
        if unread_critical:
            alerts.append({"type": "unread_critical_notifications", "count": unread_critical,
                           "severity": "critical"})

        return analytics_ok(
            summary={"alert_count": len(alerts)},
            top_items=alerts,
            filters_applied={},
        )


# ── SQL helpers ───────────────────────────────────────────────────────────────

async def _scalar(db: AsyncSession, sql: str, params: dict | None = None):
    result = await db.execute(text(sql), params or {})
    return result.scalar_one_or_none()


async def _rows(db: AsyncSession, sql: str, params: dict | None = None):
    result = await db.execute(text(sql), params or {})
    return result.mappings().all()
