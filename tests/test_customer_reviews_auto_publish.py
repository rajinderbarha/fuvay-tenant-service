"""Customer ratings publish immediately; moderation handles exceptions only."""
from datetime import datetime, timezone
from types import SimpleNamespace
import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.engines.customer_reviews.review_service import ReviewService


@pytest.mark.asyncio
async def test_customer_edit_stays_public_without_admin_approval():
    service = ReviewService()
    customer_id = uuid.uuid4()
    review = SimpleNamespace(
        id=uuid.uuid4(), tenant_id=uuid.uuid4(), customer_id=customer_id,
        status="approved", visibility="public", submitted_at=datetime.now(timezone.utc),
        approved_at=datetime.now(timezone.utc), overall_rating=4,
        provider_rating=None, staff_rating=None, communication_rating=None,
        punctuality_rating=None, quality_rating=None, value_rating=None,
        review_title=None, review_text="Good", review_tags=None, media_urls=None,
    )
    db = SimpleNamespace(flush=AsyncMock(), commit=AsyncMock())

    with patch.object(service, "_get_review", AsyncMock(return_value=review)), \
         patch.object(service, "_get_policy", AsyncMock(return_value=SimpleNamespace(edit_window_hours=48))), \
         patch.object(service, "_log_event", AsyncMock()), \
         patch.object(service, "_trigger_aggregation", AsyncMock()) as aggregate:
        result = await service.edit_review(
            db, review.id, customer_id, {"overall_rating": 5},
        )

    assert result.status == "approved"
    assert result.visibility == "public"
    aggregate.assert_awaited_once_with(db, review)


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["flagged", "hidden"])
async def test_customer_edit_cannot_bypass_exception_moderation(status):
    service = ReviewService()
    customer_id = uuid.uuid4()
    review = SimpleNamespace(
        id=uuid.uuid4(), customer_id=customer_id, status=status,
    )
    with patch.object(service, "_get_review", AsyncMock(return_value=review)):
        with pytest.raises(ValueError, match="REVIEW_NOT_EDITABLE"):
            await service.edit_review(
                SimpleNamespace(), review.id, customer_id, {"overall_rating": 5},
            )


@pytest.mark.asyncio
async def test_policy_updates_cannot_restore_manual_review_approval():
    service = ReviewService()
    policy = SimpleNamespace(
        auto_approve_enabled=True, require_admin_moderation=False,
        allow_review_edit=True,
    )
    db = SimpleNamespace(commit=AsyncMock())
    with patch.object(service, "get_policy", AsyncMock(return_value=policy)):
        result = await service.update_policy(
            db, uuid.uuid4(), {
                "auto_approve_enabled": False,
                "require_admin_moderation": True,
                "allow_review_edit": False,
            },
        )

    assert result.auto_approve_enabled is True
    assert result.require_admin_moderation is False
    assert result.allow_review_edit is False
