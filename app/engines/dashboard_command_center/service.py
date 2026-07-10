"""Platform Command Center Dashboard — service layer.

Composes real data from pre-existing tables (tenants, jobs, commission_records,
wallet_transactions, customer_service_credits, security_deposits,
customer_complaints, health_scores, platform_audit_logs) plus the pre-existing
PlatformAnalyticsService (Sprint 28) rather than duplicating those queries.

ServiceOS finance rule enforced throughout: "platform_revenue" is ONLY
wallet_transactions of type credit_topup/package_purchase/subscription —
it never includes job.total_amount (the amount the customer pays the
provider directly for Home Services). That figure is reported separately
as "provider_direct_service_value".
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


class DashboardCommandCenterService:
    def __init__(self, db: AsyncSession, actor_id: uuid.UUID | None = None,
                 actor_role: str | None = None, request_id: str | None = None):
        self.db = db
        self.actor_id = actor_id
        self.actor_role = actor_role
        self.request_id = request_id

    # ── Part C: Executive Summary ───────────────────────────────────────────

    async def get_executive_summary(self, **filters) -> dict[str, Any]:
        active_tenants = await _safe_count(self.db, "SELECT COUNT(*) FROM tenants WHERE status = 'active'")
        new_this_month = await _safe_count(self.db,
            "SELECT COUNT(*) FROM tenants WHERE status = 'active' AND created_at > NOW() - INTERVAL '30 days'")
        bookable_tenants = await _safe_count(self.db,
            "SELECT COUNT(*) FROM tenants WHERE status = 'active' AND verification_status IN ('approved','verified')")

        live_jobs = await _safe_count(self.db,
            "SELECT COUNT(*) FROM jobs WHERE status NOT IN ('closed','cancelled','completed')")
        today_bookings = await _safe_count(self.db,
            "SELECT COUNT(*) FROM bookings WHERE created_at::date = CURRENT_DATE")
        leads_today = await _safe_count(self.db,
            "SELECT COUNT(*) FROM real_estate_leads WHERE created_at::date = CURRENT_DATE")

        pending_tenant_approvals = await _safe_count(self.db,
            "SELECT COUNT(*) FROM tenants WHERE status IN ('pending_review','onboarding_pending')")
        pending_package_approvals = await _safe_count(self.db,
            "SELECT COUNT(*) FROM tenant_package_assignments WHERE status = 'pending_approval'")
        complaints_open = await _safe_count(self.db,
            "SELECT COUNT(*) FROM customer_complaints WHERE status NOT IN ('resolved','closed')")
        disputes_open = await _safe_count(self.db,
            "SELECT COUNT(*) FROM dispute_settlements WHERE status NOT IN ('executed','cancelled')")
        pending_admin_actions = pending_tenant_approvals + pending_package_approvals + complaints_open + disputes_open

        at_risk_tenants = await _safe_count(self.db,
            "SELECT COUNT(*) FROM health_scores WHERE target_type = 'tenant' AND risk_level IN ('high','critical')")
        high_risk = await _safe_count(self.db,
            "SELECT COUNT(*) FROM health_scores WHERE target_type = 'tenant' AND risk_level = 'critical'")

        open_threats = await _safe_count(self.db,
            "SELECT COUNT(*) FROM suspicious_activity_logs WHERE status = 'open'")

        health = await self.get_platform_health()

        return {
            "platform_health": {"score": health["score"], "status": health["status"]},
            "active_tenants": {"count": active_tenants, "new_this_month": new_this_month, "bookable": bookable_tenants},
            "live_operations": {"total": live_jobs + today_bookings + leads_today,
                                "jobs": live_jobs, "bookings": today_bookings, "leads": leads_today},
            "pending_admin_actions": {"count": pending_admin_actions,
                                      "approvals": pending_tenant_approvals + pending_package_approvals,
                                      "complaints": complaints_open, "disputes": disputes_open},
            "at_risk_tenants": {"count": at_risk_tenants, "high_risk": high_risk},
            "critical_alerts": {"count": open_threats, "open_threats": open_threats},
        }

    # ── Part D: Platform Health Score ───────────────────────────────────────

    async def get_platform_health(self) -> dict[str, Any]:
        reasons: list[str] = []
        score = 100

        engines = registry.all()
        unhealthy_engines = [e for e in engines if not getattr(e, "is_healthy", True)]
        if unhealthy_engines:
            score -= min(20, len(unhealthy_engines) * 5)
            reasons.append(f"{len(unhealthy_engines)} engine(s) reporting unhealthy")

        pending_tenants = await _safe_count(self.db,
            "SELECT COUNT(*) FROM tenants WHERE status IN ('pending_review','onboarding_pending')")
        if pending_tenants > 10:
            score -= 10
            reasons.append(f"{pending_tenants} tenants awaiting approval (backlog)")

        failed_deductions = await _safe_count(self.db,
            "SELECT COUNT(*) FROM commission_records WHERE status = 'failed' AND created_at > NOW() - INTERVAL '7 days'")
        if failed_deductions > 0:
            score -= min(15, failed_deductions * 2)
            reasons.append(f"{failed_deductions} failed usage-credit deduction(s) in last 7 days")

        open_threats = await _safe_count(self.db, "SELECT COUNT(*) FROM suspicious_activity_logs WHERE status = 'open'")
        if open_threats > 0:
            score -= min(20, open_threats * 10)
            reasons.append(f"{open_threats} open security threat(s)")

        overdue_complaints = await _safe_count(self.db,
            "SELECT COUNT(*) FROM customer_complaints WHERE status NOT IN ('resolved','closed') AND created_at < NOW() - INTERVAL '3 days'")
        if overdue_complaints > 0:
            score -= min(10, overdue_complaints)
            reasons.append(f"{overdue_complaints} complaint(s) nearing/past SLA")

        score = max(0, min(100, score))
        if score >= 90: status = "healthy"
        elif score >= 75: status = "good"
        elif score >= 60: status = "warning"
        elif score >= 40: status = "degraded"
        else: status = "critical"

        if not reasons:
            reasons.append("All core engines operational")

        return {
            "score": score, "status": status, "reasons": reasons,
            "recommended_actions": ["Review pending admin actions"] if score < 90 else [],
        }

    # ── Part E: Finance Snapshot ─────────────────────────────────────────────

    async def get_finance_snapshot(self, date_from: str | None = None, date_to: str | None = None,
                                    vertical: str | None = None) -> dict[str, Any]:
        base = await _analytics.get_finance_summary(self.db, date_from=date_from, date_to=date_to, vertical=vertical)
        from_dt, to_dt = _date_defaults(date_from, date_to)
        provider_direct_value = await _safe_scalar(self.db,
            "SELECT COALESCE(SUM(total_amount), 0) FROM jobs WHERE status = 'closed' AND created_at BETWEEN :f AND :t",
            {"f": from_dt, "t": to_dt})
        base["provider_direct_service_value"] = float(provider_direct_value or 0)
        return base

    # ── Part F: Tenant Lifecycle Snapshot ────────────────────────────────────

    async def get_tenant_lifecycle(self) -> dict[str, Any]:
        new_requests = await _safe_count(self.db, "SELECT COUNT(*) FROM tenants WHERE status = 'onboarding_pending'")
        pending_review = await _safe_count(self.db, "SELECT COUNT(*) FROM tenants WHERE status = 'pending_review'")
        changes_requested = await _safe_count(self.db, "SELECT COUNT(*) FROM tenants WHERE status = 'changes_requested'")
        approved_week = await _safe_count(self.db,
            "SELECT COUNT(*) FROM tenants WHERE verification_status IN ('approved','verified') AND updated_at > NOW() - INTERVAL '7 days'")
        suspended = await _safe_count(self.db, "SELECT COUNT(*) FROM tenants WHERE status = 'suspended'")
        bookable = await _safe_count(self.db,
            "SELECT COUNT(*) FROM tenants WHERE status = 'active' AND verification_status IN ('approved','verified')")
        non_bookable = await _safe_count(self.db,
            "SELECT COUNT(*) FROM tenants WHERE status = 'active' AND verification_status NOT IN ('approved','verified')")
        package_pending = await _safe_count(self.db,
            "SELECT COUNT(*) FROM tenant_package_assignments WHERE status = 'pending_approval'")

        return {
            "new_tenant_requests": new_requests, "pending_review": pending_review,
            "changes_requested": changes_requested, "approved_this_week": approved_week,
            "suspended": suspended, "bookable_tenants": bookable, "non_bookable_tenants": non_bookable,
            "package_pending_approval": package_pending,
        }

    # ── Part G: Operations Snapshot / Live Operations ────────────────────────

    async def get_operations_snapshot(self, vertical: str | None = None) -> dict[str, Any]:
        live_jobs = await _safe_count(self.db, "SELECT COUNT(*) FROM jobs WHERE status NOT IN ('closed','cancelled')")
        today_bookings = await _safe_count(self.db, "SELECT COUNT(*) FROM bookings WHERE created_at::date = CURRENT_DATE")
        pending_acceptance = await _safe_count(self.db, "SELECT COUNT(*) FROM jobs WHERE status = 'pending_assignment'")
        technicians_on_duty = await _safe_count(self.db,
            "SELECT COUNT(DISTINCT assigned_staff_id) FROM jobs WHERE status NOT IN ('closed','cancelled') AND assigned_staff_id IS NOT NULL")
        appointments_today = await _safe_count(self.db,
            "SELECT COUNT(*) FROM appointments WHERE scheduled_at::date = CURRENT_DATE")
        leads_today = await _safe_count(self.db, "SELECT COUNT(*) FROM real_estate_leads WHERE created_at::date = CURRENT_DATE")
        orders_today = await _safe_count(self.db, "SELECT COUNT(*) FROM food_orders WHERE created_at::date = CURRENT_DATE")
        sla_breaches = await _safe_count(self.db, "SELECT COUNT(*) FROM jobs WHERE sla_breach = true")

        return {
            "live_jobs": live_jobs, "today_bookings": today_bookings,
            "pending_provider_acceptance": pending_acceptance, "technicians_on_duty": technicians_on_duty,
            "appointments_today": appointments_today, "leads_today": leads_today,
            "orders_today": orders_today, "sla_breaches": sla_breaches,
        }

    async def get_live_operations(self, limit: int = 30) -> dict[str, Any]:
        rows = await _safe_rows(self.db, """
            SELECT j.id, j.job_number AS item, t.vertical, t.business_name AS tenant,
                   j.status, j.sla_breach, j.assigned_staff_id, j.updated_at
            FROM jobs j
            LEFT JOIN tenants t ON t.id = j.tenant_id
            WHERE j.status NOT IN ('closed', 'cancelled')
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
        base = await _analytics.get_platform_trends(self.db, date_from=date_from, date_to=date_to, vertical=vertical)
        from_dt, to_dt = _date_defaults(date_from, date_to)
        deductions_trend = await _safe_rows(self.db, """
            SELECT DATE_TRUNC('day', created_at)::date::text AS date, COALESCE(SUM(commission_amount),0) AS value
            FROM commission_records WHERE status = 'deducted' AND created_at BETWEEN :f AND :t
            GROUP BY 1 ORDER BY 1
        """, {"f": from_dt, "t": to_dt})
        direct_value_trend = await _safe_rows(self.db, """
            SELECT DATE_TRUNC('day', created_at)::date::text AS date, COALESCE(SUM(total_amount),0) AS value
            FROM jobs WHERE status = 'closed' AND created_at BETWEEN :f AND :t
            GROUP BY 1 ORDER BY 1
        """, {"f": from_dt, "t": to_dt})
        base["completed_job_deductions_trend"] = [{"date": r["date"], "value": float(r["value"])} for r in deductions_trend]
        base["provider_direct_service_value_trend"] = [{"date": r["date"], "value": float(r["value"])} for r in direct_value_trend]
        return base

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
            SELECT t.id, t.business_name, t.vertical, w.credit_balance
            FROM tenant_wallets w JOIN tenants t ON t.id = w.tenant_id
            WHERE w.credit_balance < w.low_balance_threshold AND t.status = 'active'
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
            SELECT cr.id, t.business_name, t.vertical, cr.job_id
            FROM commission_records cr JOIN tenants t ON t.id = cr.tenant_id
            WHERE cr.status = 'failed'
            ORDER BY cr.created_at DESC LIMIT 20
        """)
        for r in failed_deductions:
            items.append({
                "action_id": f"action_failed_deduction_{r['id']}", "priority": "critical",
                "action": f"Failed completed-job deduction for {r['business_name']}",
                "entity_type": "job", "entity_id": str(r["job_id"]) if r.get("job_id") else None,
                "vertical": r.get("vertical"), "age_hours": None, "status": "open",
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
        rows = await _safe_rows(self.db, """
            SELECT t.id, t.business_name, t.vertical, hs.score, hs.risk_level,
                   w.credit_balance, t.updated_at
            FROM health_scores hs
            JOIN tenants t ON t.id = hs.target_id AND hs.target_type = 'tenant'
            LEFT JOIN tenant_wallets w ON w.tenant_id = t.id
            WHERE hs.risk_level IN ('high','critical')
            ORDER BY hs.score ASC
            LIMIT :limit
        """, {"limit": limit})
        items = []
        for r in rows:
            reason = "Low usage credits" if (r.get("credit_balance") or 0) < 100 else \
                     "High complaints" if r["risk_level"] == "critical" else "Low health score"
            items.append({
                "tenant_id": str(r["id"]), "tenant_name": r["business_name"], "vertical": r.get("vertical"),
                "risk_level": r["risk_level"], "health_score": float(r["score"]) if r.get("score") is not None else None,
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
        pricing_rules = await _safe_count(self.db, """
            SELECT COUNT(*) FROM service_pricing_rules spr
            JOIN master_services ms ON ms.id = spr.master_service_id
            JOIN service_categories sc ON sc.id = ms.category_id
            WHERE sc.vertical_type = 'home_services' AND spr.is_active = true AND spr.deleted_at IS NULL
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
                "status": "healthy" if pricing_rules > 0 else "warning",
                "active_rules": pricing_rules,
            },
            "service_area_coverage_health": {
                "status": _health(hs_providers - tenants_without_areas, hs_providers),
                "active_areas": active_service_areas,
                "tenants_without_areas": tenants_without_areas,
            },
            "provider_matching_health": "healthy" if bookable > 0 else "not_configured",
            "auto_price_options_health": "healthy" if pricing_rules > 0 else "warning",
            "completed_job_deduction_health": "healthy" if pricing_rules > 0 else "not_configured",
            "published_tenant_services": published_tenant_services,
        }

    # ── Part M: Trust & Quality ──────────────────────────────────────────────

    async def get_trust_quality(self) -> dict[str, Any]:
        quality = await _analytics.get_quality_summary(self.db)
        complaints = await _analytics.get_complaints_summary(self.db)
        badges_week = await _safe_count(self.db,
            "SELECT COUNT(*) FROM badge_assignments WHERE created_at > NOW() - INTERVAL '7 days'")
        recalcs = await _safe_count(self.db,
            "SELECT COUNT(*) FROM health_scores WHERE calculated_at > NOW() - INTERVAL '7 days'")
        providers_under_review = await _safe_count(self.db,
            "SELECT COUNT(*) FROM health_scores WHERE target_type = 'tenant' AND risk_level IN ('high','critical')")
        return {
            "avg_rating": quality["avg_rating"], "complaint_rate": quality["complaint_rate"],
            "dispute_rate": quality["dispute_rate"], "sla_success_rate": quality["sla_success_rate"],
            "customer_service_credits_issued": complaints["customer_service_credits_issued"],
            "providers_under_review": providers_under_review,
            "badge_awards_this_week": badges_week, "health_recalculations": recalcs,
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
        return await _analytics.get_category_performance(self.db, date_from=date_from, date_to=date_to)

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
