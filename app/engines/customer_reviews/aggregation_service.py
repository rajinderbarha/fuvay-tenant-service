"""Sprint 24 — Rating Aggregation Service."""
import uuid
from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.engines.customer_reviews.models import (
    CustomerReview, TenantRatingSummary, StaffRatingSummary,
)
from app.engines.customer_reviews.constants import STATUS_APPROVED, EVT_RATING_UPDATED


class RatingAggregationService:

    async def recompute_tenant_summary(self, db: AsyncSession, tenant_id: uuid.UUID) -> TenantRatingSummary:
        rows = (await db.execute(
            select(CustomerReview).where(
                CustomerReview.tenant_id == tenant_id,
                CustomerReview.status    == STATUS_APPROVED,
            )
        )).scalars().all()

        summary = await self._get_or_create_tenant_summary(db, tenant_id)

        if not rows:
            summary.total_reviews = 0
            summary.average_rating = Decimal("0.00")
            summary.provider_average_rating      = Decimal("0.00")
            summary.communication_average_rating = Decimal("0.00")
            summary.punctuality_average_rating   = Decimal("0.00")
            summary.quality_average_rating       = Decimal("0.00")
            summary.value_average_rating         = Decimal("0.00")
            for attr in ["five_star_count","four_star_count","three_star_count","two_star_count","one_star_count"]:
                setattr(summary, attr, 0)
            summary.last_review_at = None
            summary.updated_at = datetime.now(timezone.utc)
            return summary

        n = len(rows)
        summary.total_reviews  = n
        summary.average_rating = self._avg([r.overall_rating for r in rows])
        summary.provider_average_rating      = self._avg([r.provider_rating for r in rows if r.provider_rating])
        summary.communication_average_rating = self._avg([r.communication_rating for r in rows if r.communication_rating])
        summary.punctuality_average_rating   = self._avg([r.punctuality_rating for r in rows if r.punctuality_rating])
        summary.quality_average_rating       = self._avg([r.quality_rating for r in rows if r.quality_rating])
        summary.value_average_rating         = self._avg([r.value_rating for r in rows if r.value_rating])

        summary.five_star_count  = sum(1 for r in rows if r.overall_rating == 5)
        summary.four_star_count  = sum(1 for r in rows if r.overall_rating == 4)
        summary.three_star_count = sum(1 for r in rows if r.overall_rating == 3)
        summary.two_star_count   = sum(1 for r in rows if r.overall_rating == 2)
        summary.one_star_count   = sum(1 for r in rows if r.overall_rating == 1)

        approved_at_vals = [r.approved_at for r in rows if r.approved_at]
        summary.last_review_at = max(approved_at_vals) if approved_at_vals else None
        summary.updated_at = datetime.now(timezone.utc)

        return summary

    async def recompute_staff_summary(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        staff_member_id: uuid.UUID,
    ) -> StaffRatingSummary:
        rows = (await db.execute(
            select(CustomerReview).where(
                CustomerReview.tenant_id       == tenant_id,
                CustomerReview.staff_member_id == staff_member_id,
                CustomerReview.status          == STATUS_APPROVED,
            )
        )).scalars().all()

        summary = await self._get_or_create_staff_summary(db, tenant_id, staff_member_id)

        if not rows:
            summary.total_reviews  = 0
            summary.average_rating = Decimal("0.00")
            summary.communication_average_rating = Decimal("0.00")
            summary.punctuality_average_rating   = Decimal("0.00")
            summary.quality_average_rating       = Decimal("0.00")
            summary.last_review_at = None
            summary.updated_at = datetime.now(timezone.utc)
            return summary

        summary.total_reviews  = len(rows)
        summary.average_rating = self._avg([r.staff_rating or r.overall_rating for r in rows])
        summary.communication_average_rating = self._avg([r.communication_rating for r in rows if r.communication_rating])
        summary.punctuality_average_rating   = self._avg([r.punctuality_rating for r in rows if r.punctuality_rating])
        summary.quality_average_rating       = self._avg([r.quality_rating for r in rows if r.quality_rating])
        approved_at_vals = [r.approved_at for r in rows if r.approved_at]
        summary.last_review_at = max(approved_at_vals) if approved_at_vals else None
        summary.updated_at = datetime.now(timezone.utc)
        return summary

    async def _get_or_create_tenant_summary(self, db: AsyncSession, tenant_id: uuid.UUID) -> TenantRatingSummary:
        r = await db.execute(select(TenantRatingSummary).where(TenantRatingSummary.tenant_id == tenant_id))
        obj = r.scalars().first()
        if not obj:
            obj = TenantRatingSummary(tenant_id=tenant_id)
            db.add(obj)
            await db.flush()
        return obj

    async def _get_or_create_staff_summary(
        self, db: AsyncSession, tenant_id: uuid.UUID, staff_member_id: uuid.UUID
    ) -> StaffRatingSummary:
        r = await db.execute(
            select(StaffRatingSummary).where(
                StaffRatingSummary.tenant_id      == tenant_id,
                StaffRatingSummary.staff_member_id == staff_member_id,
            )
        )
        obj = r.scalars().first()
        if not obj:
            obj = StaffRatingSummary(tenant_id=tenant_id, staff_member_id=staff_member_id)
            db.add(obj)
            await db.flush()
        return obj

    @staticmethod
    def _avg(values: list) -> Decimal:
        valid = [v for v in values if v is not None]
        if not valid:
            return Decimal("0.00")
        return Decimal(str(round(sum(valid) / len(valid), 2)))
