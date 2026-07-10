"""Sprint 19 — Sequential record number generation.

Format: PREFIX-YYYYMMDD-NNNNNN
Example: BK-20260702-000001, JOB-20260702-000001, APPT-20260702-000001, LEAD-20260702-000001

Within a DB transaction, COUNT(*) + 1 is safe because the parent transaction
holds a row-lock on the new record being inserted.
"""
from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.final_records.constants import (
    NUMBER_PREFIX_BOOKING,
    NUMBER_PREFIX_JOB,
    NUMBER_PREFIX_APPOINTMENT,
    NUMBER_PREFIX_LEAD,
)


def _today_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d")


def _format_number(prefix: str, date_str: str, seq: int) -> str:
    return f"{prefix}-{date_str}-{seq:06d}"


async def generate_booking_number(db: AsyncSession) -> str:
    from app.engines.final_records.models import ServiceBooking
    date_str = _today_str()
    prefix   = f"{NUMBER_PREFIX_BOOKING}-{date_str}-"
    result   = await db.execute(
        select(func.count()).where(
            ServiceBooking.booking_number.like(f"{prefix}%")
        )
    )
    count = result.scalar() or 0
    return _format_number(NUMBER_PREFIX_BOOKING, date_str, count + 1)


async def generate_job_number(db: AsyncSession) -> str:
    from app.engines.final_records.models import ServiceJob
    date_str = _today_str()
    prefix   = f"{NUMBER_PREFIX_JOB}-{date_str}-"
    result   = await db.execute(
        select(func.count()).where(
            ServiceJob.job_number.like(f"{prefix}%")
        )
    )
    count = result.scalar() or 0
    return _format_number(NUMBER_PREFIX_JOB, date_str, count + 1)


async def generate_appointment_number(db: AsyncSession) -> str:
    from app.engines.final_records.models import CoachingAppointment
    date_str = _today_str()
    prefix   = f"{NUMBER_PREFIX_APPOINTMENT}-{date_str}-"
    result   = await db.execute(
        select(func.count()).where(
            CoachingAppointment.appointment_number.like(f"{prefix}%")
        )
    )
    count = result.scalar() or 0
    return _format_number(NUMBER_PREFIX_APPOINTMENT, date_str, count + 1)


async def generate_lead_number(db: AsyncSession) -> str:
    from app.engines.final_records.models import RealEstateLead
    date_str = _today_str()
    prefix   = f"{NUMBER_PREFIX_LEAD}-{date_str}-"
    result   = await db.execute(
        select(func.count()).where(
            RealEstateLead.lead_number.like(f"{prefix}%")
        )
    )
    count = result.scalar() or 0
    return _format_number(NUMBER_PREFIX_LEAD, date_str, count + 1)
