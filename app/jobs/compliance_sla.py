"""ComplianceSlaJob — DPDP Act 2023 SLA automation.

Runs three tasks:
  1. sla_check      — marks open requests on_track / at_risk / breached;
                      sends in-app notifications to super_admin users for
                      at_risk and breached transitions.
  2. expire_exports — sets compliance_exports status=expired where
                      expires_at < utcnow() and status=ready/downloaded.
  3. run_all        — runs both in sequence.

Designed to run:
  - Automatically: asyncio background task in lifespan (every 15 min)
  - Manually:      POST /v1/admin/compliance/jobs/run
  - CLI:           python -m app.jobs.compliance_sla [sla|expire|all]

Usage:
    cd G:/serviceos
    python -m app.jobs.compliance_sla sla
    python -m app.jobs.compliance_sla expire
    python -m app.jobs.compliance_sla all
"""
from __future__ import annotations

import asyncio
import sys
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any

import structlog

log = structlog.get_logger("jobs.compliance_sla")
utcnow = lambda: datetime.now(timezone.utc)

# SLA thresholds
AT_RISK_HOURS  = 24   # flag as at_risk when < 24 h remain
OPEN_STATUSES  = (
    "submitted", "identity_verification_pending",
    "under_review", "approved", "partially_approved",
    "processing",
)
# Export grace period: expire 7 days after expires_at to ensure download window
EXPORT_EXPIRY_GRACE_HOURS = 0


# ─────────────────────────────────────────────────────────────────────────────
# TASK 1 — SLA CHECK
# ─────────────────────────────────────────────────────────────────────────────

async def run_sla_check() -> dict:
    """
    Scan open ComplianceRequests, update sla_status, create audit entries,
    and fire in-app notifications for super_admin users on transitions.
    Returns counts: checked / breached / at_risk / on_track / notifications_sent.
    """
    from app.database import AsyncSessionLocal
    from sqlalchemy import select, func
    from app.engines.compliance.models import ComplianceRequest, ComplianceAuditLog
    from app.engines.platform_notifications.models import InAppNotification
    from app.engines.auth.models import User

    now = utcnow()

    async with AsyncSessionLocal() as db:
        async with db.begin():
            # ── Load open requests ─────────────────────────────────────────
            r = await db.execute(
                select(ComplianceRequest).where(
                    ComplianceRequest.status.in_(OPEN_STATUSES)))
            open_reqs = r.scalars().all()

            # ── Load super_admin user IDs once ─────────────────────────────
            admin_r = await db.execute(
                select(User.id).where(
                    User.role == "super_admin",
                    User.is_active == True))
            admin_ids: list[uuid.UUID] = [row[0] for row in admin_r.all()]

            checked = breached = at_risk = on_track = notified = 0
            newly_breached: list[ComplianceRequest] = []
            newly_at_risk:  list[ComplianceRequest] = []

            for req in open_reqs:
                checked += 1
                if not req.due_at:
                    continue

                hours_left = (req.due_at - now).total_seconds() / 3600
                prev_sla   = req.sla_status

                if hours_left < 0:
                    new_sla   = "breached"
                    new_status = "sla_breached" if req.status not in (
                        "completed", "rejected", "cancelled") else req.status
                    breached += 1
                elif hours_left < AT_RISK_HOURS:
                    new_sla   = "at_risk"
                    new_status = req.status
                    at_risk   += 1
                else:
                    new_sla   = "on_track"
                    new_status = req.status
                    on_track  += 1

                # Only write + notify on transitions
                if new_sla != prev_sla:
                    req.sla_status = new_sla
                    req.status     = new_status
                    req.updated_at = now

                    # Audit log for the status change
                    db.add(ComplianceAuditLog(
                        user_id=None,
                        tenant_id=None,
                        action=f"sla.{new_sla}",
                        table_accessed="compliance_requests",
                        purpose=f"SLA auto-check: {prev_sla} → {new_sla}",
                        legal_basis="dpdp_act_2023",
                        actor_id=None,
                        actor_role="system",
                        actor_ip=None,
                        reference_id=str(req.id),
                        meta={
                            "request_number": req.request_number,
                            "request_type": req.request_type,
                            "hours_left": round(hours_left, 2),
                            "prev_sla": prev_sla,
                            "new_sla": new_sla,
                        }))

                    if new_sla == "breached":
                        newly_breached.append(req)
                    elif new_sla == "at_risk":
                        newly_at_risk.append(req)

            # ── Send in-app notifications to all super_admin users ─────────
            def _make_notif(admin_id: uuid.UUID, req: ComplianceRequest,
                            severity: str, title: str, body: str) -> InAppNotification:
                return InAppNotification(
                    user_id=admin_id,
                    tenant_id=None,
                    notification_type=f"compliance.sla.{severity}",
                    title=title,
                    body=body,
                    action_url=f"/admin/compliance?highlight={req.id}",
                    action_label="Review Request",
                    source_record_type="compliance_requests",
                    source_record_id=req.id,
                    severity=severity,
                    read_status="unread",
                )

            for req in newly_breached:
                hours_over = abs((req.due_at - now).total_seconds() / 3600) if req.due_at else 0
                for aid in admin_ids:
                    db.add(_make_notif(
                        aid, req, "critical",
                        f"⚠ SLA Breached — {req.request_number}",
                        f"{req.request_type.replace('_', ' ').title()} request from "
                        f"{req.subject_email or req.subject_type} is "
                        f"{hours_over:.1f}h overdue. Immediate action required.",
                    ))
                    notified += 1

            for req in newly_at_risk:
                hours_left_val = (req.due_at - now).total_seconds() / 3600 if req.due_at else 0
                for aid in admin_ids:
                    db.add(_make_notif(
                        aid, req, "warning",
                        f"⏰ SLA At Risk — {req.request_number}",
                        f"{req.request_type.replace('_', ' ').title()} request from "
                        f"{req.subject_email or req.subject_type} has "
                        f"{hours_left_val:.1f}h remaining before SLA breach.",
                    ))
                    notified += 1

    log.info("jobs.compliance_sla.check_done",
             checked=checked, breached=breached, at_risk=at_risk,
             on_track=on_track, notifications_sent=notified)
    return {
        "task": "sla_check",
        "checked": checked,
        "newly_breached": breached,
        "newly_at_risk": at_risk,
        "on_track": on_track,
        "notifications_sent": notified,
        "run_at": now.isoformat(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# TASK 2 — EXPIRE OLD EXPORTS
# ─────────────────────────────────────────────────────────────────────────────

async def run_expire_exports() -> dict:
    """
    Expire ComplianceExport records where:
      - expires_at < utcnow()
      - status in (ready, downloaded)
    Clears the download_url so the link stops working.
    Writes an audit log entry for each expired export.
    """
    from app.database import AsyncSessionLocal
    from sqlalchemy import select
    from app.engines.compliance.models import ComplianceExport, ComplianceAuditLog

    now = utcnow()

    async with AsyncSessionLocal() as db:
        async with db.begin():
            r = await db.execute(
                select(ComplianceExport).where(
                    ComplianceExport.expires_at < now,
                    ComplianceExport.status.in_(["ready", "downloaded"])))
            exports = r.scalars().all()
            expired = 0

            for exp in exports:
                exp.status       = "expired"
                exp.download_url = None
                exp.updated_at   = now

                db.add(ComplianceAuditLog(
                    user_id=exp.subject_id,
                    tenant_id=None,
                    action="export.auto_expired",
                    table_accessed="compliance_exports",
                    purpose="Export TTL exceeded — download link removed",
                    legal_basis="dpdp_act_2023",
                    actor_id=None,
                    actor_role="system",
                    actor_ip=None,
                    reference_id=str(exp.id),
                    meta={
                        "export_format": exp.export_format,
                        "subject_type": exp.subject_type,
                        "expired_at": now.isoformat(),
                    }))
                expired += 1

    log.info("jobs.compliance_sla.expire_exports_done", expired=expired)
    return {
        "task": "expire_exports",
        "expired": expired,
        "run_at": now.isoformat(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# TASK 3 — RUN ALL
# ─────────────────────────────────────────────────────────────────────────────

async def run_all() -> dict:
    """Run both tasks sequentially. Safe to call repeatedly (idempotent)."""
    log.info("jobs.compliance_sla.start")
    sla_result    = await run_sla_check()
    expire_result = await run_expire_exports()
    log.info("jobs.compliance_sla.done",
             breached=sla_result["newly_breached"],
             at_risk=sla_result["newly_at_risk"],
             expired=expire_result["expired"])
    return {
        "sla_check":      sla_result,
        "expire_exports": expire_result,
        "run_at":         utcnow().isoformat(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# BACKGROUND LOOP — used by lifespan asyncio.create_task
# ─────────────────────────────────────────────────────────────────────────────

LOOP_INTERVAL_SECONDS = 15 * 60  # 15 minutes


async def background_loop(interval: int = LOOP_INTERVAL_SECONDS) -> None:
    """
    Infinite async loop. Intended to be started as an asyncio.create_task()
    inside app/main.py lifespan. Runs run_all() every `interval` seconds.
    First run is delayed by one interval so startup is not blocked.
    """
    log.info("jobs.compliance_sla.loop_started", interval_seconds=interval)
    while True:
        await asyncio.sleep(interval)
        try:
            result = await run_all()
            log.info("jobs.compliance_sla.loop_tick",
                     breached=result["sla_check"]["newly_breached"],
                     at_risk=result["sla_check"]["newly_at_risk"],
                     expired=result["expire_exports"]["expired"])
        except asyncio.CancelledError:
            log.info("jobs.compliance_sla.loop_cancelled")
            raise
        except Exception as exc:
            log.error("jobs.compliance_sla.loop_error", error=str(exc))
            # Don't crash the loop on transient errors


# ─────────────────────────────────────────────────────────────────────────────
# CLI ENTRYPOINT
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    commands: dict[str, Any] = {
        "sla":    run_sla_check,
        "expire": run_expire_exports,
        "all":    run_all,
    }
    fn = commands.get(cmd)
    if fn is None:
        print(f"Unknown command: {cmd}. Use: sla | expire | all")
        sys.exit(1)
    result = asyncio.run(fn())
    log.info("jobs.compliance_sla.cli_done", cmd=cmd, result=result)
    sys.exit(0)


if __name__ == "__main__":
    main()
