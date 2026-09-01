"""Home Services admin command-center service layer.

The dashboard reads canonical booking, job, provider-visibility, finance,
complaint, refund, warranty, security, and audit sources. Platform revenue is
funded top-up revenue; customer-to-provider service value remains separate.
"""
from __future__ import annotations
import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ServiceOSException
from app.engines.analytics.platform_service import (
    PlatformAnalyticsService, _safe_count, _safe_scalar, _safe_rows, _date_defaults,
)
from app.engine_registry.registry import registry

_utcnow = lambda: datetime.now(timezone.utc)
_analytics = PlatformAnalyticsService()

# Curated engine list (Part J) mapped to real engine_registry ids where one
# exists; engines with no direct backend counterpart are honestly reported
# as "not_configured" rather than faked.
_ENGINE_DISPLAY = [
    ("Auth & IAM", "auth"),
    ("Tenant Engine", "tenant"),
    ("Catalog Engine", "service_catalog"),
    ("Pricing Engine", "pricing"),
    ("Booking Engine", "booking"),
    ("Workflow Engine", "workflow"),
    ("Field Ops Engine", "field_ops"),
    ("Finance / Usage Credit Engine", "platform_commerce"),
    ("Notification Engine", "notification"),
    ("Media Vault", "media"),
    ("Trust & Quality", "trust_quality"),
    ("Compliance Engine", "compliance"),
    ("Marketing Engine", "marketing"),
    ("Intelligence Engine", "data_science"),
    ("Audit Engine", "audit"),
]

# A provider needs admin attention when a real operational control is failing.
# This replaces the retired health_scores projection. Every source is
# tenant-scoped before the final join, avoiding row multiplication at scale.
_PROVIDER_ATTENTION_CTE = """
    WITH complaint_signal AS (
        SELECT tenant_id,
               COUNT(*) FILTER (WHERE status NOT IN ('resolved','closed','cancelled')) AS open_count,
               COUNT(*) FILTER (
                   WHERE status NOT IN ('resolved','closed','cancelled')
                     AND created_at < NOW() - INTERVAL '3 days'
               ) AS overdue_count
        FROM customer_complaints
        WHERE created_at > NOW() - INTERVAL '90 days'
        GROUP BY tenant_id
    ), deduction_signal AS (
        SELECT sj.tenant_id,
               COUNT(*) FILTER (WHERE ucl.id IS NULL) AS missing_count
        FROM service_jobs sj
        LEFT JOIN usage_credit_ledger ucl
          ON ucl.job_id = sj.id AND ucl.event_type = 'completed_job_deduction'
        WHERE sj.status = 'completed'
          AND sj.updated_at > NOW() - INTERVAL '30 days'
        GROUP BY sj.tenant_id
    ), provider_signals AS (
        SELECT t.id, COALESCE(t.business_name, t.tenant_name, t.tenant_code, 'Unnamed provider') AS business_name,
               t.vertical, t.updated_at,
               COALESCE(pvs.is_bookable, false) AS is_bookable,
               COALESCE(tb.credit_balance, 0) AS credit_balance,
               COALESCE(cs.open_count, 0) AS open_complaints,
               COALESCE(cs.overdue_count, 0) AS overdue_complaints,
               COALESCE(ds.missing_count, 0) AS missing_deductions,
               CASE
                 WHEN COALESCE(ds.missing_count, 0) > 0 OR COALESCE(cs.overdue_count, 0) > 0 THEN 'critical'
                 WHEN COALESCE(pvs.is_bookable, false) = false OR COALESCE(cs.open_count, 0) > 0 THEN 'high'
                 WHEN COALESCE(tb.credit_balance, 0) < 500 THEN 'medium'
                 ELSE 'normal'
               END AS risk_level
        FROM tenants t
        LEFT JOIN provider_visibility_statuses pvs ON pvs.tenant_id = t.id
        LEFT JOIN tenant_billing tb ON tb.tenant_id = t.id
        LEFT JOIN complaint_signal cs ON cs.tenant_id = t.id
        LEFT JOIN deduction_signal ds ON ds.tenant_id = t.id
        WHERE t.vertical = 'home_services' AND t.status = 'active'
          AND t.terminated_at IS NULL AND t.archived_at IS NULL
    )
"""


class DashboardCommandCenterService:
    def __init__(self, db: AsyncSession, actor_id: uuid.UUID | None = None,
                 actor_role: str | None = None, request_id: str | None = None):
        self.db = db
        self.actor_id = actor_id
        self.actor_role = actor_role
        self.request_id = request_id

    @staticmethod
    def _health_payload(signals: dict[str, Any]) -> dict[str, Any]:
        reasons: list[str] = []
        score = 100
        unhealthy = sum(1 for engine in registry.all() if not getattr(engine, "is_healthy", True))
        if unhealthy:
            score -= min(20, unhealthy * 5)
            reasons.append(f"{unhealthy} engine(s) reporting unhealthy")
        pending = int(signals.get("pending_tenants") or 0)
        if pending > 10:
            score -= 10; reasons.append(f"{pending} tenants awaiting approval (backlog)")
        missing = int(signals.get("failed_deductions") or 0)
        if missing:
            score -= min(15, missing * 2); reasons.append(f"{missing} missing usage-credit deduction(s) in last 7 days")
        threats = int(signals.get("open_threats") or 0)
        if threats:
            score -= min(20, threats * 10); reasons.append(f"{threats} open security threat(s)")
        overdue = int(signals.get("overdue_complaints") or 0)
        if overdue:
            score -= min(10, overdue); reasons.append(f"{overdue} complaint(s) past response SLA")
        score = max(0, min(100, score))
        status = "healthy" if score >= 90 else "good" if score >= 75 else "warning" if score >= 60 else "degraded" if score >= 40 else "critical"
        return {"score": score, "status": status, "reasons": reasons or ["All core engines operational"],
                "recommended_actions": ["Review pending admin actions"] if score < 90 else []}

    # ── Part C: Executive Summary ───────────────────────────────────────────

    async def get_executive_summary(self, **filters) -> dict[str, Any]:
        rows = await _safe_rows(self.db, _PROVIDER_ATTENTION_CTE + """
            SELECT
              (SELECT COUNT(*) FROM tenants WHERE vertical='home_services' AND status='active') AS active_tenants,
              (SELECT COUNT(*) FROM tenants WHERE vertical='home_services' AND status='active' AND created_at > NOW()-INTERVAL '30 days') AS new_tenants,
              (SELECT COUNT(*) FROM provider_signals WHERE is_bookable=true) AS bookable,
              (SELECT COUNT(*) FROM service_jobs WHERE status NOT IN ('completed','cancelled')) AS live_jobs,
              (SELECT COUNT(*) FROM service_bookings WHERE created_at>=CURRENT_DATE AND created_at<CURRENT_DATE+INTERVAL '1 day') AS today_bookings,
              (SELECT COUNT(*) FROM tenants WHERE status IN ('pending_review','onboarding_pending')) AS pending_tenants,
              (SELECT COUNT(*) FROM tenants WHERE verification_status='changes_pending_review' AND meta->>'pending_changes' IS NOT NULL AND terminated_at IS NULL AND archived_at IS NULL) AS pending_changes,
              (SELECT COUNT(*) FROM customer_complaints WHERE status NOT IN ('resolved','closed','cancelled')) AS open_complaints,
              (SELECT COUNT(*) FROM customer_complaints WHERE status NOT IN ('resolved','closed','cancelled') AND created_at<NOW()-INTERVAL '3 days') AS overdue_complaints,
              (SELECT COUNT(*) FROM dispute_settlements WHERE settlement_status NOT IN ('executed','cancelled')) AS open_disputes,
              (SELECT COUNT(*) FROM warranty_claims WHERE status='admin_review') AS warranty_escalations,
              (SELECT COUNT(*) FROM refund_requests WHERE escalated_at IS NOT NULL AND status NOT IN ('closed','cancelled','rejected','credit_issued')) AS refund_escalations,
              (SELECT COUNT(*) FROM provider_signals WHERE risk_level IN ('high','critical')) AS attention_count,
              (SELECT COUNT(*) FROM provider_signals WHERE risk_level='critical') AS critical_attention,
              (SELECT COUNT(*) FROM suspicious_activity_logs WHERE status='open') AS open_threats,
              (SELECT COUNT(*) FROM service_jobs sj LEFT JOIN usage_credit_ledger ucl ON ucl.job_id=sj.id AND ucl.event_type='completed_job_deduction' WHERE sj.status='completed' AND sj.updated_at>NOW()-INTERVAL '7 days' AND ucl.id IS NULL) AS failed_deductions
        """)
        row = rows[0] if rows else {}
        health = self._health_payload(row)
        pending_actions = sum(int(row.get(key) or 0) for key in ("pending_tenants","pending_changes","open_complaints","open_disputes","warranty_escalations","refund_escalations"))

        return {
            "platform_health": {"score": health["score"], "status": health["status"]},
            "active_tenants": {"count": int(row.get("active_tenants") or 0), "new_this_month": int(row.get("new_tenants") or 0), "bookable": int(row.get("bookable") or 0)},
            "live_operations": {"total": int(row.get("live_jobs") or 0)+int(row.get("today_bookings") or 0), "jobs": int(row.get("live_jobs") or 0), "bookings": int(row.get("today_bookings") or 0), "leads": 0},
            "pending_admin_actions": {"count": pending_actions, "approvals": int(row.get("pending_tenants") or 0)+int(row.get("pending_changes") or 0), "complaints": int(row.get("open_complaints") or 0), "disputes": int(row.get("open_disputes") or 0)},
            "at_risk_tenants": {"count": int(row.get("attention_count") or 0), "high_risk": int(row.get("critical_attention") or 0)},
            "critical_alerts": {"count": int(row.get("open_threats") or 0), "open_threats": int(row.get("open_threats") or 0)},
        }

    # ── Part D: Platform Health Score ───────────────────────────────────────

    async def get_platform_health(self) -> dict[str, Any]:
        rows = await _safe_rows(self.db, """
            SELECT
              (SELECT COUNT(*) FROM tenants WHERE status IN ('pending_review','onboarding_pending')) AS pending_tenants,
              (SELECT COUNT(*) FROM service_jobs sj LEFT JOIN usage_credit_ledger ucl ON ucl.job_id=sj.id AND ucl.event_type='completed_job_deduction' WHERE sj.status='completed' AND sj.updated_at>NOW()-INTERVAL '7 days' AND ucl.id IS NULL) AS failed_deductions,
              (SELECT COUNT(*) FROM suspicious_activity_logs WHERE status='open') AS open_threats,
              (SELECT COUNT(*) FROM customer_complaints WHERE status NOT IN ('resolved','closed','cancelled') AND created_at<NOW()-INTERVAL '3 days') AS overdue_complaints
        """)
        return self._health_payload(rows[0] if rows else {})

    # ── Part E: Finance Snapshot ─────────────────────────────────────────────

    async def get_finance_snapshot(self, date_from: str | None = None, date_to: str | None = None,
                                    vertical: str | None = None) -> dict[str, Any]:
        from_dt, to_dt = _date_defaults(date_from, date_to)
        p = {"f": from_dt, "t": to_dt}
        topups = await _safe_scalar(self.db, """
            SELECT COALESCE(SUM(cto.amount_paid - COALESCE(cto.refunded_amount, 0)), 0)
            FROM credit_topup_orders cto
            JOIN tenants t ON t.id = cto.tenant_id
            WHERE t.vertical = 'home_services'
              AND cto.payment_status IN ('credited','partially_refunded')
              AND cto.created_at BETWEEN :f AND :t
        """, p)
        deductions = await _safe_scalar(self.db, """
            SELECT COALESCE(SUM(-ucl.credit_delta), 0)
            FROM usage_credit_ledger ucl
            JOIN tenants t ON t.id = ucl.tenant_id
            WHERE t.vertical = 'home_services'
              AND ucl.event_type IN ('completed_job_deduction','customer_platform_charge_recovery')
              AND ucl.created_at BETWEEN :f AND :t
        """, p)
        provider_direct_value = await _safe_scalar(self.db, """
            SELECT COALESCE(SUM(si.total_amount), 0)
            FROM service_invoices si
            JOIN tenants t ON t.id = si.tenant_id
            WHERE t.vertical = 'home_services'
              AND si.status <> 'cancelled'
              AND si.payment_status IN ('collected','verified','paid')
              AND si.created_at BETWEEN :f AND :t
        """, p)
        credits_issued = await _safe_scalar(self.db, """
            SELECT COALESCE(SUM(csc.amount), 0)
            FROM customer_service_credits csc
            JOIN tenants t ON t.id = csc.tenant_id
            WHERE t.vertical = 'home_services' AND csc.created_at BETWEEN :f AND :t
        """, p)
        missing_deductions = await _safe_count(self.db, """
            SELECT COUNT(*) FROM service_jobs sj
            LEFT JOIN usage_credit_ledger ucl
              ON ucl.job_id = sj.id AND ucl.event_type = 'completed_job_deduction'
            WHERE sj.status = 'completed' AND sj.updated_at BETWEEN :f AND :t AND ucl.id IS NULL
        """, p)
        return {
            "platform_revenue": float(topups or 0), "usage_credit_topups": float(topups or 0),
            "completed_job_deductions": float(deductions or 0),
            "customer_service_credits_issued": float(credits_issued or 0),
            "security_deposits_held": 0.0,
            "failed_deductions": missing_deductions,
            "provider_direct_service_value": float(provider_direct_value or 0),
        }

    # ── Part F: Tenant Lifecycle Snapshot ────────────────────────────────────

    async def get_tenant_lifecycle(self) -> dict[str, Any]:
        new_requests = await _safe_count(self.db, "SELECT COUNT(*) FROM tenants WHERE status = 'onboarding_pending'")
        pending_review = await _safe_count(self.db, "SELECT COUNT(*) FROM tenants WHERE status = 'pending_review'")
        changes_requested = await _safe_count(self.db, "SELECT COUNT(*) FROM tenants WHERE status = 'changes_requested'")
        approved_week = await _safe_count(self.db,
            "SELECT COUNT(*) FROM tenants WHERE verification_status IN ('approved','verified') AND updated_at > NOW() - INTERVAL '7 days'")
        suspended = await _safe_count(self.db, "SELECT COUNT(*) FROM tenants WHERE status = 'suspended'")
        bookable = await _safe_count(self.db, """
            SELECT COUNT(*) FROM tenants t JOIN provider_visibility_statuses p ON p.tenant_id=t.id
            WHERE t.vertical='home_services' AND t.status='active' AND p.is_bookable=true
        """)
        active_hs = await _safe_count(self.db,
            "SELECT COUNT(*) FROM tenants WHERE vertical='home_services' AND status='active'")
        non_bookable = max(active_hs - bookable, 0)

        return {
            "new_tenant_requests": new_requests, "pending_review": pending_review,
            "changes_requested": changes_requested, "approved_this_week": approved_week,
            "suspended": suspended, "bookable_tenants": bookable, "non_bookable_tenants": non_bookable,
        }

    # ── Part G: Operations Snapshot / Live Operations ────────────────────────

    async def get_operations_snapshot(self, vertical: str | None = None) -> dict[str, Any]:
        live_jobs = await _safe_count(self.db,
            "SELECT COUNT(*) FROM service_jobs WHERE status NOT IN ('completed','cancelled')")
        today_bookings = await _safe_count(self.db, """
            SELECT COUNT(*) FROM service_bookings
            WHERE created_at >= CURRENT_DATE AND created_at < CURRENT_DATE + INTERVAL '1 day'
        """)
        pending_acceptance = await _safe_count(self.db,
            "SELECT COUNT(*) FROM service_jobs WHERE status = 'pending_assignment'")
        technicians_on_duty = await _safe_count(self.db,
            "SELECT COUNT(DISTINCT assigned_staff_id) FROM service_jobs WHERE status NOT IN ('completed','cancelled') AND assigned_staff_id IS NOT NULL")
        sla_breaches = await _safe_count(self.db, """
            SELECT COUNT(*) FROM customer_complaints
            WHERE status NOT IN ('resolved','closed','cancelled') AND sla_status = 'breached'
        """)

        return {
            "live_jobs": live_jobs, "today_bookings": today_bookings,
            "pending_provider_acceptance": pending_acceptance, "technicians_on_duty": technicians_on_duty,
            "appointments_today": 0, "leads_today": 0,
            "orders_today": 0, "sla_breaches": sla_breaches,
        }

    async def get_live_operations(self, limit: int = 30) -> dict[str, Any]:
        rows = await _safe_rows(self.db, """
            SELECT j.id, j.job_number AS item, t.vertical, t.business_name AS tenant,
                   j.status, false AS sla_breach, j.assigned_staff_id, j.updated_at
            FROM service_jobs j
            LEFT JOIN tenants t ON t.id = j.tenant_id
            WHERE j.status NOT IN ('completed', 'cancelled')
            ORDER BY j.updated_at DESC
            LIMIT :limit
        """, {"limit": limit})
        items = [{
            "id": str(r["id"]), "item": r["item"], "vertical": r.get("vertical"),
            "tenant": r.get("tenant"), "status": r["status"], "sla_breach": bool(r.get("sla_breach")),
            "assigned_to": str(r["assigned_staff_id"]) if r.get("assigned_staff_id") else None,
            "updated_at": r["updated_at"].isoformat() if r.get("updated_at") else None,
        } for r in rows]
        return {"items": items}

    # ── Part H: Trends ───────────────────────────────────────────────────────

    async def get_trends(self, date_from: str | None = None, date_to: str | None = None,
                          vertical: str | None = None) -> dict[str, Any]:
        from_dt, to_dt = _date_defaults(date_from, date_to)
        p = {"f": from_dt, "t": to_dt}
        jobs = await _safe_rows(self.db, """
            SELECT DATE_TRUNC('day', created_at)::date::text AS date, COUNT(*) AS value
            FROM service_jobs WHERE created_at BETWEEN :f AND :t GROUP BY 1 ORDER BY 1
        """, p)
        revenue = await _safe_rows(self.db, """
            SELECT DATE_TRUNC('day', cto.created_at)::date::text AS date,
                   COALESCE(SUM(cto.amount_paid - COALESCE(cto.refunded_amount,0)),0) AS value
            FROM credit_topup_orders cto JOIN tenants t ON t.id=cto.tenant_id
            WHERE t.vertical='home_services' AND cto.payment_status IN ('credited','partially_refunded')
              AND cto.created_at BETWEEN :f AND :t GROUP BY 1 ORDER BY 1
        """, p)
        tenant_growth = await _safe_rows(self.db, """
            SELECT DATE_TRUNC('day', created_at)::date::text AS date, COUNT(*) AS value
            FROM tenants WHERE vertical='home_services' AND created_at BETWEEN :f AND :t GROUP BY 1 ORDER BY 1
        """, p)
        complaints = await _safe_rows(self.db, """
            SELECT DATE_TRUNC('day', created_at)::date::text AS date, COUNT(*) AS value
            FROM customer_complaints WHERE created_at BETWEEN :f AND :t GROUP BY 1 ORDER BY 1
        """, p)
        deductions_trend = await _safe_rows(self.db, """
            SELECT DATE_TRUNC('day', ucl.created_at)::date::text AS date, COALESCE(SUM(-ucl.credit_delta),0) AS value
            FROM usage_credit_ledger ucl JOIN tenants t ON t.id=ucl.tenant_id
            WHERE t.vertical='home_services'
              AND ucl.event_type IN ('completed_job_deduction','customer_platform_charge_recovery')
              AND ucl.created_at BETWEEN :f AND :t
            GROUP BY 1 ORDER BY 1
        """, {"f": from_dt, "t": to_dt})
        direct_value_trend = await _safe_rows(self.db, """
            SELECT DATE_TRUNC('day', si.created_at)::date::text AS date, COALESCE(SUM(si.total_amount),0) AS value
            FROM service_invoices si JOIN tenants t ON t.id=si.tenant_id
            WHERE t.vertical='home_services' AND si.status <> 'cancelled'
              AND si.payment_status IN ('collected','verified','paid') AND si.created_at BETWEEN :f AND :t
            GROUP BY 1 ORDER BY 1
        """, {"f": from_dt, "t": to_dt})
        points = lambda rows: [{"date": r["date"], "value": float(r["value"])} for r in rows]
        return {
            "jobs_trend": points(jobs), "revenue_trend": points(revenue),
            "tenant_growth": points(tenant_growth), "complaint_trend": points(complaints),
            "completed_job_deductions_trend": points(deductions_trend),
            "provider_direct_service_value_trend": points(direct_value_trend),
        }

    # ── Part I: Action Queue ─────────────────────────────────────────────────

    async def get_action_queue(self, limit: int = 50) -> dict[str, Any]:
        alerts = await _analytics.get_operational_alerts(self.db, limit=200)
        items: list[dict] = []
        for a in alerts["items"]:
            items.append({
                "action_id": a["id"], "priority": "critical" if a["severity"] == "critical" else "high",
                "action": a["message"], "entity_type": a["entity_type"], "entity_id": a["entity_id"],
                "vertical": a.get("vertical"), "age_hours": None, "status": a["status"],
            })

        low_credit = await _safe_rows(self.db, """
            SELECT t.id, t.business_name, t.vertical, b.credit_balance
            FROM tenant_billing b JOIN tenants t ON t.id = b.tenant_id
            WHERE b.credit_balance < 500 AND t.status = 'active' AND t.vertical='home_services'
            LIMIT 20
        """)
        for r in low_credit:
            items.append({
                "action_id": f"action_low_credit_{r['id']}", "priority": "high",
                "action": f"{r['business_name']} has low usage credit balance (₹{r['credit_balance']})",
                "entity_type": "tenant", "entity_id": str(r["id"]), "vertical": r.get("vertical"),
                "age_hours": None, "status": "open",
            })

        failed_deductions = await _safe_rows(self.db, """
            SELECT sj.id, t.business_name, t.vertical, sj.id AS job_id
            FROM service_jobs sj JOIN tenants t ON t.id = sj.tenant_id
            LEFT JOIN usage_credit_ledger ucl
              ON ucl.job_id=sj.id AND ucl.event_type='completed_job_deduction'
            WHERE sj.status='completed' AND ucl.id IS NULL
              AND sj.updated_at > NOW() - INTERVAL '30 days'
            ORDER BY sj.updated_at DESC LIMIT 20
        """)
        for r in failed_deductions:
            items.append({
                "action_id": f"action_failed_deduction_{r['id']}", "priority": "critical",
                "action": f"Failed completed-job deduction for {r['business_name']}",
                "entity_type": "job", "entity_id": str(r["job_id"]) if r.get("job_id") else None,
                "vertical": r.get("vertical"), "age_hours": None, "status": "open",
            })

        profile_changes = await _safe_rows(self.db, """
            SELECT id, business_name, vertical FROM tenants
            WHERE verification_status='changes_pending_review'
              AND meta ->> 'pending_changes' IS NOT NULL
              AND terminated_at IS NULL AND archived_at IS NULL
            ORDER BY updated_at DESC LIMIT 20
        """)
        for r in profile_changes:
            items.append({
                "action_id": f"action_profile_change_{r['id']}", "priority": "high",
                "action": f"Review verified profile change for {r['business_name']}",
                "entity_type": "tenant", "entity_id": str(r["id"]), "vertical": r.get("vertical"),
                "age_hours": None, "status": "open",
            })

        escalations = await _safe_rows(self.db, """
            SELECT 'warranty' AS kind, wc.id, wc.tenant_id, t.business_name, t.vertical
              FROM warranty_claims wc JOIN tenants t ON t.id=wc.tenant_id
             WHERE wc.status='admin_review'
            UNION ALL
            SELECT 'refund' AS kind, rr.id, rr.tenant_id, t.business_name, t.vertical
              FROM refund_requests rr JOIN tenants t ON t.id=rr.tenant_id
             WHERE rr.escalated_at IS NOT NULL
               AND rr.status NOT IN ('closed','cancelled','rejected','credit_issued')
            LIMIT 20
        """)
        for r in escalations:
            items.append({
                "action_id": f"action_{r['kind']}_{r['id']}", "priority": "critical",
                "action": f"Admin {r['kind']} escalation for {r['business_name']}",
                "entity_type": r["kind"], "entity_id": str(r["id"]), "vertical": r.get("vertical"),
                "age_hours": None, "status": "open",
            })

        # Apply persisted overrides (resolve/snooze/assign)
        overrides = await _safe_rows(self.db, "SELECT action_key, status, snoozed_until FROM dashboard_action_states")
        override_map = {o["action_key"]: o for o in overrides}
        now = _utcnow()
        visible = []
        for item in items:
            ov = override_map.get(item["action_id"])
            if ov:
                if ov["status"] == "resolved":
                    continue
                if ov["status"] == "snoozed" and ov.get("snoozed_until") and ov["snoozed_until"] > now:
                    continue
            visible.append(item)

        return {"items": visible[:limit], "total": len(visible)}

    async def resolve_action(self, action_id: str, reason: str | None = None) -> dict[str, Any]:
        await self._upsert_action_state(action_id, status="resolved", resolved_by=self.actor_id, reason=reason)
        return {"action_id": action_id, "status": "resolved"}

    async def snooze_action(self, action_id: str, hours: int = 24) -> dict[str, Any]:
        snoozed_until = _utcnow() + timedelta(hours=hours)
        await self._upsert_action_state(action_id, status="snoozed", snoozed_until=snoozed_until)
        return {"action_id": action_id, "status": "snoozed", "snoozed_until": snoozed_until.isoformat()}

    async def assign_action(self, action_id: str, assigned_to_user_id: str) -> dict[str, Any]:
        await self._upsert_action_state(action_id, status="assigned", assigned_to=assigned_to_user_id)
        return {"action_id": action_id, "status": "assigned", "assigned_to_user_id": assigned_to_user_id}

    async def _upsert_action_state(self, action_key: str, *, status: str,
                                    assigned_to: str | None = None, snoozed_until=None,
                                    resolved_by=None, reason: str | None = None) -> None:
        await self.db.execute(text("""
            INSERT INTO dashboard_action_states
                (action_key, status, assigned_to_user_id, snoozed_until, resolved_at, resolved_by_user_id, resolution_reason, updated_at)
            VALUES (:key, :status, :assigned_to, :snoozed_until,
                    CASE WHEN :status = 'resolved' THEN now() ELSE NULL END,
                    :resolved_by, :reason, now())
            ON CONFLICT (action_key) DO UPDATE SET
                status = :status, assigned_to_user_id = COALESCE(:assigned_to, dashboard_action_states.assigned_to_user_id),
                snoozed_until = :snoozed_until,
                resolved_at = CASE WHEN :status = 'resolved' THEN now() ELSE dashboard_action_states.resolved_at END,
                resolved_by_user_id = COALESCE(:resolved_by, dashboard_action_states.resolved_by_user_id),
                resolution_reason = COALESCE(:reason, dashboard_action_states.resolution_reason),
                updated_at = now()
        """), {"key": action_key, "status": status, "assigned_to": assigned_to,
               "snoozed_until": snoozed_until, "resolved_by": resolved_by, "reason": reason})
        await self.db.commit()

    # ── Part J: Engine Health ────────────────────────────────────────────────

    async def get_engine_health(self) -> dict[str, Any]:
        db_ok = await _safe_scalar(self.db, "SELECT 1") == 1
        engines_by_id = {e.engine_id: e for e in registry.all()}
        items = []
        for label, engine_id in _ENGINE_DISPLAY:
            if engine_id is None:
                items.append({"name": label, "status": "not_configured", "latency_ms": None,
                              "error_rate": None, "last_check": None})
                continue
            e = engines_by_id.get(engine_id)
            if not e:
                items.append({"name": label, "status": "not_configured", "latency_ms": None,
                              "error_rate": None, "last_check": None})
                continue
            status = "healthy" if (getattr(e, "is_healthy", True) and db_ok) else "degraded"
            items.append({
                "name": label, "status": status,
                "latency_ms": getattr(e, "avg_latency_ms", None),
                "error_rate": getattr(e, "error_rate", None),
                "last_check": _utcnow().isoformat(),
            })
        return {"items": items, "note": "Status derived from engine registration state + live DB connectivity check; "
                                         "no dedicated per-engine heartbeat telemetry exists yet."}

    # ── Part K: At-Risk Tenants ──────────────────────────────────────────────

    async def get_at_risk_tenants(self, limit: int = 50) -> dict[str, Any]:
        rows = await _safe_rows(self.db, _PROVIDER_ATTENTION_CTE + """
            SELECT * FROM provider_signals
            WHERE risk_level IN ('high','critical','medium')
            ORDER BY CASE risk_level WHEN 'critical' THEN 1 WHEN 'high' THEN 2 ELSE 3 END,
                     updated_at DESC, id
            LIMIT :limit
        """, {"limit": limit})
        items = []
        for r in rows:
            reason = ("Missing completed-job deduction" if r.get("missing_deductions") else
                      "Complaint response SLA breached" if r.get("overdue_complaints") else
                      "Provider is not bookable" if not r.get("is_bookable") else
                      "Open customer complaint" if r.get("open_complaints") else
                      "Usage credit balance below 500")
            items.append({
                "tenant_id": str(r["id"]), "tenant_name": r["business_name"], "vertical": r.get("vertical"),
                "risk_level": r["risk_level"], "health_score": None,
                "top_reason": reason, "credit_balance": float(r["credit_balance"]) if r.get("credit_balance") is not None else None,
                "last_activity": r["updated_at"].isoformat() if r.get("updated_at") else None,
            })
        return {"items": items}

    # ── Part L: Compliance & Security ────────────────────────────────────────

    async def get_compliance_security(self) -> dict[str, Any]:
        dpdp_pending = await _safe_count(self.db, "SELECT COUNT(*) FROM compliance_requests WHERE status = 'pending'")
        export_requests = await _safe_count(self.db, "SELECT COUNT(*) FROM data_portability_requests WHERE status = 'pending'")
        deletion_requests = await _safe_count(self.db, "SELECT COUNT(*) FROM data_deletion_requests WHERE status = 'pending'")
        open_threats = await _safe_count(self.db, "SELECT COUNT(*) FROM suspicious_activity_logs WHERE status = 'open'")
        failed_logins = await _safe_count(self.db,
            "SELECT COUNT(*) FROM login_events WHERE success = false AND created_at > NOW() - INTERVAL '24 hours'")
        return {
            "dpdp_requests_pending": dpdp_pending, "data_export_requests": export_requests,
            "deletion_requests": deletion_requests, "consent_issues": 0,
            "open_threats": open_threats, "failed_logins": failed_logins,
            "mfa_gaps": 0, "suspicious_sessions": 0,
        }

    # ── Part L2: Home Services Summary ───────────────────────────────────────
    # Shown as its own dashboard section (never merged into the generic
    # tenant/operations cards) per the Home Services menu-isolation rule
    # established earlier this session — see HOME_SERVICES_MENU_ORGANIZATION_REPORT.md.

    async def get_home_services_summary(self) -> dict[str, Any]:
        hs_providers = await _safe_count(self.db,
            "SELECT COUNT(*) FROM tenants WHERE vertical = 'home_services'")
        bookable = await _safe_count(self.db, """
            SELECT COUNT(*) FROM tenants t
            JOIN provider_visibility_statuses pvs ON pvs.tenant_id = t.id
            WHERE t.vertical = 'home_services' AND pvs.is_bookable = true
        """)
        not_bookable = max(hs_providers - bookable, 0)

        catalog_services = await _safe_count(self.db, """
            SELECT COUNT(*) FROM master_services ms
            JOIN service_categories sc ON sc.id = ms.category_id
            WHERE sc.vertical_type = 'home_services' AND ms.is_active = true AND ms.deleted_at IS NULL
        """)
        monetization_policies = await _safe_count(self.db, """
            SELECT COUNT(*) FROM vertical_monetization_policies vmp
            JOIN verticals v ON v.id = vmp.vertical_id
            WHERE v.key='home_services' AND vmp.is_current=true AND vmp.status='published'
        """)
        published_tenant_services = await _safe_count(self.db, """
            SELECT COUNT(*) FROM tenant_services ts
            JOIN service_categories sc ON sc.id = ts.category_id
            WHERE sc.vertical_type = 'home_services' AND ts.setup_status = 'published' AND ts.deleted_at IS NULL
        """)
        active_service_areas = await _safe_count(self.db, """
            SELECT COUNT(*) FROM tenant_service_areas tsa
            JOIN tenants t ON t.id = tsa.tenant_id
            WHERE t.vertical = 'home_services' AND tsa.is_active = true
        """)
        tenants_without_areas = max(hs_providers - await _safe_count(self.db, """
            SELECT COUNT(DISTINCT tsa.tenant_id) FROM tenant_service_areas tsa
            JOIN tenants t ON t.id = tsa.tenant_id
            WHERE t.vertical = 'home_services' AND tsa.is_active = true
        """), 0)

        def _health(ok_count: int, total: int) -> str:
            if total == 0:
                return "not_configured"
            ratio = ok_count / total
            if ratio >= 0.9:
                return "healthy"
            if ratio >= 0.5:
                return "warning"
            return "critical"

        return {
            "home_services_providers": hs_providers,
            "bookable_providers": bookable,
            "not_bookable_providers": not_bookable,
            "service_catalog_health": {
                "status": "healthy" if catalog_services > 0 else "not_configured",
                "active_services": catalog_services,
            },
            "pricing_rule_health": {
                "status": "healthy" if monetization_policies > 0 else "warning",
                "active_rules": monetization_policies,
            },
            "provider_coverage_health": {
                "status": _health(hs_providers - tenants_without_areas, hs_providers),
                "active_areas": active_service_areas,
                "tenants_without_areas": tenants_without_areas,
            },
            "provider_bookability_health": {
                "status": _health(bookable, hs_providers),
                "bookable_providers": bookable,
                "not_bookable_providers": not_bookable,
            },
            "auto_price_options_health": "retired",
            "completed_job_deduction_health": "healthy" if monetization_policies > 0 else "not_configured",
            "published_tenant_services": published_tenant_services,
        }

    # ── Part M: Trust & Quality ──────────────────────────────────────────────

    async def get_trust_quality(self) -> dict[str, Any]:
        avg_rating = await _safe_scalar(self.db, """
            SELECT COALESCE(AVG(cr.overall_rating),0) FROM customer_reviews cr
            JOIN tenants t ON t.id=cr.tenant_id
            WHERE t.vertical='home_services' AND cr.status <> 'deleted'
        """)
        completed_jobs = await _safe_count(self.db,
            "SELECT COUNT(*) FROM service_jobs WHERE status='completed'")
        complaint_count = await _safe_count(self.db, """
            SELECT COUNT(*) FROM customer_complaints cc JOIN tenants t ON t.id=cc.tenant_id
            WHERE t.vertical='home_services'
        """)
        dispute_count = await _safe_count(self.db, """
            SELECT COUNT(*) FROM dispute_settlements ds JOIN tenants t ON t.id=ds.tenant_id
            WHERE t.vertical='home_services'
        """)
        sla_breaches = await _safe_count(self.db, """
            SELECT COUNT(*) FROM customer_complaints cc JOIN tenants t ON t.id=cc.tenant_id
            WHERE t.vertical='home_services' AND cc.sla_status='breached'
        """)
        service_credits = await _safe_scalar(self.db, """
            SELECT COALESCE(SUM(csc.amount),0) FROM customer_service_credits csc
            JOIN tenants t ON t.id=csc.tenant_id WHERE t.vertical='home_services'
        """)
        badges_week = await _safe_count(self.db,
            "SELECT COUNT(*) FROM badge_assignments WHERE created_at > NOW() - INTERVAL '7 days'")
        risk = await _safe_rows(self.db, _PROVIDER_ATTENTION_CTE + """
            SELECT COUNT(*) AS count FROM provider_signals WHERE risk_level IN ('high','critical')
        """)
        providers_under_review = int(risk[0]["count"] or 0) if risk else 0
        denominator = max(completed_jobs, 1)
        return {
            "avg_rating": round(float(avg_rating or 0), 1),
            "complaint_rate": round(complaint_count / denominator * 100, 2),
            "dispute_rate": round(dispute_count / denominator * 100, 2),
            "sla_success_rate": round(max(0, 100 - (sla_breaches / max(complaint_count, 1) * 100)), 2),
            "customer_service_credits_issued": float(service_credits or 0),
            "providers_under_review": providers_under_review,
            "badge_awards_this_week": badges_week, "health_recalculations": 0,
        }

    # ── Part N: Activity Feed ────────────────────────────────────────────────

    async def get_activity_feed(self, limit: int = 30) -> dict[str, Any]:
        rows = await _safe_rows(self.db, """
            SELECT id, actor_id, actor_role, operation, engine_id, entity_type, entity_id, created_at
            FROM platform_audit_logs
            ORDER BY created_at DESC
            LIMIT :limit
        """, {"limit": limit})
        items = [{
            "id": str(r["id"]), "time": r["created_at"].isoformat() if r.get("created_at") else None,
            "actor": str(r["actor_id"]) if r.get("actor_id") else "system", "actor_role": r.get("actor_role"),
            "action": r["operation"], "entity_type": r.get("entity_type"), "entity_id": str(r["entity_id"]) if r.get("entity_id") else None,
        } for r in rows]
        return {"items": items}

    # ── Part O: Category Performance ─────────────────────────────────────────

    async def get_category_performance(self, date_from: str | None = None, date_to: str | None = None) -> dict[str, Any]:
        from_dt, to_dt = _date_defaults(date_from, date_to)
        p = {"f": from_dt, "t": to_dt}
        rows = await _safe_rows(self.db, """
            SELECT
                'home_services' AS vertical_key,
                'Home Services' AS category_name,
                (SELECT COUNT(*) FROM tenants WHERE vertical='home_services' AND status='active') AS tenant_count,
                (SELECT COUNT(*) FROM service_bookings WHERE created_at BETWEEN :f AND :t) AS booking_count,
                (SELECT COUNT(*) FROM service_jobs WHERE status='completed' AND updated_at BETWEEN :f AND :t) AS completed_count,
                (SELECT COALESCE(SUM(cto.amount_paid - COALESCE(cto.refunded_amount,0)),0)
                   FROM credit_topup_orders cto JOIN tenants t ON t.id=cto.tenant_id
                  WHERE t.vertical='home_services' AND cto.payment_status IN ('credited','partially_refunded')
                    AND cto.created_at BETWEEN :f AND :t) AS platform_revenue,
                (SELECT COALESCE(AVG(cr.overall_rating),0) FROM customer_reviews cr
                   JOIN tenants t ON t.id=cr.tenant_id
                  WHERE t.vertical='home_services' AND cr.created_at BETWEEN :f AND :t
                    AND cr.status <> 'deleted') AS avg_rating,
                (SELECT COUNT(*) FROM customer_complaints WHERE created_at BETWEEN :f AND :t) AS complaint_count
            WHERE EXISTS (SELECT 1 FROM verticals WHERE key='home_services' AND is_enabled=true)
        """, p)
        items = []
        for r in rows:
            bookings = int(r["booking_count"] or 0)
            items.append({
                "vertical_key": r["vertical_key"], "category_name": r["category_name"],
                "tenant_count": int(r["tenant_count"] or 0), "booking_count": bookings,
                "completion_rate": round(int(r["completed_count"] or 0) / max(bookings, 1) * 100, 2),
                "platform_revenue": float(r["platform_revenue"] or 0),
                "avg_rating": round(float(r["avg_rating"] or 0), 1),
                "complaint_rate": round(int(r["complaint_count"] or 0) / max(bookings, 1) * 100, 2),
            })
        return {"items": items}

    # ── Export / Refresh (Part B) ────────────────────────────────────────────

    async def export_snapshot(self) -> dict[str, Any]:
        summary = await self.get_executive_summary()
        finance = await self.get_finance_snapshot()
        row = await self.db.execute(text("""
            INSERT INTO dashboard_snapshots (snapshot_json, created_by_user_id)
            VALUES (CAST(:snap AS JSONB), :actor) RETURNING id, created_at
        """), {"snap": json.dumps({"executive_summary": summary, "finance_snapshot": finance}, default=str),
               "actor": self.actor_id})
        await self.db.commit()
        r = row.fetchone()
        return {"snapshot_id": str(r.id), "created_at": r.created_at.isoformat()}
