"""Automatic provider-response SLA enforcement for customer remedy cases.

The platform does not adjudicate complaints, refunds, or warranty claims.
This job only measures provider response deadlines, posts one idempotent usage
credit penalty when a deadline is missed, and refreshes account health.
"""
from __future__ import annotations

import asyncio
import sys
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import structlog
from sqlalchemy import select, text

log = structlog.get_logger("jobs.complaint_sla")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def _resolve_penalty_amount(db, tenant_id, category_id=None) -> Decimal:
    """Resolve the most specific active SLA policy, with a safe default."""
    value = (await db.execute(text(
        "SELECT provider_sla_breach_penalty FROM complaint_policies "
        "WHERE is_active=true AND (tenant_id=:tenant_id OR tenant_id IS NULL) "
        "AND (:category_id IS NULL OR category_id=:category_id OR category_id IS NULL) "
        "ORDER BY (tenant_id IS NOT NULL) DESC, (category_id IS NOT NULL) DESC "
        "LIMIT 1"
    ), {
        "tenant_id": str(tenant_id),
        "category_id": str(category_id) if category_id else None,
    })).scalar_one_or_none()
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


async def run_sla_check() -> dict:
    """Refresh complaint SLA state and charge each missed response once."""
    from app.database import get_session_factory
    from app.engines.complaints.complaint_service import ComplaintService
    from app.engines.complaints.constants import (
        FINAL_STATUSES,
        SLA_AT_RISK,
        SLA_BREACHED,
        SLA_ESCALATED,
        STATUS_SETTLED,
    )
    from app.engines.complaints.models import CustomerComplaint

    service = ComplaintService()
    counts = {
        "checked": 0, "at_risk": 0, "breached": 0, "escalated": 0,
        "changed": 0, "penalised": 0, "already_penalised": 0,
    }
    async with get_session_factory()() as db:
        complaints = (await db.execute(
            select(CustomerComplaint).where(
                CustomerComplaint.status.notin_(list(FINAL_STATUSES | {STATUS_SETTLED})),
                CustomerComplaint.tenant_first_response_due_at.is_not(None),
            ).limit(500)
        )).scalars().all()

        for complaint in complaints:
            before = complaint.sla_status
            await service.check_and_update_sla(db, complaint, request_id="job:complaint_sla")
            counts["checked"] += 1
            if complaint.sla_status != before:
                counts["changed"] += 1
            if complaint.sla_status == SLA_AT_RISK:
                counts["at_risk"] += 1
            elif complaint.sla_status == SLA_BREACHED:
                counts["breached"] += 1
            elif complaint.sla_status == SLA_ESCALATED:
                counts["escalated"] += 1

            if (
                complaint.sla_status in (SLA_BREACHED, SLA_ESCALATED)
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
        warranty_claims = (await db.execute(
            select(WarrantyClaim).where(
                WarrantyClaim.status == "provider_action_required",
                WarrantyClaim.provider_response_due_at.is_not(None),
                WarrantyClaim.provider_response_due_at <= now,
                WarrantyClaim.provider_responded_at.is_(None),
            ).limit(500)
        )).scalars().all()
        refund_requests = (await db.execute(
            select(RefundRequest).where(
                RefundRequest.status.in_((REFUND_REQUESTED, REFUND_PROVIDER_REVIEW)),
                RefundRequest.provider_response_due_at.is_not(None),
                RefundRequest.provider_response_due_at <= now,
                RefundRequest.tenant_id.is_not(None),
            ).limit(500)
        )).scalars().all()

        for claim in warranty_claims:
            counts["warranty_checked"] += 1
            result = await _charge_sla_penalty(
                db,
                tenant_id=claim.tenant_id,
                source_type="warranty_claim",
                source_id=str(claim.id),
                request_id="job:warranty_sla",
            )
            key = "already_penalised" if result["idempotent"] else "penalised"
            counts[key] += 1

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


async def run_all() -> dict:
    return {
        "complaints": await run_sla_check(),
        "remedies": await run_remedy_sla_check(),
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
                remedy_penalties=result["remedies"]["penalised"],
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
        "all": run_all,
    }
    fn = commands.get(cmd)
    if fn is None:
        print(f"Unknown command: {cmd}. Use: sla | remedies | all")
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
