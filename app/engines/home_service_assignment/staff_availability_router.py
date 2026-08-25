"""Per-technician time off and date overrides.

The availability board has had cells for both since it was built, with nothing behind
them -- the page said so on screen rather than showing empty boxes. These are the writes
that make those cells real.

Two separate things on purpose:

* An OVERRIDE changes a technician's hours for one date ("Wed 29 Jul, 10:00-16:00").
* TIME OFF removes them for a period, with a reason.

Every route is tenant-scoped from the token, never from the body: a staff id belonging to
another provider must not be writable by passing it in.
"""
from __future__ import annotations

import datetime as dt
import uuid

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_tenant_owner_mutation
from app.dependencies.auth import UserContext, get_current_user
from app.dependencies.db import get_db
from app.exceptions import ServiceOSException
from app.schemas.base import ApiResponse, ok

router = APIRouter(prefix="/v1/provider/team", tags=["Team Availability"])
ENGINE_ID = "assignment"


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", None) or "—"


async def _assert_own_staff(db: AsyncSession, tenant_id: uuid.UUID, staff_member_id: uuid.UUID) -> None:
    """The staff row must belong to the caller's tenant.

    Checked on every write. Without it, a provider could book another provider's
    technician off simply by knowing their id -- the tenant scope on the INSERT alone
    would not stop the row being created against someone else's person.
    """
    row = (await db.execute(text(
        "SELECT 1 FROM provider_team_members "
        "WHERE id = CAST(:sid AS uuid) AND tenant_id = CAST(:tid AS uuid)"
    ), {"sid": str(staff_member_id), "tid": str(tenant_id)})).first()
    if not row:
        raise ServiceOSException("NOT_FOUND", "That team member was not found.", status_code=404)


class TimeOffRequest(BaseModel):
    start_date: dt.date
    end_date: dt.date
    all_day: bool = True
    start_time: dt.time | None = None
    end_time: dt.time | None = None
    reason: str | None = Field(None, max_length=300)

    @model_validator(mode="after")
    def _sane_range(self):
        if self.end_date < self.start_date:
            raise ValueError("end_date cannot be before start_date.")
        if not self.all_day:
            if not self.start_time or not self.end_time:
                raise ValueError("A part-day absence needs a start and end time.")
            if self.end_time <= self.start_time:
                raise ValueError("end_time must be after start_time.")
        return self


class OverrideRequest(BaseModel):
    override_date: dt.date
    start_time: dt.time | None = None
    end_time: dt.time | None = None
    full_day_closed: bool = False
    reason: str | None = Field(None, max_length=300)

    @model_validator(mode="after")
    def _sane_hours(self):
        if self.full_day_closed:
            return self
        if not self.start_time or not self.end_time:
            raise ValueError("An override needs a start and end time, or full_day_closed.")
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time.")
        return self


# ── Time off ─────────────────────────────────────────────────────────────────

@router.get("/{staff_member_id}/time-off", response_model=ApiResponse,
            summary="Time off for one technician")
async def list_time_off(
    staff_member_id: uuid.UUID,
    upcoming_only: bool = False,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    r: Request = ...,
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = uuid.UUID(user.tenant_id)
    await _assert_own_staff(db, tenant_id, staff_member_id)
    sql = ("SELECT id, start_date, end_date, all_day, start_time, end_time, reason, status "
           "FROM staff_time_off WHERE tenant_id = CAST(:tid AS uuid) "
           "AND staff_member_id = CAST(:sid AS uuid) AND status <> 'cancelled'")
    if upcoming_only:
        # "Upcoming" includes leave running TODAY -- someone off right now is not history.
        sql += " AND end_date >= CURRENT_DATE"
    count_sql = f"SELECT count(*) FROM ({sql}) AS filtered_time_off"
    params = {"tid": str(tenant_id), "sid": str(staff_member_id), "limit": limit, "offset": offset}
    total = int((await db.execute(text(count_sql), params)).scalar() or 0)
    sql += " ORDER BY start_date LIMIT :limit OFFSET :offset"
    rows = (await db.execute(text(sql), params)).all()
    return ok({
        "time_off": [dict(row._mapping) for row in rows],
        "pagination": {"total": total, "limit": limit, "offset": offset, "has_next": offset + limit < total},
    }, _rid(r), ENGINE_ID)


@router.post("/{staff_member_id}/time-off", response_model=ApiResponse, status_code=201,
             summary="Book a technician off")
async def create_time_off(
    staff_member_id: uuid.UUID,
    body: TimeOffRequest,
    r: Request = ...,
    user: UserContext = Depends(require_tenant_owner_mutation),
    db: AsyncSession = Depends(get_db),
):
    """Recorded as approved: the owner is entering it, so there is nobody left to approve
    it. The status column exists so a request flow can be added later without a migration
    and without back-filling a meaning onto rows that never had one."""
    tenant_id = uuid.UUID(user.tenant_id)
    await _assert_own_staff(db, tenant_id, staff_member_id)
    new_id = uuid.uuid4()
    await db.execute(text(
        "INSERT INTO staff_time_off (id, tenant_id, staff_member_id, start_date, end_date, "
        "  all_day, start_time, end_time, reason, status, created_by_user_id) "
        "VALUES (CAST(:id AS uuid), CAST(:tid AS uuid), CAST(:sid AS uuid), :sd, :ed, "
        "  :all_day, :st, :et, :reason, 'approved', CAST(:uid AS uuid))"
    ), {
        "id": str(new_id), "tid": str(tenant_id), "sid": str(staff_member_id),
        "sd": body.start_date, "ed": body.end_date, "all_day": body.all_day,
        "st": body.start_time, "et": body.end_time, "reason": body.reason,
        "uid": user.user_id,
    })
    await db.commit()
    return ok({"id": str(new_id), "status": "approved"}, _rid(r), ENGINE_ID)


@router.delete("/{staff_member_id}/time-off/{time_off_id}", response_model=ApiResponse,
               summary="Cancel booked time off")
async def cancel_time_off(
    staff_member_id: uuid.UUID,
    time_off_id: uuid.UUID,
    r: Request = ...,
    user: UserContext = Depends(require_tenant_owner_mutation),
    db: AsyncSession = Depends(get_db),
):
    """Marked cancelled rather than deleted. Someone asking "why was nobody available on
    the 4th" deserves an answer, and a deleted row cannot give one."""
    tenant_id = uuid.UUID(user.tenant_id)
    result = await db.execute(text(
        "UPDATE staff_time_off SET status = 'cancelled', updated_at = now() "
        "WHERE id = CAST(:id AS uuid) AND tenant_id = CAST(:tid AS uuid) "
        "  AND staff_member_id = CAST(:sid AS uuid)"
    ), {"id": str(time_off_id), "tid": str(tenant_id), "sid": str(staff_member_id)})
    await db.commit()
    if result.rowcount == 0:
        raise ServiceOSException("NOT_FOUND", "That time off was not found.", status_code=404)
    return ok({"id": str(time_off_id), "status": "cancelled"}, _rid(r), ENGINE_ID)


# ── Date overrides ───────────────────────────────────────────────────────────

@router.get("/{staff_member_id}/overrides", response_model=ApiResponse,
            summary="Date overrides for one technician")
async def list_overrides(
    staff_member_id: uuid.UUID,
    from_date: dt.date | None = None,
    to_date: dt.date | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    r: Request = ...,
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = uuid.UUID(user.tenant_id)
    await _assert_own_staff(db, tenant_id, staff_member_id)
    sql = ("SELECT id, override_date, start_time, end_time, full_day_closed, reason "
           "FROM staff_availability_overrides WHERE tenant_id = CAST(:tid AS uuid) "
           "AND staff_member_id = CAST(:sid AS uuid)")
    params: dict = {"tid": str(tenant_id), "sid": str(staff_member_id)}
    if from_date:
        sql += " AND override_date >= :from_date"
        params["from_date"] = from_date
    if to_date:
        sql += " AND override_date <= :to_date"
        params["to_date"] = to_date
    total = int((await db.execute(text(f"SELECT count(*) FROM ({sql}) AS filtered_overrides"), params)).scalar() or 0)
    params.update({"limit": limit, "offset": offset})
    sql += " ORDER BY override_date LIMIT :limit OFFSET :offset"
    rows = (await db.execute(text(sql), params)).all()
    return ok({
        "overrides": [dict(row._mapping) for row in rows],
        "pagination": {"total": total, "limit": limit, "offset": offset, "has_next": offset + limit < total},
    }, _rid(r), ENGINE_ID)


@router.put("/{staff_member_id}/overrides", response_model=ApiResponse,
            summary="Set (or replace) one day's hours for a technician")
async def upsert_override(
    staff_member_id: uuid.UUID,
    body: OverrideRequest,
    r: Request = ...,
    user: UserContext = Depends(require_tenant_owner_mutation),
    db: AsyncSession = Depends(get_db),
):
    """PUT, not POST: one day has one set of hours.

    Upserted on (staff, date) so editing Wednesday twice replaces Wednesday rather than
    leaving two contradictory rows for the resolver to choose between.
    """
    tenant_id = uuid.UUID(user.tenant_id)
    await _assert_own_staff(db, tenant_id, staff_member_id)
    await db.execute(text(
        "INSERT INTO staff_availability_overrides (id, tenant_id, staff_member_id, "
        "  override_date, start_time, end_time, full_day_closed, reason, created_by_user_id) "
        "VALUES (gen_random_uuid(), CAST(:tid AS uuid), CAST(:sid AS uuid), :d, :st, :et, "
        "  :closed, :reason, CAST(:uid AS uuid)) "
        "ON CONFLICT (staff_member_id, override_date) DO UPDATE SET "
        "  start_time = EXCLUDED.start_time, end_time = EXCLUDED.end_time, "
        "  full_day_closed = EXCLUDED.full_day_closed, reason = EXCLUDED.reason, "
        "  updated_at = now()"
    ), {
        "tid": str(tenant_id), "sid": str(staff_member_id), "d": body.override_date,
        "st": body.start_time, "et": body.end_time, "closed": body.full_day_closed,
        "reason": body.reason, "uid": user.user_id,
    })
    await db.commit()
    return ok({"override_date": body.override_date.isoformat()}, _rid(r), ENGINE_ID)


@router.delete("/{staff_member_id}/overrides/{override_date}", response_model=ApiResponse,
               summary="Drop an override, returning the day to the weekly pattern")
async def delete_override(
    staff_member_id: uuid.UUID,
    override_date: dt.date,
    r: Request = ...,
    user: UserContext = Depends(require_tenant_owner_mutation),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = uuid.UUID(user.tenant_id)
    result = await db.execute(text(
        "DELETE FROM staff_availability_overrides "
        "WHERE tenant_id = CAST(:tid AS uuid) AND staff_member_id = CAST(:sid AS uuid) "
        "  AND override_date = :d"
    ), {"tid": str(tenant_id), "sid": str(staff_member_id), "d": override_date})
    await db.commit()
    if result.rowcount == 0:
        raise ServiceOSException("NOT_FOUND", "No override on that date.", status_code=404)
    # Deleted rather than cancelled: an override is a schedule edit, and removing it
    # simply restores the weekly pattern -- there is no history question to answer.
    return ok({"override_date": override_date.isoformat(), "removed": True}, _rid(r), ENGINE_ID)
