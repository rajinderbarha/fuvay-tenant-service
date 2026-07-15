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

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.platform_notifications.models import InAppNotification
from app.engines.quote_checklist.models import ServiceJobQuote


async def _tenant_owner_id(db: AsyncSession, tenant_id) -> uuid.UUID | None:
    from app.engines.tenant_engine.models import Tenant
    t = await db.get(Tenant, tenant_id)
    return getattr(t, "owner_user_id", None) if t else None


async def _assigned_staff_id(db: AsyncSession, job_id) -> uuid.UUID | None:
    from app.engines.final_records.models import ServiceJob
    job = await db.get(ServiceJob, job_id)
    return getattr(job, "assigned_staff_id", None) if job else None


def _add(db, *, user_id, tenant_id, ntype, title, body, url, source_id=None):
    db.add(InAppNotification(
        user_id=user_id, tenant_id=tenant_id,
        notification_type=ntype, title=title, body=body,
        action_url=url, action_label="View quote",
        source_record_type="service_job_quote", source_record_id=source_id,
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
         source_id=quote.id)


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
