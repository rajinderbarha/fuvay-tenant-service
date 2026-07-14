"""ComplaintSlaJob — complaint SLA evaluation + admin escalation.

MODULE-L5-02 bug #32: CustomerComplaint stamps tenant_first_response_due_at,
ai_escalation_at, admin_escalation_at and sla_status=on_time at creation, and
ComplaintService already implements check_and_update_sla() (which computes
on_time / at_risk / breached / escalated and logs an SLA-breach event) plus
get_sla_overdue_complaints(). But NOTHING called either of them — there was no
scheduler, so sla_status stayed 'on_time' forever no matter how long a complaint
sat unanswered, and no escalation ever fired. The whole complaint SLA/escalation
engine was dead code.

This job supplies the missing driver, following the same shape as
app/jobs/compliance_sla.py:

  1. sla_check  — recompute sla_status for every non-final complaint that has a
                  first-response deadline (marks at_risk / breached / escalated
                  and logs the breach event).
  2. escalate   — complaints past admin_escalation_at that the provider still has
                  not responded to are moved to under_admin_review so they land
                  on the admin queue instead of silently rotting.
  3. run_all    — both, in sequence.

AI escalation (ai_escalation_at) is deliberately NOT auto-triggered here: it
calls out to DeepSeek, so firing it from an unattended loop would incur external
API cost/latency. It stays an explicit admin action.

Designed to run:
  - Automatically: asyncio background task in lifespan (every 15 min)
  - CLI:           python -m app.jobs.complaint_sla [sla|escalate|all]
"""
from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
from typing import Any

import structlog

log = structlog.get_logger("jobs.complaint_sla")
utcnow = lambda: datetime.now(timezone.utc)


# ─────────────────────────────────────────────────────────────────────────────
# TASK 1 — SLA CHECK
# ─────────────────────────────────────────────────────────────────────────────

async def run_sla_check() -> dict:
    """Recompute sla_status for every non-final complaint with a deadline.

    Returns counts: checked / at_risk / breached / escalated / changed.
    """
    from sqlalchemy import select
    from app.database import get_session_factory
    from app.engines.complaints.complaint_service import ComplaintService
    from app.engines.complaints.models import CustomerComplaint
    from app.engines.complaints.constants import (
        FINAL_STATUSES, STATUS_SETTLED,
        SLA_AT_RISK, SLA_BREACHED, SLA_ESCALATED,
    )

    svc = ComplaintService()
    session_factory = get_session_factory()
    counts = {"checked": 0, "at_risk": 0, "breached": 0, "escalated": 0, "changed": 0}

    async with session_factory() as db:
        q = (
            select(CustomerComplaint)
            .where(
                CustomerComplaint.status.notin_(list(FINAL_STATUSES | {STATUS_SETTLED})),
                CustomerComplaint.tenant_first_response_due_at.is_not(None),
            )
            .limit(500)
        )
        complaints = (await db.execute(q)).scalars().all()

        for c in complaints:
            before = c.sla_status
            await svc.check_and_update_sla(db, c, request_id="job:complaint_sla")
            counts["checked"] += 1
            if c.sla_status != before:
                counts["changed"] += 1
            if c.sla_status == SLA_AT_RISK:
                counts["at_risk"] += 1
            elif c.sla_status == SLA_BREACHED:
                counts["breached"] += 1
            elif c.sla_status == SLA_ESCALATED:
                counts["escalated"] += 1

        await db.commit()

    log.info("jobs.complaint_sla.sla_check_done", **counts)
    return counts


# ─────────────────────────────────────────────────────────────────────────────
# TASK 2 — ADMIN ESCALATION
# ─────────────────────────────────────────────────────────────────────────────

async def run_escalations() -> dict:
    """Move complaints past admin_escalation_at (with no provider response yet)
    onto the admin queue via under_admin_review.

    Returns counts: candidates / escalated / skipped.
    """
    from sqlalchemy import select
    from app.database import get_session_factory
    from app.engines.complaints.complaint_service import ComplaintService
    from app.engines.complaints.models import CustomerComplaint
    from app.engines.complaints.constants import (
        FINAL_STATUSES, STATUS_SETTLED, STATUS_UNDER_ADMIN_REVIEW,
        ALLOWED_TRANSITIONS, ACTOR_SYSTEM,
    )

    svc = ComplaintService()
    session_factory = get_session_factory()
    counts = {"candidates": 0, "escalated": 0, "skipped": 0}
    now = utcnow()

    async with session_factory() as db:
        q = (
            select(CustomerComplaint)
            .where(
                CustomerComplaint.status.notin_(list(FINAL_STATUSES | {STATUS_SETTLED})),
                CustomerComplaint.admin_escalation_at.is_not(None),
                CustomerComplaint.admin_escalation_at < now,
                CustomerComplaint.provider_responded_at.is_(None),
            )
            .limit(200)
        )
        complaints = (await db.execute(q)).scalars().all()

        for c in complaints:
            counts["candidates"] += 1
            if STATUS_UNDER_ADMIN_REVIEW not in ALLOWED_TRANSITIONS.get(c.status, set()):
                # already under review (or a state from which review is not a
                # legal move) — nothing to do
                counts["skipped"] += 1
                continue
            await svc._transition(
                db, c, STATUS_UNDER_ADMIN_REVIEW, ACTOR_SYSTEM, None,
                reason="SLA admin-escalation deadline passed with no provider response",
                request_id="job:complaint_sla",
            )
            # bug #40: notify the admins that a stalled complaint is now theirs.
            try:
                from app.engines.complaints.notifications import notify_admins_complaint
                await notify_admins_complaint(
                    db, c,
                    notification_type="complaint.sla.escalated",
                    title=f"Complaint escalated to you — {c.complaint_number}",
                    body="The provider did not respond within the SLA window; this "
                         "complaint has been escalated to admin manual review.",
                    severity="critical",
                )
            except Exception:
                pass
            counts["escalated"] += 1

        await db.commit()

    log.info("jobs.complaint_sla.escalations_done", **counts)
    return counts


async def run_ai_auto_start() -> dict:
    """MODULE-L5-02 — AI settlement is not started by hand.

    It takes over automatically once the PROVIDER has failed to solve the
    complaint: either they never responded within their SLA window, or the
    customer rejected the resolution they offered (which lands the complaint in
    under_admin_review). The admin only sets the rule — enable/disable, the cap,
    the permitted remedies — on complaint_policies.

    Starting a session charges the provider the AI settlement fee.

    Returns counts: candidates / started / skipped.
    """
    from sqlalchemy import select, or_
    from app.database import get_session_factory
    from app.engines.complaints.complaint_service import ComplaintService
    from app.engines.complaints.ai_settlement_service import AISettlementService
    from app.engines.complaints.models import CustomerComplaint, AISettlementSession
    from app.engines.complaints.settlement_rules import resolve_rule
    from app.engines.complaints.constants import (
        FINAL_STATUSES, STATUS_SETTLED, STATUS_AWAITING_PROVIDER,
        STATUS_UNDER_ADMIN_REVIEW, STATUS_AI_SETTLEMENT_STARTED,
    )

    svc = ComplaintService()
    ai = AISettlementService()
    session_factory = get_session_factory()
    counts = {"candidates": 0, "started": 0, "skipped": 0}
    now = utcnow()

    async with session_factory() as db:
        # Provider failed = they blew their response SLA, or the customer bounced
        # their resolution back and it is sitting with admin.
        q = (
            select(CustomerComplaint)
            .where(
                CustomerComplaint.status.notin_(list(FINAL_STATUSES | {STATUS_SETTLED})),
                or_(
                    (CustomerComplaint.status == STATUS_AWAITING_PROVIDER) &
                    (CustomerComplaint.tenant_first_response_due_at < now) &
                    (CustomerComplaint.provider_responded_at.is_(None)),
                    CustomerComplaint.status == STATUS_UNDER_ADMIN_REVIEW,
                ),
            )
            .limit(100)
        )
        complaints = (await db.execute(q)).scalars().all()

        for c in complaints:
            counts["candidates"] += 1

            existing = (await db.execute(
                select(AISettlementSession).where(AISettlementSession.complaint_id == c.id)
            )).scalars().first()
            if existing:
                counts["skipped"] += 1      # already had its turn with the AI
                continue

            rule = await resolve_rule(db, c)
            if not rule.enabled or not rule.auto_start_on_provider_failure:
                counts["skipped"] += 1      # the admin turned this off
                continue

            await ai.start_session(db, c, actor_id=None, request_id="job:ai_auto_start")
            c.status = STATUS_AI_SETTLEMENT_STARTED
            counts["started"] += 1

        await db.commit()

    log.info("jobs.complaint_sla.ai_auto_start_done", **counts)
    return counts


async def run_all() -> dict:
    return {
        "sla_check":     await run_sla_check(),
        "escalations":   await run_escalations(),
        "ai_auto_start": await run_ai_auto_start(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# BACKGROUND LOOP
# ─────────────────────────────────────────────────────────────────────────────

LOOP_INTERVAL_SECONDS = 15 * 60  # 15 minutes


async def background_loop(interval: int = LOOP_INTERVAL_SECONDS) -> None:
    """Infinite async loop, started as an asyncio task in app/main.py lifespan.
    First run is delayed by one interval so startup is not blocked."""
    log.info("jobs.complaint_sla.loop_started", interval_seconds=interval)
    while True:
        await asyncio.sleep(interval)
        try:
            result = await run_all()
            log.info("jobs.complaint_sla.loop_tick",
                     breached=result["sla_check"]["breached"],
                     at_risk=result["sla_check"]["at_risk"],
                     escalated=result["escalations"]["escalated"],
                     ai_started=result["ai_auto_start"]["started"])
        except asyncio.CancelledError:
            log.info("jobs.complaint_sla.loop_cancelled")
            raise
        except Exception as exc:  # never crash the loop on a transient error
            log.error("jobs.complaint_sla.loop_error", error=str(exc))


# ─────────────────────────────────────────────────────────────────────────────
# CLI ENTRYPOINT
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    commands: dict[str, Any] = {
        "sla":      run_sla_check,
        "escalate": run_escalations,
        "ai":       run_ai_auto_start,
        "all":      run_all,
    }
    fn = commands.get(cmd)
    if fn is None:
        print(f"Unknown command: {cmd}. Use: sla | escalate | ai | all")
        sys.exit(1)

    async def _run() -> dict:
        # The background loop runs inside the app lifespan (DB already
        # initialised); the CLI has to set the engine up itself.
        from app.database import init_db, close_db
        await init_db()
        try:
            return await fn()
        finally:
            await close_db()

    result = asyncio.run(_run())
    log.info("jobs.complaint_sla.cli_done", cmd=cmd, result=result)
    print(f"complaint_sla {cmd}: {result}")
    sys.exit(0)


if __name__ == "__main__":
    main()
