"""Technician Mobile App Phase P — Schedule & Availability.

Reuses the canonical recurring-hours table (`provider_availability_rules`,
via `availability_resolver.py`'s own query helpers -- never re-queried
independently) and `service_jobs` for assignments. Adds exactly the two
genuinely-missing pieces confirmed by audit: a technician-facing day-by-day
projection endpoint (none existed -- `availability_resolver.py` is
tenant/dispatch-side only) and the new `StaffBlockedTime`/
`StaffTimeOffRequest` tables for schedule exceptions leave/time-off never
existed anywhere in the repo).

Never a second availability state machine: live presence
(available/busy/offline) remains exactly `ProviderTeamMember.availability_state`
via the existing `PUT /v1/staff/me/availability` (Phase-Home), untouched here.
"""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ServiceOSException
from app.engines.home_service_assignment.availability_resolver import (
    _fetch_staff_pattern, _fetch_assignments, _time_str, DEFAULT_TIMEZONE,
)
from app.engines.home_service_assignment.schedule_models import StaffBlockedTime, StaffTimeOffRequest

_TERMINAL_STATUSES = {"completed", "cancelled", "failed", "closed_estimate_declined"}
_ACTIVE_LEAVE_STATUSES = {"pending", "approved"}


class MobileScheduleService:
    async def _resolve_staff_id(self, db: AsyncSession, user_id: uuid.UUID) -> uuid.UUID:
        from app.engines.home_service_assignment.staff_model import ProviderTeamMember
        res = await db.execute(select(ProviderTeamMember.id).where(ProviderTeamMember.user_id == user_id))
        row = res.scalars().first()
        return row if row else user_id

    async def _blocked_times(self, db: AsyncSession, tenant_id: uuid.UUID, staff_id: uuid.UUID, start: dt.date, end: dt.date) -> list[StaffBlockedTime]:
        res = await db.execute(select(StaffBlockedTime).where(
            StaffBlockedTime.tenant_id == tenant_id, StaffBlockedTime.staff_member_id == staff_id,
            StaffBlockedTime.block_date >= start, StaffBlockedTime.block_date <= end,
        ))
        return list(res.scalars().all())

    async def _time_off(self, db: AsyncSession, tenant_id: uuid.UUID, staff_id: uuid.UUID, start: dt.date, end: dt.date) -> list[StaffTimeOffRequest]:
        res = await db.execute(select(StaffTimeOffRequest).where(
            StaffTimeOffRequest.tenant_id == tenant_id, StaffTimeOffRequest.staff_member_id == staff_id,
            StaffTimeOffRequest.status.in_(_ACTIVE_LEAVE_STATUSES),
            StaffTimeOffRequest.start_date <= end, StaffTimeOffRequest.end_date >= start,
        ))
        return list(res.scalars().all())

    async def get_schedule(self, db: AsyncSession, user_id: uuid.UUID, tenant_id: uuid.UUID, date_from: dt.date, date_to: dt.date) -> dict:
        if date_to < date_from:
            raise ServiceOSException("VALIDATION_ERROR", "'to' must not be before 'from'.", status_code=422)
        if (date_to - date_from).days > 31:
            raise ServiceOSException("VALIDATION_ERROR", "Date range cannot exceed 31 days.", status_code=422)

        staff_id = await self._resolve_staff_id(db, user_id)
        blocks = await self._blocked_times(db, tenant_id, staff_id, date_from, date_to)
        leaves = await self._time_off(db, tenant_id, staff_id, date_from, date_to)
        pending_time_off_count = len([l for l in leaves if l.status == "pending"])

        days = []
        cursor = date_from
        while cursor <= date_to:
            days.append(await self._build_day(db, tenant_id, staff_id, cursor, blocks, leaves))
            cursor += dt.timedelta(days=1)

        return {
            "timezone": DEFAULT_TIMEZONE,
            "days": days,
            "pending_time_off_count": pending_time_off_count,
            "last_synced_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        }

    async def _build_day(self, db, tenant_id, staff_id, target_date: dt.date, blocks: list[StaffBlockedTime], leaves: list[StaffTimeOffRequest]) -> dict:
        dow = target_date.isoweekday() % 7  # 0=Sunday, matches provider_availability_rules convention
        pattern = await _fetch_staff_pattern(db, tenant_id, staff_id, dow)
        assignments = await _fetch_assignments(db, tenant_id, staff_id, target_date)

        items: list[dict] = []
        assigned_job_count = 0
        for a in assignments:
            if a["status"] in _TERMINAL_STATUSES:
                continue
            assigned_job_count += 1
            items.append({
                "type": "assigned_job", "job_id": str(a["id"]), "job_reference": a["job_number"],
                "time_label": a["scheduled_time_window"], "workflow_status": a["status"],
            })

        day_leaves = [l for l in leaves if l.start_date <= target_date <= l.end_date]
        for l in day_leaves:
            items.append({
                "type": "approved_leave" if l.status == "approved" else "pending_leave",
                "id": str(l.id), "reason_category": l.reason_category,
                "is_full_day": l.is_full_day,
                "start_time": _time_str(l.start_time) if l.start_time else None,
                "end_time": _time_str(l.end_time) if l.end_time else None,
            })

        day_blocks = [b for b in blocks if b.block_date == target_date]
        for b in day_blocks:
            items.append({
                "type": "blocked_time", "id": str(b.id), "start_time": _time_str(b.start_time),
                "end_time": _time_str(b.end_time), "reason": b.reason, "source": b.source,
            })

        open_slot_count = 0
        working_hours_label = None
        if pattern:
            working_hours_label = f"{_time_str(pattern['start_time'])}–{_time_str(pattern['end_time'])}"
            full_day_leave = any(l.is_full_day for l in day_leaves if l.status == "approved")
            if not full_day_leave:
                max_jobs = pattern.get("max_jobs_per_day") or 0
                open_slot_count = max(max_jobs - assigned_job_count - len(day_blocks), 0)
                if open_slot_count > 0:
                    items.append({"type": "available_slot", "time_label": working_hours_label, "duration_minutes": 60})

        items.sort(key=lambda i: i.get("time_label") or i.get("start_time") or "")

        return {
            "date": target_date.isoformat(),
            "day_of_week": dow,
            "working_hours_label": working_hours_label,
            "assigned_job_count": assigned_job_count,
            "open_slot_count": open_slot_count,
            "pending_leave_count": len([l for l in day_leaves if l.status == "pending"]),
            "items": items,
        }

    # ── Blocked time (spec section 5) ────────────────────────────────────

    async def create_blocked_time(self, db: AsyncSession, user_id: uuid.UUID, tenant_id: uuid.UUID,
                                   block_date: dt.date, start_time: dt.time, end_time: dt.time, reason: str | None) -> dict:
        if end_time <= start_time:
            raise ServiceOSException("VALIDATION_ERROR", "End time must be after start time.", status_code=422)
        staff_id = await self._resolve_staff_id(db, user_id)

        assignments = await _fetch_assignments(db, tenant_id, staff_id, block_date)
        active = [a for a in assignments if a["status"] not in _TERMINAL_STATUSES]
        if active:
            raise ServiceOSException(
                "SCHEDULE_CONFLICT",
                "This time conflicts with an assigned job. Blocked time cannot be added over an assignment.",
                status_code=409,
                context={"conflicting_jobs": [{"job_id": str(a["id"]), "job_reference": a["job_number"], "time_label": a["scheduled_time_window"]} for a in active]},
            )

        block = StaffBlockedTime(
            tenant_id=tenant_id, staff_member_id=staff_id, block_date=block_date,
            start_time=start_time, end_time=end_time, reason=reason,
            source="staff", created_by_user_id=user_id,
        )
        db.add(block)
        await db.commit()
        return block.to_dict()

    async def remove_blocked_time(self, db: AsyncSession, user_id: uuid.UUID, tenant_id: uuid.UUID, block_id: uuid.UUID) -> dict:
        staff_id = await self._resolve_staff_id(db, user_id)
        block = await db.get(StaffBlockedTime, block_id)
        if not block or str(block.tenant_id) != str(tenant_id):
            raise ServiceOSException("ENTITY_NOT_FOUND", "Blocked time not found.", status_code=404)
        if str(block.staff_member_id) != str(staff_id):
            raise ServiceOSException("ENTITY_NOT_ASSIGNED", "You can only remove your own blocked time.", status_code=403)
        if block.source != "staff":
            raise ServiceOSException("BLOCK_NOT_STAFF_OWNED", "Only technician-created blocks can be removed here.", status_code=403)
        if block.block_date < dt.date.today():
            raise ServiceOSException("BLOCK_IN_PAST", "Past blocked time cannot be removed.", status_code=422)
        await db.delete(block)
        await db.commit()
        return {"removed": True}

    # ── Time off (spec section 6) ────────────────────────────────────────

    async def submit_time_off(self, db: AsyncSession, user_id: uuid.UUID, tenant_id: uuid.UUID, *,
                               start_date: dt.date, end_date: dt.date, is_full_day: bool,
                               start_time: dt.time | None, end_time: dt.time | None,
                               reason_category: str, note: str | None) -> dict:
        if end_date < start_date:
            raise ServiceOSException("VALIDATION_ERROR", "End date must not be before start date.", status_code=422)
        if not is_full_day and (start_time is None or end_time is None or end_time <= start_time):
            raise ServiceOSException("VALIDATION_ERROR", "Partial-day requests require a valid start and end time.", status_code=422)
        staff_id = await self._resolve_staff_id(db, user_id)

        req = StaffTimeOffRequest(
            tenant_id=tenant_id, staff_member_id=staff_id, start_date=start_date, end_date=end_date,
            is_full_day=is_full_day, start_time=start_time, end_time=end_time,
            reason_category=reason_category, note=note, status="pending", requested_by_user_id=user_id,
        )
        db.add(req)
        await db.commit()
        return req.to_dict()

    async def cancel_time_off(self, db: AsyncSession, user_id: uuid.UUID, tenant_id: uuid.UUID, request_id: uuid.UUID) -> dict:
        staff_id = await self._resolve_staff_id(db, user_id)
        req = await db.get(StaffTimeOffRequest, request_id)
        if not req or str(req.tenant_id) != str(tenant_id):
            raise ServiceOSException("ENTITY_NOT_FOUND", "Time-off request not found.", status_code=404)
        if str(req.staff_member_id) != str(staff_id):
            raise ServiceOSException("ENTITY_NOT_ASSIGNED", "You can only cancel your own request.", status_code=403)
        if req.status not in ("pending", "approved"):
            raise ServiceOSException("TIME_OFF_NOT_CANCELLABLE", f"A request that is '{req.status}' cannot be cancelled.", status_code=409)
        req.status = "cancelled"
        req.cancelled_at = dt.datetime.now(dt.timezone.utc)
        db.add(req)
        await db.commit()
        return req.to_dict()

    async def list_time_off(self, db: AsyncSession, user_id: uuid.UUID, tenant_id: uuid.UUID) -> list[dict]:
        staff_id = await self._resolve_staff_id(db, user_id)
        res = await db.execute(select(StaffTimeOffRequest).where(
            StaffTimeOffRequest.tenant_id == tenant_id, StaffTimeOffRequest.staff_member_id == staff_id,
        ).order_by(StaffTimeOffRequest.created_at.desc()))
        return [r.to_dict() for r in res.scalars().all()]
