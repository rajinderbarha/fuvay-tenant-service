"""MODULE-L5-21 — quote lifecycle notifications.

The quote engine changed job/quote state and logged events, but never told the
other party. A provider sending a quote left the customer unaware one was waiting
(so the job silently stalled at "awaiting quote approval"), and a customer's
approve/reject/revision never reached the provider. This adds targeted in-app
notifications on each transition, reusing the same InAppNotification the chat and
complaints engines use.
"""
from __future__ import annotations

import uuid

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.platform_notifications.models import InAppNotification
from app.engines.quote_checklist.models import ServiceJobQuote

logger = structlog.get_logger("quote_notifications")


async def _tenant_owner_id(db: AsyncSession, tenant_id) -> uuid.UUID | None:
    from app.engines.tenant_engine.models import Tenant
    t = await db.get(Tenant, tenant_id)
    return getattr(t, "owner_user_id", None) if t else None


async def _assigned_staff_id(db: AsyncSession, job_id) -> uuid.UUID | None:
    from app.engines.final_records.models import ServiceJob
    job = await db.get(ServiceJob, job_id)
    return getattr(job, "assigned_staff_id", None) if job else None


def _add(
    db, *, user_id, tenant_id, ntype, title, body, url,
    source_id=None, source_type="service_job_quote",
):
    db.add(InAppNotification(
        user_id=user_id, tenant_id=tenant_id,
        notification_type=ntype, title=title, body=body,
        action_url=url, action_label="View quote",
        source_record_type=source_type, source_record_id=source_id,
        severity="info",
    ))


async def notify_customer_quote_sent(db: AsyncSession, quote: ServiceJobQuote) -> None:
    """Tell the customer a quote is waiting for approval."""
    if not quote.customer_id:
        return
    total = quote.total_amount
    _add(db, user_id=quote.customer_id, tenant_id=quote.tenant_id,
         ntype="quote.sent",
         title="A quote is waiting for your approval",
         body=f"Your provider sent a quote for {quote.currency}{total}. Review and approve to continue.",
         url=f"/customer/bookings/{quote.booking_id}/quotes?job_id={quote.job_id}",
         # Customer native navigation has a real Booking Details destination,
         # not a standalone quote screen. Point at the booking so tapping this
         # notification opens the quote approval card safely instead of
         # rendering an action-looking dead row.
         source_type="service_bookings", source_id=quote.booking_id)
    # A chat-originated customer may never open the native inbox. Notify the
    # same recent WhatsApp/Instagram thread best-effort; their next message is
    # answered with the customer-safe estimate and decision controls.
    # Chat delivery is best-effort and must never share the quote transaction.
    # A messaging-schema/API failure on the shared session leaves PostgreSQL's
    # transaction aborted; catching that exception and then committing used to
    # roll back the already-successful quote transition silently. Isolate chat
    # lookup/delivery in its own session so the in-app notification and quote
    # state remain atomic regardless of the external channel's health.
    try:
        from app.database import get_session_factory
        from app.engines.messaging_gateway.service import notify_customer
        async with get_session_factory()() as messaging_db:
            try:
                await notify_customer(
                    messaging_db, quote.customer_id,
                    f"Your provider sent estimate {quote.quote_number}. "
                    "Reply here to review the itemised customer total.",
                )
                await messaging_db.commit()
            except Exception:
                await messaging_db.rollback()
                raise
    except Exception as exc:
        logger.warning(
            "quote_notifications.chat_delivery_failed",
            quote_id=str(quote.id),
            error=str(exc),
        )


async def notify_provider_quote_decision(
    db: AsyncSession, quote: ServiceJobQuote, decision: str,
) -> None:
    """Tell the provider side (owner + assigned technician) the customer's
    decision on a quote: approved / rejected / revision requested."""
    label = {"approved": "approved", "rejected": "rejected",
             "revision": "asked for changes to"}.get(decision, decision)
    title = f"Customer {label} a quote"
    body = f"Quote {quote.quote_number} for {quote.currency}{quote.total_amount} was {label} by the customer."
    url = f"/service-jobs/{quote.job_id}/quotes"

    recipients: set[str] = set()
    owner = await _tenant_owner_id(db, quote.tenant_id)
    if owner:
        recipients.add(str(owner))
    staff = await _assigned_staff_id(db, quote.job_id)
    if staff:
        recipients.add(str(staff))
    for rid in recipients:
        _add(db, user_id=uuid.UUID(rid), tenant_id=quote.tenant_id,
             ntype="quote.decision", title=title, body=body, url=url, source_id=quote.id)
