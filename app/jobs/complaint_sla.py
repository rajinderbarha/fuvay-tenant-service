"""Automatic deadline enforcement for customer remedy cases.

The platform does not adjudicate complaints, refunds, or warranty claims. This
job measures the deadlines each party owns and keeps every case moving:

* Provider first response -- one idempotent penalty when missed.
* Provider resolution -- runs whenever the case is the provider's move (filed,
  resolution rejected, rework or refund accepted). One idempotent penalty per
  provider turn, plus a notice at breach and again at escalation. Before this,
  a single reply stopped all measurement and a case could stay open forever.
* Customer response -- a proposed resolution waits on the customer; they get
  one reminder, and a case they never answer resolves instead of holding the
  provider's queue open.
* Close-out -- resolved and settled cases close after a follow-up window.
  Nothing wrote `closed` before, so resolved cases never left the queue.

It never decides a complaint's merits: elapsed time only moves a case along
the path each party already chose.
"""
from __future__ import annotations

import asyncio
import sys
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import structlog
from sqlalchemy import and_, or_, select

log = structlog.get_logger("jobs.complaint_sla")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _uuid_or_none(value):
    if value is None or isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        return None


async def _resolve_penalty_amount(db, tenant_id, category_id=None) -> Decimal:
    """Resolve the most specific active SLA policy, with a safe default.

    This was raw SQL with `(:category_id IS NULL OR category_id=:category_id)`,
    which asyncpg rejects ("could not determine data type of parameter").
    Complaints always carry a category, so every penalty attempt raised,
    the sweep aborted before its commit, and its SLA status updates were
    rolled back with it: complaint SLA enforcement never took effect. It now
    uses the same typed resolver as filing and deadlines.
    """
    from app.engines.complaints.eligibility_service import ComplaintEligibilityService
    policy = await ComplaintEligibilityService().get_complaint_policy(
        db, _uuid_or_none(category_id), _uuid_or_none(tenant_id),
    )
    value = policy.provider_sla_breach_penalty if policy is not None else None
    return Decimal(str(value if value is not None else "50.00"))


async def _charge_sla_penalty(
    db, *, tenant_id, source_type: str, source_id: str,
    category_id=None, request_id: str,
) -> dict:
    from app.engines.tenant_engine.health import compute_health_score
    from app.engines.usage_credits.service import UsageCreditService

    amount = await _resolve_penalty_amount(db, tenant_id, category_id)
    if amount <= 0:
        return {"idempotent": True, "skipped": True, "amount": Decimal("0")}
    credit_service = UsageCreditService(
        db, actor_role="system", request_id=request_id,
    )
    if source_type == "customer_complaint":
        result = await credit_service.charge_complaint_sla_penalty(
            tenant_id=tenant_id, complaint_id=uuid.UUID(str(source_id)), amount=amount,
        )
    else:
        result = await credit_service.charge_provider_response_sla_penalty(
            tenant_id=tenant_id,
            source_type=source_type,
            source_id=source_id,
            amount=amount,
        )
    if not result["idempotent"]:
        await compute_health_score(tenant_id, db=db)
    return {**result, "amount": amount}


async def _sla_warning_hours(db) -> int:
    """`complaint_sla_warning_threshold_hours`, falling back to the default.

    The setting was registered for governance with no reader, and the at-risk
    window was a hardcoded four hours.
    """
    from app.engines.complaints.complaint_service import DEFAULT_SLA_WARNING_HOURS
    try:
        from app.engines.settings_engine.service import SettingsService
        resolved = await SettingsService(db).resolve("complaint_sla_warning_threshold_hours")
        value = resolved.get("value") if isinstance(resolved, dict) else None
        if isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0:
            return int(value)
    except Exception as exc:  # noqa: BLE001 -- a settings outage must not stop enforcement
        log.warning("jobs.complaint_sla.warning_setting_unavailable", error=str(exc))
    return DEFAULT_SLA_WARNING_HOURS


def _aware(value):
    if not isinstance(value, datetime):
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


async def _notify_provider_overdue(db, complaint, *, clock: str | None, escalated: bool) -> None:
    """Tell the provider a complaint deadline passed, in terms of what to do."""
    try:
        from app.engines.complaints.notifications import notify_provider_complaint
        number = complaint.complaint_number
        if clock == "first_response":
            body = f"Complaint {number} has had no reply from you. Respond to the customer now."
        else:
            body = (f"Complaint {number} is past its resolution deadline. Propose a "
                    "resolution or complete the agreed remedy.")
        if escalated:
            body += " It is now escalated and counts against your account health."
        await notify_provider_complaint(
            db, complaint,
            notification_type="complaint.sla_escalated" if escalated else "complaint.sla_breached",
            title=(f"Complaint escalated — {number}" if escalated
                   else f"Complaint overdue — {number}"),
            body=body, severity="critical" if escalated else "warning",
        )
    except Exception as exc:  # noqa: BLE001 -- never lose the enforcement to a notice
        log.warning("jobs.complaint_sla.notify_failed", complaint_id=str(complaint.id), error=str(exc))


async def run_sla_check() -> dict:
    """Refresh provider deadlines and charge each missed deadline once."""
    from app.database import get_session_factory
    from app.engines.complaints.complaint_service import ComplaintService
    from app.engines.complaints.constants import (
        PROVIDER_ACTION_TIMED_STATUSES,
        RESOLVED_OR_FINAL_STATUSES,
        SLA_AT_RISK,
        SLA_BREACHED,
        SLA_ESCALATED,
    )
    from app.engines.complaints.models import CustomerComplaint

    service = ComplaintService()
    counts = {
        "checked": 0, "at_risk": 0, "breached": 0, "escalated": 0,
        "changed": 0, "penalised": 0, "already_penalised": 0,
        "resolution_penalised": 0, "deadline_stamped": 0,
    }
    async with get_session_factory()() as db:
        warning_hours = await _sla_warning_hours(db)
        complaints = (await db.execute(
            select(CustomerComplaint).where(
                CustomerComplaint.status.notin_(list(RESOLVED_OR_FINAL_STATUSES)),
                or_(
                    # First response still owed.
                    and_(
                        CustomerComplaint.tenant_first_response_due_at.is_not(None),
                        CustomerComplaint.provider_responded_at.is_(None),
                    ),
                    # A resolution is owed.
                    CustomerComplaint.provider_action_due_at.is_not(None),
                    # The provider's move with no deadline: rows from before
                    # the clock covered their status, or any path that set the
                    # status without stamping one. They get a deadline here
                    # rather than sitting unmeasured.
                    and_(
                        CustomerComplaint.status.in_(list(PROVIDER_ACTION_TIMED_STATUSES)),
                        CustomerComplaint.provider_action_due_at.is_(None),
                    ),
                ),
            ).order_by(CustomerComplaint.created_at).limit(500)
        )).scalars().all()

        now = utcnow()
        for complaint in complaints:
            if (complaint.status in PROVIDER_ACTION_TIMED_STATUSES
                    and complaint.provider_action_due_at is None):
                await service.enter_status(db, complaint, complaint.status)
                counts["deadline_stamped"] += 1
            before = complaint.sla_status
            _due, clock = service.running_provider_deadline(complaint)
            await service.check_and_update_sla(
                db, complaint, request_id="job:complaint_sla", warning_hours=warning_hours,
            )
            counts["checked"] += 1
            if complaint.sla_status != before:
                counts["changed"] += 1
                if complaint.sla_status in (SLA_BREACHED, SLA_ESCALATED):
                    await _notify_provider_overdue(
                        db, complaint, clock=clock,
                        escalated=complaint.sla_status == SLA_ESCALATED,
                    )
            if complaint.sla_status == SLA_AT_RISK:
                counts["at_risk"] += 1
            elif complaint.sla_status == SLA_BREACHED:
                counts["breached"] += 1
            elif complaint.sla_status == SLA_ESCALATED:
                counts["escalated"] += 1

            # Resolution deadline: one penalty per provider turn. The due time
            # is part of the source id, so a later turn is a new obligation
            # while a re-run of the same turn stays idempotent.
            action_due = _aware(complaint.provider_action_due_at)
            penalised_at = _aware(complaint.provider_action_penalized_at)
            if (
                complaint.status in PROVIDER_ACTION_TIMED_STATUSES
                and action_due is not None and now > action_due
                and complaint.tenant_id
                and not (penalised_at and penalised_at >= action_due)
            ):
                result = await _charge_sla_penalty(
                    db,
                    tenant_id=complaint.tenant_id,
                    source_type="complaint_resolution",
                    source_id=f"{complaint.id}:{action_due.strftime('%Y%m%dT%H%M')}",
                    category_id=complaint.category_id,
                    request_id="job:complaint_sla",
                )
                complaint.provider_action_penalized_at = now
                if not result["idempotent"]:
                    counts["resolution_penalised"] += 1

            # First response: only when that clock is the one that breached.
            # A case with no first-response deadline (provider-opened, or the
            # backing record of a refund) must not be charged for a reply.
            if (
                clock == "first_response"
                and complaint.provider_responded_at is None
                and complaint.sla_status in (SLA_BREACHED, SLA_ESCALATED)
                and complaint.tenant_id
                and not complaint.provider_sla_penalized_at
            ):
                result = await _charge_sla_penalty(
                    db,
                    tenant_id=complaint.tenant_id,
                    source_type="customer_complaint",
                    source_id=str(complaint.id),
                    category_id=complaint.category_id,
                    request_id="job:complaint_sla",
                )
                complaint.provider_sla_penalty_charged = abs(
                    Decimal(str(result.get("credit_delta", 0)))
                )
                complaint.provider_sla_penalized_at = utcnow()
                key = "already_penalised" if result["idempotent"] else "penalised"
                counts[key] += 1

        await db.commit()

    log.info("jobs.complaint_sla.sla_check_done", **counts)
    return counts


def warranty_penalty_source_id(claim_id, due_at) -> str:
    """One penalty per missed warranty deadline -- each escalation sets a new one."""
    stamp = due_at.strftime("%Y%m%dT%H%M") if isinstance(due_at, datetime) else "initial"
    return f"{claim_id}:{stamp}"


async def _overdue_pages(db, statement, due_column, id_column, *, page_size: int = 500):
    """Keyset-page overdue cases so a penalised first page cannot starve later ones.

    Penalties are idempotent, but the cases remain overdue until the provider
    responds. Re-querying only the first 500 on every sweep never reaches case
    501. A stable (deadline, id) cursor visits the complete backlog each run.
    """
    cursor = None
    while True:
        page = statement
        if cursor is not None:
            due_at, case_id = cursor
            page = page.where(or_(
                due_column > due_at,
                and_(due_column == due_at, id_column > case_id),
            ))
        rows = (await db.execute(
            page.order_by(due_column, id_column).limit(page_size)
        )).scalars().all()
        if not rows:
            return
        yield rows
        cursor = (rows[-1].provider_response_due_at, rows[-1].id)
        if len(rows) < page_size:
            return


async def run_remedy_sla_check() -> dict:
    """Automatically penalise overdue refund and warranty response cases."""
    from app.database import get_session_factory
    from app.engines.complaints.constants import REFUND_PROVIDER_REVIEW, REFUND_REQUESTED
    from app.engines.complaints.models import RefundRequest
    from app.engines.platform_commerce.models import WarrantyClaim

    now = utcnow()
    counts = {
        "warranty_checked": 0, "refund_checked": 0,
        "penalised": 0, "already_penalised": 0,
    }
    async with get_session_factory()() as db:
        warranty_query = select(WarrantyClaim).where(
                # `provider_in_progress` counts too: the provider promised to
                # fix it and now owes a resolution by its own deadline.
                WarrantyClaim.provider_response_due_at.is_not(None),
                WarrantyClaim.provider_response_due_at <= now,
                or_(
                    # A first response is owed until the provider answers the
                    # CURRENT round; an answer from before the latest
                    # escalation does not count.
                    and_(
                        WarrantyClaim.status == "provider_action_required",
                        or_(
                            WarrantyClaim.provider_responded_at.is_(None),
                            and_(
                                WarrantyClaim.escalated_at.is_not(None),
                                WarrantyClaim.provider_responded_at < WarrantyClaim.escalated_at,
                            ),
                        ),
                    ),
                    # The provider said they were fixing it and then let the
                    # resolution deadline pass.
                    WarrantyClaim.status == "provider_in_progress",
                ),
            )
        refund_query = select(RefundRequest).where(
                RefundRequest.status.in_((REFUND_REQUESTED, REFUND_PROVIDER_REVIEW)),
                RefundRequest.provider_response_due_at.is_not(None),
                RefundRequest.provider_response_due_at <= now,
                RefundRequest.tenant_id.is_not(None),
            )

        async for warranty_claims in _overdue_pages(
            db, warranty_query, WarrantyClaim.provider_response_due_at, WarrantyClaim.id,
        ):
            for claim in warranty_claims:
                counts["warranty_checked"] += 1
                result = await _charge_sla_penalty(
                    db,
                    tenant_id=claim.tenant_id,
                    source_type="warranty_claim",
                    source_id=warranty_penalty_source_id(claim.id, claim.provider_response_due_at),
                    request_id="job:warranty_sla",
                )
                key = "already_penalised" if result["idempotent"] else "penalised"
                counts[key] += 1

        async for refund_requests in _overdue_pages(
            db, refund_query, RefundRequest.provider_response_due_at, RefundRequest.id,
        ):
            for refund in refund_requests:
                counts["refund_checked"] += 1
                result = await _charge_sla_penalty(
                    db,
                    tenant_id=refund.tenant_id,
                    source_type="refund_request",
                    source_id=str(refund.id),
                    request_id="job:refund_sla",
                )
                key = "already_penalised" if result["idempotent"] else "penalised"
                counts[key] += 1

        await db.commit()

    log.info("jobs.complaint_sla.remedy_check_done", **counts)
    return counts


async def run_customer_response_check() -> dict:
    """Remind, then resolve, cases whose proposed resolution waits on the customer."""
    from app.database import get_session_factory
    from app.engines.complaints.complaint_service import ComplaintService
    from app.engines.complaints.constants import (
        CUSTOMER_REMINDER_HOURS,
        CUSTOMER_RESPONSE_EXPIRY_HOURS,
        CUSTOMER_TURN_STATUSES,
    )
    from app.engines.complaints.models import ComplaintEvent, CustomerComplaint

    service = ComplaintService()
    counts = {"checked": 0, "reminded": 0, "expired": 0}
    async with get_session_factory()() as db:
        complaints = (await db.execute(
            select(CustomerComplaint).where(
                CustomerComplaint.status.in_(list(CUSTOMER_TURN_STATUSES)),
            ).order_by(CustomerComplaint.updated_at).limit(500)
        )).scalars().all()
        now = utcnow()
        for complaint in complaints:
            counts["checked"] += 1
            pending = await service.pending_resolution(db, complaint.id)
            # The customer's turn began when the offer was made.
            waiting_since = _aware(getattr(pending, "created_at", None)) or _aware(complaint.updated_at)
            if waiting_since is None:
                continue
            expires_at = waiting_since + timedelta(hours=CUSTOMER_RESPONSE_EXPIRY_HOURS)
            if now >= expires_at:
                if await service.expire_unanswered_resolution(db, complaint):
                    counts["expired"] += 1
                continue
            if now < waiting_since + timedelta(hours=CUSTOMER_REMINDER_HOURS):
                continue
            already = (await db.execute(
                select(ComplaintEvent.id).where(
                    ComplaintEvent.complaint_id == complaint.id,
                    ComplaintEvent.event_type == "customer_response_reminder",
                    ComplaintEvent.created_at >= waiting_since,
                ).limit(1)
            )).scalar_one_or_none()
            if already is None:
                await service.remind_customer_to_respond(db, complaint, expires_at=expires_at)
                counts["reminded"] += 1
        await db.commit()
    log.info("jobs.complaint_sla.customer_response_check_done", **counts)
    return counts


async def run_auto_close() -> dict:
    """Close resolved and settled cases once their follow-up window passes."""
    from app.database import get_session_factory
    from app.engines.complaints.complaint_service import ComplaintService
    from app.engines.complaints.constants import (
        RESOLVED_AUTO_CLOSE_HOURS,
        STATUS_REFUND_RECORDED,
        STATUS_RESOLVED,
        STATUS_SETTLED,
    )
    from app.engines.complaints.models import CustomerComplaint

    service = ComplaintService()
    counts = {"checked": 0, "closed": 0}
    cutoff = utcnow() - timedelta(hours=RESOLVED_AUTO_CLOSE_HOURS)
    async with get_session_factory()() as db:
        complaints = (await db.execute(
            select(CustomerComplaint).where(
                CustomerComplaint.status.in_(
                    [STATUS_RESOLVED, STATUS_SETTLED, STATUS_REFUND_RECORDED]),
            ).order_by(CustomerComplaint.updated_at).limit(500)
        )).scalars().all()
        for complaint in complaints:
            counts["checked"] += 1
            # `resolved_at` was not stamped on every path, so fall back to the
            # last update rather than leaving those cases open forever.
            resolved_at = _aware(complaint.resolved_at) or _aware(complaint.updated_at)
            if resolved_at is None or resolved_at > cutoff:
                continue
            if await service.close_resolved(db, complaint):
                counts["closed"] += 1
        await db.commit()
    log.info("jobs.complaint_sla.auto_close_done", **counts)
    return counts


async def run_all() -> dict:
    return {
        "complaints": await run_sla_check(),
        "remedies": await run_remedy_sla_check(),
        "customer_response": await run_customer_response_check(),
        "auto_close": await run_auto_close(),
    }


LOOP_INTERVAL_SECONDS = 15 * 60


async def background_loop(interval: int = LOOP_INTERVAL_SECONDS) -> None:
    """Run SLA enforcement periodically without blocking application startup."""
    log.info("jobs.complaint_sla.loop_started", interval_seconds=interval)
    while True:
        await asyncio.sleep(interval)
        try:
            result = await run_all()
            log.info(
                "jobs.complaint_sla.loop_tick",
                complaint_penalties=result["complaints"]["penalised"],
                resolution_penalties=result["complaints"]["resolution_penalised"],
                remedy_penalties=result["remedies"]["penalised"],
                customer_responses_expired=result["customer_response"]["expired"],
                closed=result["auto_close"]["closed"],
            )
        except asyncio.CancelledError:
            log.info("jobs.complaint_sla.loop_cancelled")
            raise
        except Exception as exc:
            log.error("jobs.complaint_sla.loop_error", error=str(exc))


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    commands: dict[str, Any] = {
        "sla": run_sla_check,
        "remedies": run_remedy_sla_check,
        "customer": run_customer_response_check,
        "close": run_auto_close,
        "all": run_all,
    }
    fn = commands.get(cmd)
    if fn is None:
        print(f"Unknown command: {cmd}. Use: sla | remedies | customer | close | all")
        raise SystemExit(1)

    async def _run() -> dict:
        from app.database import close_db, init_db
        await init_db()
        try:
            return await fn()
        finally:
            await close_db()

    result = asyncio.run(_run())
    log.info("jobs.complaint_sla.cli_done", cmd=cmd, result=result)
    print(f"complaint_sla {cmd}: {result}")


if __name__ == "__main__":
    main()
