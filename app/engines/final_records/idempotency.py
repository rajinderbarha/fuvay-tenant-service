"""Sprint 19 — ConfirmationLockService.

Prevents duplicate final records when a customer retries the confirm endpoint.
Uses a DB unique constraint on (draft_type, draft_id) as the hard guard,
with a soft pre-check before attempting the insert.
"""
from __future__ import annotations
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.final_records.constants import (
    CONFIRM_STATUS_CREATED,
    ERR_DUPLICATE_CONFIRMATION,
)
from app.engines.final_records.models import CustomerBookingConfirmation


class ConfirmationLockService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_existing(
        self,
        draft_type: str,
        draft_id:   uuid.UUID,
    ) -> CustomerBookingConfirmation | None:
        """Return existing confirmation record if the draft was already confirmed."""
        result = await self.db.execute(
            select(CustomerBookingConfirmation).where(
                CustomerBookingConfirmation.draft_type == draft_type,
                CustomerBookingConfirmation.draft_id   == draft_id,
                CustomerBookingConfirmation.status     == CONFIRM_STATUS_CREATED,
            )
        )
        return result.scalars().first()

    async def create_lock(
        self,
        draft_type:      str,
        draft_id:        uuid.UUID,
        customer_id:     uuid.UUID | None,
        idempotency_key: str | None,
        result_type:     str,
        result_id:       uuid.UUID,
        result_number:   str,
    ) -> CustomerBookingConfirmation:
        """Insert the confirmation lock record. Raises IntegrityError on duplicate."""
        record = CustomerBookingConfirmation(
            customer_id     = customer_id,
            draft_type      = draft_type,
            draft_id        = draft_id,
            idempotency_key = idempotency_key,
            result_type     = result_type,
            result_id       = result_id,
            result_number   = result_number,
            status          = CONFIRM_STATUS_CREATED,
        )
        self.db.add(record)
        await self.db.flush()
        await self.db.refresh(record)
        return record

    async def check_and_raise_if_duplicate(
        self,
        draft_type: str,
        draft_id:   uuid.UUID,
    ) -> CustomerBookingConfirmation | None:
        """
        Returns the existing confirmation if already confirmed, so the caller
        can return it as an idempotent success instead of creating a duplicate.
        Returns None if no prior confirmation exists.
        """
        return await self.get_existing(draft_type, draft_id)
