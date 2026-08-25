"""MODULE-L5-22 — review lifecycle notifications.

The review engine recorded reviews and replies and recomputed rating summaries,
but never told anyone. A customer's new review never reached the provider, and a
provider's reply never reached the customer — so a review conversation happened
entirely in silence. This adds targeted in-app notifications, reusing the shared
InAppNotification the chat/quote/complaint engines use.
"""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.platform_notifications.models import InAppNotification
from app.engines.customer_reviews.models import CustomerReview


async def _tenant_owner_id(db: AsyncSession, tenant_id) -> uuid.UUID | None:
    from app.engines.tenant_engine.models import Tenant
    t = await db.get(Tenant, tenant_id)
    return getattr(t, "owner_user_id", None) if t else None


async def _staff_user_id(db: AsyncSession, staff_member_id) -> uuid.UUID | None:
    """Map a provider_team_members.id to the login user it belongs to.

    Team members exist without a login (a technician who was never invited),
    in which case there is no one to notify and None is returned.
    """
    if not staff_member_id:
        return None
    from sqlalchemy import text as _text
    try:
        row = (await db.execute(
            _text("SELECT user_id FROM provider_team_members WHERE id = :sid"),
            {"sid": str(staff_member_id)},
        )).fetchone()
    except Exception:
        return None
    return row.user_id if row and row.user_id else None


def _add(db, *, user_id, tenant_id, ntype, title, body, url, source_id):
    db.add(InAppNotification(
        user_id=user_id, tenant_id=tenant_id,
        notification_type=ntype, title=title, body=body,
        action_url=url, action_label="View review",
        source_record_type="customer_review", source_record_id=source_id,
        severity="info",
    ))


async def notify_provider_new_review(db: AsyncSession, review: CustomerReview) -> None:
    """Tell the provider side (owner + the reviewed technician) about a new review."""
    stars = "★" * int(review.overall_rating or 0)
    title = f"New {int(review.overall_rating or 0)}-star review"
    body = (review.review_text or f"A customer left you a {stars} review.").strip()
    if len(body) > 140:
        body = body[:137] + "…"

    recipients: set[str] = set()
    owner = await _tenant_owner_id(db, review.tenant_id)
    if owner:
        recipients.add(str(owner))
    # `staff_member_id` is a provider_team_members.id, NOT a users.id, but it
    # was being used directly as the notification's `user_id` -- which would
    # address the notification to a user that does not exist, so the reviewed
    # technician would never see it. This never fired in practice because
    # nothing ever populated staff_member_id; now that submit_review resolves
    # it from the job, the team member has to be mapped to its login user.
    staff_user_id = await _staff_user_id(db, review.staff_member_id)
    if staff_user_id:
        recipients.add(str(staff_user_id))
    for rid in recipients:
        _add(db, user_id=uuid.UUID(rid), tenant_id=review.tenant_id,
             ntype="review.new", title=title, body=body,
             url="/provider/reviews", source_id=review.id)


async def notify_customer_review_reply(db: AsyncSession, review: CustomerReview) -> None:
    """Tell the customer their provider replied to their review."""
    if not review.customer_id:
        return
    _add(db, user_id=review.customer_id, tenant_id=review.tenant_id,
         ntype="review.reply",
         title="Your provider replied to your review",
         body="Tap to read your provider's response.",
         url="/customer/reviews", source_id=review.id)
