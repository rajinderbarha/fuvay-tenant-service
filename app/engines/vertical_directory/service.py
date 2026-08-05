"""VERTICAL-DIRECTORY-FRAMEWORK: one directory service per domain
(Providers/Staff/Customers/Complaints), every method requiring a
VerticalScope. Scoping is applied BEFORE search/filter/pagination/
aggregation -- never after, and never derived from a client-supplied
vertical id.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, func, and_, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_platform_audit
from app.dependencies.vertical_directory_scope import VerticalScope
from app.engines.tenant_engine.models import Tenant
from app.engines.vertical_catalog.models import TenantVerticalEnrollment, VerticalAuditLog
from app.engines.vertical_directory.models import StaffBusinessVertical, CustomerBusinessVertical
from app.engines.home_service_assignment.staff_model import ProviderTeamMember
from app.engines.auth.models import User
from app.engines.complaints.models import (
    CustomerComplaint, ComplaintMessage, ComplaintMedia, ComplaintEvent, ComplaintResolution,
)
from app.engines.complaints.complaint_service import ComplaintService
from app.engines.complaints.constants import (
    ACTOR_ADMIN, VIS_ADMIN_ONLY, VIS_PUBLIC, STATUS_UNDER_ADMIN_REVIEW,
)
from app.engines.final_records.models import ServiceJob
from app.exceptions import ServiceOSException, NotFoundException

# ServiceJob is the canonical Home-Services job table (not the dead
# field_ops `jobs` table the old global staff page queried against, per the
# platform's own established audit finding -- see MODULE-L5-35/36/38).
_ACTIVE_JOB_STATUSES = ("assigned", "in_progress", "pending_start", "on_the_way")
_ENGINE_ID = "vertical_directory"

ASSIGNMENT_STATUSES = ("pending", "active", "restricted", "suspended", "deactivated")
VERIFICATION_STATUSES = ("not_started", "in_review", "changes_requested", "verified", "rejected", "expired")


def _require_scope_domain(scope: VerticalScope, expected: str) -> None:
    if scope.domain != expected:
        raise ValueError(f"VerticalScope resolved for domain '{scope.domain}', expected '{expected}'")


# ═══════════════════════════════════════════════════════════════════════════
# PROVIDERS
# ═══════════════════════════════════════════════════════════════════════════

class VerticalProviderDirectoryService:
    """Reuses the existing TenantVerticalEnrollment relationship. Falls back
    to Tenant.vertical (the flat, always-set field) only for tenants that
    predate the enrollment table -- an unambiguous single-vertical case, not
    a guess."""

    async def _member_tenant_ids(self, db: AsyncSession, scope: VerticalScope) -> Any:
        # Both sides labeled "id" explicitly -- a plain .union() otherwise
        # exposes the FIRST select's column name on the compiled subquery
        # (.c.tenant_id here, not .c.id), which breaks every .c.id reference
        # below with a confusing AttributeError at call time.
        enrolled = select(TenantVerticalEnrollment.tenant_id.label("id")).where(
            TenantVerticalEnrollment.vertical_id == scope.vertical.id)
        legacy = select(Tenant.id.label("id")).where(
            Tenant.vertical == scope.vertical_key,
            Tenant.id.notin_(select(TenantVerticalEnrollment.tenant_id)),
        )
        return enrolled.union(legacy)

    async def list_providers(self, db: AsyncSession, scope: VerticalScope, *,
                             search: str | None = None, status: str | None = None,
                             page: int = 1, page_size: int = 25) -> dict:
        _require_scope_domain(scope, "providers")
        member_ids = await self._member_tenant_ids(db, scope)
        conditions = [Tenant.id.in_(member_ids)]
        if status:
            conditions.append(Tenant.status == status)
        if search:
            conditions.append(Tenant.business_name.ilike(f"%{search}%") | Tenant.tenant_name.ilike(f"%{search}%"))

        total = await db.scalar(select(func.count(Tenant.id)).where(*conditions))
        rows = (await db.execute(
            select(Tenant).where(*conditions).order_by(Tenant.created_at.desc())
            .offset((page - 1) * page_size).limit(page_size)
        )).scalars().all()

        tenant_ids = [t.id for t in rows]
        enrollments = {}
        if tenant_ids:
            enroll_rows = (await db.execute(select(TenantVerticalEnrollment).where(
                TenantVerticalEnrollment.tenant_id.in_(tenant_ids),
                TenantVerticalEnrollment.vertical_id == scope.vertical.id,
            ))).scalars().all()
            enrollments = {e.tenant_id: e for e in enroll_rows}

        items = []
        for t in rows:
            enr = enrollments.get(t.id)
            items.append({
                "tenant_id": str(t.id), "business_name": t.business_name or t.tenant_name,
                "registration_status": t.status, "verification_status": t.verification_status,
                "vertical_status": enr.status if enr else "legacy_primary_vertical",
                "activated_at": enr.activated_at.isoformat() if enr and enr.activated_at else None,
                "suspended_at": enr.suspended_at.isoformat() if enr and enr.suspended_at else None,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            })
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    async def get_provider(self, db: AsyncSession, scope: VerticalScope, tenant_id: uuid.UUID) -> dict:
        _require_scope_domain(scope, "providers")
        member_ids = await self._member_tenant_ids(db, scope)
        t = await db.get(Tenant, tenant_id)
        if not t:
            from app.exceptions import NotFoundException
            raise NotFoundException("Tenant", str(tenant_id))
        member_sub = member_ids.subquery()
        member_row = (await db.execute(select(member_sub.c.id).where(
            member_sub.c.id == tenant_id))).scalar_one_or_none()
        if member_row is None:
            from app.exceptions import ServiceOSException
            raise ServiceOSException("CROSS_VERTICAL_ACCESS_DENIED",
                                     f"Tenant is not a member of vertical '{scope.vertical_key}'.", status_code=403)
        enr = (await db.execute(select(TenantVerticalEnrollment).where(
            TenantVerticalEnrollment.tenant_id == tenant_id,
            TenantVerticalEnrollment.vertical_id == scope.vertical.id,
        ))).scalar_one_or_none()
        return {
            "tenant_id": str(t.id), "business_name": t.business_name or t.tenant_name,
            "registration_status": t.status, "verification_status": t.verification_status,
            "vertical_status": enr.status if enr else "legacy_primary_vertical",
            "admin_notes": enr.admin_notes if enr else None,
        }

    async def get_summary(self, db: AsyncSession, scope: VerticalScope) -> dict:
        _require_scope_domain(scope, "providers")
        member_ids = await self._member_tenant_ids(db, scope)
        sub = member_ids.subquery()
        total = await db.scalar(select(func.count()).select_from(sub))
        by_status = dict((await db.execute(
            select(Tenant.status, func.count()).where(Tenant.id.in_(select(sub.c.id))).group_by(Tenant.status)
        )).all())
        return {
            "total_providers": total,
            "pending_verification": by_status.get("onboarding_pending", 0),
            "active": by_status.get("active", 0),
            "suspended": by_status.get("suspended", 0),
        }


# ═══════════════════════════════════════════════════════════════════════════
# STAFF
# ═══════════════════════════════════════════════════════════════════════════

class VerticalStaffDirectoryService:
    """Staff directory + operational review actions for a Business Vertical.
    Every method requires a VerticalScope resolved server-side from the URL
    path (never a client-supplied vertical). Availability/workload are
    derived live from ServiceJob (the canonical Home-Services job table),
    never from a second, invented availability state machine."""

    async def _workload_subquery(self, db: AsyncSession):
        """Per-staff active/completed job counts + next scheduled job, from
        ServiceJob.assigned_staff_id -- the same canonical execution data
        the rest of the platform uses, not a parallel job system."""
        return select(
            ServiceJob.assigned_staff_id.label("staff_id"),
            func.count(ServiceJob.id).label("total_jobs"),
            func.count(ServiceJob.id).filter(ServiceJob.status == "completed").label("completed_jobs"),
            func.count(ServiceJob.id).filter(ServiceJob.status.in_(_ACTIVE_JOB_STATUSES)).label("active_jobs"),
            func.min(ServiceJob.scheduled_date).filter(
                ServiceJob.status.in_(_ACTIVE_JOB_STATUSES)).label("next_job_date"),
        ).where(ServiceJob.assigned_staff_id.isnot(None)).group_by(ServiceJob.assigned_staff_id)

    def _derive_availability(self, sbv: StaffBusinessVertical, active_jobs: int) -> str:
        # Assignment-level state always wins over live job load -- a
        # suspended/restricted assignment is never "available" no matter
        # what ServiceJob says.
        if sbv.assignment_status in ("suspended", "deactivated"):
            return "offline"
        if sbv.assignment_status == "restricted":
            return "unavailable"
        if not sbv.is_active:
            return "offline"
        if active_jobs > 0:
            return "on_job"
        return "available"

    async def list_staff(self, db: AsyncSession, scope: VerticalScope, *,
                         search: str | None = None, verification_status: str | None = None,
                         assignment_status: str | None = None, availability: str | None = None,
                         page: int = 1, page_size: int = 25) -> dict:
        _require_scope_domain(scope, "staff")
        conditions = [StaffBusinessVertical.vertical_id == scope.vertical.id]
        q = select(StaffBusinessVertical, ProviderTeamMember).join(
            ProviderTeamMember, StaffBusinessVertical.staff_id == ProviderTeamMember.id
        ).where(*conditions)
        if search:
            like = f"%{search}%"
            q = q.where(ProviderTeamMember.full_name.ilike(like) | ProviderTeamMember.email.ilike(like)
                        | ProviderTeamMember.phone.ilike(like))
        if verification_status:
            q = q.where(StaffBusinessVertical.verification_status == verification_status)
        if assignment_status:
            q = q.where(StaffBusinessVertical.assignment_status == assignment_status)

        total = await db.scalar(select(func.count()).select_from(q.subquery()))
        rows = (await db.execute(q.order_by(StaffBusinessVertical.created_at.desc())
                                 .offset((page - 1) * page_size).limit(page_size))).all()

        staff_ids = [sbv.staff_id for sbv, _ in rows]
        workload_by_staff: dict[uuid.UUID, Any] = {}
        if staff_ids:
            wl_sub = (await self._workload_subquery(db)).subquery()
            wl_rows = (await db.execute(select(wl_sub).where(wl_sub.c.staff_id.in_(staff_ids)))).all()
            workload_by_staff = {r.staff_id: r for r in wl_rows}

        items = []
        for sbv, ptm in rows:
            wl = workload_by_staff.get(sbv.staff_id)
            active_jobs = wl.active_jobs if wl else 0
            avail = self._derive_availability(sbv, active_jobs)
            if availability and avail != availability:
                continue
            items.append({
                "staff_id": str(sbv.staff_id), "full_name": ptm.full_name, "tenant_id": str(sbv.tenant_id),
                "designation": sbv.designation or ptm.designation, "is_active": sbv.is_active,
                "verification_status": sbv.verification_status, "assignment_status": sbv.assignment_status,
                "availability_status": avail,
                "active_jobs": active_jobs, "completed_jobs": wl.completed_jobs if wl else 0,
                "has_capabilities": bool(sbv.job_type_capabilities),
                "updated_at": sbv.updated_at.isoformat() if sbv.updated_at else None,
            })
        # availability filter is applied post-join (derived, not stored) --
        # total/pagination reflect the pre-filter set, consistent with how
        # every other derived-column filter in this codebase behaves when
        # the filter can't be pushed into SQL without duplicating the CASE.
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    async def get_staff(self, db: AsyncSession, scope: VerticalScope, staff_id: uuid.UUID) -> tuple[StaffBusinessVertical, ProviderTeamMember]:
        _require_scope_domain(scope, "staff")
        row = (await db.execute(select(StaffBusinessVertical, ProviderTeamMember).join(
            ProviderTeamMember, StaffBusinessVertical.staff_id == ProviderTeamMember.id
        ).where(StaffBusinessVertical.staff_id == staff_id,
                StaffBusinessVertical.vertical_id == scope.vertical.id))).first()
        if not row:
            raise ServiceOSException("CROSS_VERTICAL_ACCESS_DENIED",
                                     f"Staff member is not assigned to vertical '{scope.vertical_key}'.", status_code=403)
        return row

    async def get_staff_detail(self, db: AsyncSession, scope: VerticalScope, staff_id: uuid.UUID) -> dict:
        sbv, ptm = await self.get_staff(db, scope, staff_id)
        wl_sub = (await self._workload_subquery(db)).subquery()
        wl = (await db.execute(select(wl_sub).where(wl_sub.c.staff_id == staff_id))).first()
        active_jobs = wl.active_jobs if wl else 0
        return {
            **sbv.to_dict(), "full_name": ptm.full_name, "email": ptm.email, "phone": ptm.phone,
            "employee_code": getattr(ptm, "username", None), "joined_at": ptm.created_at.isoformat() if ptm.created_at else None,
            "availability_status": self._derive_availability(sbv, active_jobs),
            "active_jobs": active_jobs, "completed_jobs": wl.completed_jobs if wl else 0,
            "next_job_date": wl.next_job_date.isoformat() if wl and wl.next_job_date else None,
        }

    async def get_capabilities(self, db: AsyncSession, scope: VerticalScope, staff_id: uuid.UUID) -> dict:
        """Resolves through the Vertical -> Service Group -> Master Service
        -> Job Type catalog by looking up the exact JobTypeDefinition rows
        named in StaffBusinessVertical.job_type_capabilities -- never a
        broad category mapping."""
        from app.engines.admin_catalog.models import JobTypeDefinition, MasterService
        sbv, _ = await self.get_staff(db, scope, staff_id)
        job_type_ids = [uuid.UUID(x) for x in (sbv.job_type_capabilities or []) if x]
        job_types = []
        if job_type_ids:
            rows = (await db.execute(
                select(JobTypeDefinition, MasterService)
                .join(MasterService, JobTypeDefinition.master_service_id == MasterService.id, isouter=True)
                .where(JobTypeDefinition.id.in_(job_type_ids))
            )).all()
            job_types = [{
                "job_type_id": str(jt.id), "job_type_name": jt.name,
                "master_service_id": str(ms.id) if ms else None,
                "master_service_name": ms.name if ms else None,
            } for jt, ms in rows]
        return {"job_types": job_types, "service_capabilities": sbv.service_capabilities or []}

    async def get_workload(self, db: AsyncSession, scope: VerticalScope, staff_id: uuid.UUID) -> dict:
        await self.get_staff(db, scope, staff_id)  # ownership check
        jobs = (await db.execute(
            select(ServiceJob).where(ServiceJob.assigned_staff_id == staff_id)
            .order_by(ServiceJob.scheduled_date.asc().nulls_last()).limit(50)
        )).scalars().all()
        active = [j for j in jobs if j.status in _ACTIVE_JOB_STATUSES]
        return {
            "active_jobs": [{"job_id": str(j.id), "job_number": j.job_number, "status": j.status,
                             "scheduled_date": j.scheduled_date.isoformat() if j.scheduled_date else None} for j in active],
            "capacity_active": len(active),
        }

    async def get_performance(self, db: AsyncSession, scope: VerticalScope, staff_id: uuid.UUID) -> dict:
        await self.get_staff(db, scope, staff_id)  # ownership check
        jobs = (await db.execute(select(ServiceJob).where(ServiceJob.assigned_staff_id == staff_id))).scalars().all()
        completed = [j for j in jobs if j.status == "completed"]
        cancelled = [j for j in jobs if j.status == "cancelled"]
        total = len(jobs) or 1
        return {
            "completed_jobs": len(completed), "cancelled_jobs": len(cancelled),
            "completion_rate": round(len(completed) / total * 100, 1),
            "cancellation_rate": round(len(cancelled) / total * 100, 1),
            "scope": scope.vertical_key,
        }

    async def get_activity(self, db: AsyncSession, scope: VerticalScope, staff_id: uuid.UUID, limit: int = 50) -> dict:
        sbv, _ = await self.get_staff(db, scope, staff_id)
        rows = (await db.execute(
            select(VerticalAuditLog).where(
                VerticalAuditLog.vertical_id == scope.vertical.id,
                VerticalAuditLog.tenant_id == sbv.tenant_id,
                VerticalAuditLog.action_type.like("staff.%"),
            ).order_by(VerticalAuditLog.created_at.desc()).limit(limit)
        )).scalars().all()
        return {"items": [{
            "id": str(r.id), "action_type": r.action_type, "notes": r.notes,
            "before_state": r.before_state, "after_state": r.after_state,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        } for r in rows]}

    async def get_summary(self, db: AsyncSession, scope: VerticalScope) -> dict:
        _require_scope_domain(scope, "staff")
        base = select(StaffBusinessVertical).where(StaffBusinessVertical.vertical_id == scope.vertical.id)
        total = await db.scalar(select(func.count()).select_from(base.subquery()))
        active = await db.scalar(select(func.count(StaffBusinessVertical.id)).where(
            StaffBusinessVertical.vertical_id == scope.vertical.id, StaffBusinessVertical.assignment_status == "active"))
        pending_verification = await db.scalar(select(func.count(StaffBusinessVertical.id)).where(
            StaffBusinessVertical.vertical_id == scope.vertical.id,
            StaffBusinessVertical.verification_status.in_(("not_started", "in_review", "changes_requested"))))
        suspended = await db.scalar(select(func.count(StaffBusinessVertical.id)).where(
            StaffBusinessVertical.vertical_id == scope.vertical.id, StaffBusinessVertical.assignment_status == "suspended"))
        capability_incomplete = await db.scalar(select(func.count(StaffBusinessVertical.id)).where(
            StaffBusinessVertical.vertical_id == scope.vertical.id,
            (StaffBusinessVertical.job_type_capabilities.is_(None))))

        rows = (await db.execute(select(StaffBusinessVertical.staff_id, StaffBusinessVertical.assignment_status,
                                        StaffBusinessVertical.is_active)
                                 .where(StaffBusinessVertical.vertical_id == scope.vertical.id))).all()
        staff_ids = [r.staff_id for r in rows]
        active_count_by_staff: dict[uuid.UUID, int] = {}
        if staff_ids:
            wl_sub = (await self._workload_subquery(db)).subquery()
            wl_rows = (await db.execute(select(wl_sub).where(wl_sub.c.staff_id.in_(staff_ids)))).all()
            active_count_by_staff = {r.staff_id: r.active_jobs for r in wl_rows}
        available = assigned = unavailable = 0
        for r in rows:
            aj = active_count_by_staff.get(r.staff_id, 0)
            av = self._derive_availability(
                StaffBusinessVertical(assignment_status=r.assignment_status, is_active=r.is_active), aj)
            if av == "available": available += 1
            elif av == "on_job": assigned += 1
            else: unavailable += 1

        return {
            "total_staff": total, "active": active, "pending_verification": pending_verification,
            "available": available, "assigned": assigned, "unavailable": unavailable,
            "capability_incomplete": capability_incomplete, "suspended": suspended,
        }

    # ── Mutations (Super Admin review actions; never silent, always audited) ──

    async def _apply_transition(self, db: AsyncSession, scope: VerticalScope, staff_id: uuid.UUID, *,
                                action: str, field: str, new_value: str, reason: str,
                                allowed_from: tuple[str, ...] | None, actor) -> dict:
        sbv, ptm = await self.get_staff(db, scope, staff_id)
        current = getattr(sbv, field)
        if allowed_from is not None and current not in allowed_from:
            raise ServiceOSException(
                "INVALID_STATE_TRANSITION",
                f"Cannot {action}: current {field} is '{current}', expected one of {allowed_from}.",
                status_code=422,
            )
        before = {field: current}
        setattr(sbv, field, new_value)
        if field == "assignment_status" and new_value in ("suspended", "deactivated", "restricted"):
            sbv.is_active = False
        elif field == "assignment_status" and new_value == "active":
            sbv.is_active = True
        after = {field: new_value}
        await db.flush()
        await record_platform_audit(
            db, operation=f"staff.{action}", engine_id=_ENGINE_ID,
            entity_type="staff_business_vertical", entity_id=str(sbv.id), tenant_id=sbv.tenant_id,
            actor_id=uuid.UUID(actor.user_id) if getattr(actor, "user_id", None) else None,
            actor_role=getattr(actor, "role", None), request_id="—",
            before=before, after=after,
        )
        # Mirror into VerticalAuditLog too (vertical-scoped activity feed
        # read by get_activity above -- platform_audit_logs is the
        # system-of-record; this is the vertical-scoped projection of it).
        db.add(VerticalAuditLog(
            vertical_id=scope.vertical.id, tenant_id=sbv.tenant_id,
            actor_id=uuid.UUID(actor.user_id) if getattr(actor, "user_id", None) else None,
            action_type=f"staff.{action}", before_state=before, after_state=after, notes=reason,
        ))
        await db.commit()
        return {**sbv.to_dict(), "full_name": ptm.full_name}

    async def verify(self, db: AsyncSession, scope: VerticalScope, staff_id: uuid.UUID, *, reason: str, actor) -> dict:
        return await self._apply_transition(
            db, scope, staff_id, action="verify", field="verification_status", new_value="verified",
            reason=reason, allowed_from=("not_started", "in_review", "changes_requested"), actor=actor)

    async def reject(self, db: AsyncSession, scope: VerticalScope, staff_id: uuid.UUID, *, reason: str, actor) -> dict:
        return await self._apply_transition(
            db, scope, staff_id, action="reject", field="verification_status", new_value="rejected",
            reason=reason, allowed_from=("not_started", "in_review", "changes_requested"), actor=actor)

    async def request_changes(self, db: AsyncSession, scope: VerticalScope, staff_id: uuid.UUID, *, reason: str, actor) -> dict:
        if not reason or not reason.strip():
            raise ServiceOSException("VALIDATION_ERROR", "A reason is required to request changes.", status_code=422)
        return await self._apply_transition(
            db, scope, staff_id, action="request_changes", field="verification_status", new_value="changes_requested",
            reason=reason, allowed_from=None, actor=actor)

    async def restrict(self, db: AsyncSession, scope: VerticalScope, staff_id: uuid.UUID, *, reason: str, actor) -> dict:
        if not reason or not reason.strip():
            raise ServiceOSException("VALIDATION_ERROR", "A reason is required to restrict an assignment.", status_code=422)
        return await self._apply_transition(
            db, scope, staff_id, action="restrict", field="assignment_status", new_value="restricted",
            reason=reason, allowed_from=("pending", "active"), actor=actor)

    async def suspend(self, db: AsyncSession, scope: VerticalScope, staff_id: uuid.UUID, *, reason: str, actor) -> dict:
        if not reason or not reason.strip():
            raise ServiceOSException("VALIDATION_ERROR", "A reason is required to suspend an assignment.", status_code=422)
        return await self._apply_transition(
            db, scope, staff_id, action="suspend", field="assignment_status", new_value="suspended",
            reason=reason, allowed_from=("pending", "active", "restricted"), actor=actor)

    async def reactivate(self, db: AsyncSession, scope: VerticalScope, staff_id: uuid.UUID, *, reason: str, actor) -> dict:
        return await self._apply_transition(
            db, scope, staff_id, action="reactivate", field="assignment_status", new_value="active",
            reason=reason, allowed_from=("restricted", "suspended"), actor=actor)


# ═══════════════════════════════════════════════════════════════════════════
# CUSTOMERS
# ═══════════════════════════════════════════════════════════════════════════

class VerticalCustomerDirectoryService:

    async def list_customers(self, db: AsyncSession, scope: VerticalScope, *,
                             search: str | None = None, page: int = 1, page_size: int = 25) -> dict:
        _require_scope_domain(scope, "customers")
        q = select(CustomerBusinessVertical, User).join(
            User, CustomerBusinessVertical.customer_id == User.id
        ).where(CustomerBusinessVertical.vertical_id == scope.vertical.id)
        if search:
            q = q.where(User.full_name.ilike(f"%{search}%") | User.email.ilike(f"%{search}%"))

        total = await db.scalar(select(func.count()).select_from(q.subquery()))
        rows = (await db.execute(q.order_by(CustomerBusinessVertical.last_activity_at.desc())
                                 .offset((page - 1) * page_size).limit(page_size))).all()
        items = [{
            "customer_id": str(cbv.customer_id), "full_name": u.full_name, "email": u.email,
            "first_activity_at": cbv.first_activity_at.isoformat(), "last_activity_at": cbv.last_activity_at.isoformat(),
            "booking_count": cbv.booking_count, "relationship_status": cbv.relationship_status,
        } for cbv, u in rows]
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    async def get_customer(self, db: AsyncSession, scope: VerticalScope, customer_id: uuid.UUID) -> dict:
        _require_scope_domain(scope, "customers")
        row = (await db.execute(select(CustomerBusinessVertical, User).join(
            User, CustomerBusinessVertical.customer_id == User.id
        ).where(CustomerBusinessVertical.customer_id == customer_id,
                CustomerBusinessVertical.vertical_id == scope.vertical.id))).first()
        if not row:
            from app.exceptions import ServiceOSException
            raise ServiceOSException("CROSS_VERTICAL_ACCESS_DENIED",
                                     f"Customer has no recorded activity in vertical '{scope.vertical_key}'.", status_code=403)
        cbv, u = row
        # Complaints scoped to THIS vertical only -- never another vertical's.
        complaints = (await db.execute(select(func.count(CustomerComplaint.id)).where(
            CustomerComplaint.customer_id == customer_id, CustomerComplaint.vertical_id == scope.vertical.id,
        ))).scalar() or 0
        return {**cbv.to_dict(), "full_name": u.full_name, "email": u.email, "complaints_count": complaints}

    async def get_summary(self, db: AsyncSession, scope: VerticalScope) -> dict:
        _require_scope_domain(scope, "customers")
        total = await db.scalar(select(func.count(CustomerBusinessVertical.id)).where(
            CustomerBusinessVertical.vertical_id == scope.vertical.id))
        active = await db.scalar(select(func.count(CustomerBusinessVertical.id)).where(
            CustomerBusinessVertical.vertical_id == scope.vertical.id,
            CustomerBusinessVertical.relationship_status == "active"))
        return {"total_customers": total, "active_customers": active}


# ═══════════════════════════════════════════════════════════════════════════
# COMPLAINTS
# ═══════════════════════════════════════════════════════════════════════════

class VerticalComplaintWorkspaceService:
    """Central Home Services (and future-vertical) complaint work queue.
    Reuses the SAME canonical `app.engines.complaints` engine (state
    machine, SLA policy, evidence, messaging, resolution/settlement) --
    every mutation below is a thin, vertical-scope-checked wrapper around
    `ComplaintService`, never a second complaint engine."""

    def __init__(self):
        self._svc = ComplaintService()

    async def _scoped_complaint(self, db: AsyncSession, scope: VerticalScope, complaint_id: uuid.UUID) -> CustomerComplaint:
        _require_scope_domain(scope, "complaints")
        c = await db.get(CustomerComplaint, complaint_id)
        if not c or c.vertical_id != scope.vertical.id:
            from app.exceptions import ServiceOSException
            raise ServiceOSException("CROSS_VERTICAL_ACCESS_DENIED",
                                     f"Complaint does not belong to vertical '{scope.vertical_key}'.", status_code=403)
        return c

    async def list_complaints(self, db: AsyncSession, scope: VerticalScope, *,
                              search: str | None = None, status: str | None = None,
                              severity: str | None = None, complaint_type: str | None = None,
                              sla_status: str | None = None, assigned_admin_id: str | None = None,
                              page: int = 1, page_size: int = 25) -> dict:
        _require_scope_domain(scope, "complaints")
        conditions = [CustomerComplaint.vertical_id == scope.vertical.id]
        if status:
            conditions.append(CustomerComplaint.status == status)
        if severity:
            conditions.append(CustomerComplaint.severity == severity)
        if complaint_type:
            conditions.append(CustomerComplaint.complaint_type == complaint_type)
        if sla_status:
            conditions.append(CustomerComplaint.sla_status == sla_status)
        if assigned_admin_id:
            conditions.append(CustomerComplaint.assigned_admin_user_id == uuid.UUID(assigned_admin_id))
        if search:
            conditions.append(CustomerComplaint.complaint_number.ilike(f"%{search}%") |
                              CustomerComplaint.title.ilike(f"%{search}%"))

        total = await db.scalar(select(func.count(CustomerComplaint.id)).where(*conditions))
        rows = (await db.execute(select(CustomerComplaint).where(*conditions)
                                 .order_by(CustomerComplaint.created_at.desc())
                                 .offset((page - 1) * page_size).limit(page_size))).scalars().all()
        items = [{
            "id": str(c.id), "complaint_number": c.complaint_number, "status": c.status,
            "severity": c.severity, "sla_status": c.sla_status, "title": c.title,
            "complaint_type": c.complaint_type, "priority": c.priority,
            "customer_id": str(c.customer_id) if c.customer_id else None,
            "tenant_id": str(c.tenant_id) if c.tenant_id else None,
            "job_id": str(c.job_id) if c.job_id else None,
            "assigned_admin_user_id": str(c.assigned_admin_user_id) if c.assigned_admin_user_id else None,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        } for c in rows]
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    async def get_complaint(self, db: AsyncSession, scope: VerticalScope, complaint_id: uuid.UUID) -> dict:
        c = await self._scoped_complaint(db, scope, complaint_id)
        return c.to_dict()

    async def get_job_context(self, db: AsyncSession, scope: VerticalScope, complaint_id: uuid.UUID) -> dict:
        c = await self._scoped_complaint(db, scope, complaint_id)
        if not c.job_id:
            return {"job_linked": False}
        job = await db.get(ServiceJob, c.job_id)
        if not job:
            return {"job_linked": False, "job_id": str(c.job_id), "note": "Job reference unresolved"}
        return {
            "job_linked": True, "job_id": str(job.id), "job_number": job.job_number,
            "booking_id": str(job.booking_id), "category_id": str(job.category_id),
            "offering_id": str(job.offering_id), "job_type_id": str(job.job_type_id) if job.job_type_id else None,
            "assigned_staff_id": str(job.assigned_staff_id) if job.assigned_staff_id else None,
            "status": job.status, "scheduled_date": job.scheduled_date.isoformat() if job.scheduled_date else None,
            "completion_data": job.completion_data,
        }

    async def list_evidence(self, db: AsyncSession, scope: VerticalScope, complaint_id: uuid.UUID) -> dict:
        await self._scoped_complaint(db, scope, complaint_id)
        media = await self._svc.list_media(db, complaint_id, viewer="admin")
        return {"items": [m.to_dict() for m in media]}

    async def list_conversation(self, db: AsyncSession, scope: VerticalScope, complaint_id: uuid.UUID) -> dict:
        await self._scoped_complaint(db, scope, complaint_id)
        msgs = await self._svc.list_messages(db, complaint_id, viewer="admin")
        return {"items": [m.to_dict() for m in msgs]}

    async def list_timeline(self, db: AsyncSession, scope: VerticalScope, complaint_id: uuid.UUID) -> dict:
        await self._scoped_complaint(db, scope, complaint_id)
        events = await self._svc.list_events(db, complaint_id)
        return {"items": [e.to_dict() for e in events]}

    async def get_resolution(self, db: AsyncSession, scope: VerticalScope, complaint_id: uuid.UUID) -> dict:
        await self._scoped_complaint(db, scope, complaint_id)
        resolutions = await self._svc.list_resolutions(db, complaint_id)
        return {"items": [r.to_dict() for r in resolutions]}

    async def get_summary(self, db: AsyncSession, scope: VerticalScope) -> dict:
        _require_scope_domain(scope, "complaints")
        base_where = CustomerComplaint.vertical_id == scope.vertical.id
        by_status = dict((await db.execute(
            select(CustomerComplaint.status, func.count()).where(base_where).group_by(CustomerComplaint.status)
        )).all())
        breached = await db.scalar(select(func.count(CustomerComplaint.id)).where(
            base_where, CustomerComplaint.sla_status == "breached"))
        due_soon = await db.scalar(select(func.count(CustomerComplaint.id)).where(
            base_where, CustomerComplaint.sla_status == "at_risk"))
        unassigned = await db.scalar(select(func.count(CustomerComplaint.id)).where(
            base_where, CustomerComplaint.assigned_admin_user_id.is_(None),
            CustomerComplaint.status.notin_(("closed", "resolved", "rejected", "cancelled"))))
        open_count = sum(v for k, v in by_status.items() if k not in ("closed", "resolved", "rejected", "cancelled"))
        return {
            "open": open_count,
            "new": by_status.get("open", 0),
            "unassigned": unassigned or 0,
            "in_investigation": by_status.get("under_admin_review", 0),
            "waiting_on_customer": by_status.get("awaiting_customer_response", 0),
            "waiting_on_provider": by_status.get("awaiting_provider_response", 0),
            "waiting_on_technician": 0,  # no canonical technician-waiting state exists today -- not invented
            "escalated": by_status.get("resolution_proposed", 0),
            "sla_due_soon": due_soon or 0,
            "sla_breached": breached or 0,
            "resolved": by_status.get("resolved", 0),
            "reopened": 0,  # requires a dedicated reopen-count field/event query -- deferred, see report
        }

    # ── Mutations (Super Admin case handling; reuses ComplaintService,
    # never mutates CustomerComplaint columns directly) ─────────────────────

    async def assign(self, db: AsyncSession, scope: VerticalScope, complaint_id: uuid.UUID,
                     assignee_id: uuid.UUID, actor_id: uuid.UUID) -> dict:
        await self._scoped_complaint(db, scope, complaint_id)
        c = await self._svc.admin_assign_complaint(db, actor_id, complaint_id, assignee_id)
        return c.to_dict()

    async def request_provider_response(self, db: AsyncSession, scope: VerticalScope, complaint_id: uuid.UUID,
                                        actor_id: uuid.UUID) -> dict:
        await self._scoped_complaint(db, scope, complaint_id)
        c = await self._svc.admin_request_provider_response(db, actor_id, complaint_id)
        return c.to_dict()

    async def add_message(self, db: AsyncSession, scope: VerticalScope, complaint_id: uuid.UUID,
                          message_text: str, internal_only: bool, actor_id: uuid.UUID) -> dict:
        await self._scoped_complaint(db, scope, complaint_id)
        visibility = VIS_ADMIN_ONLY if internal_only else VIS_PUBLIC
        msg = await self._svc.admin_add_message(db, actor_id, complaint_id, message_text, visibility=visibility)
        return msg.to_dict()

    async def escalate(self, db: AsyncSession, scope: VerticalScope, complaint_id: uuid.UUID,
                       reason: str, actor_id: uuid.UUID) -> dict:
        c = await self._scoped_complaint(db, scope, complaint_id)
        if not reason or not reason.strip():
            from app.exceptions import ServiceOSException
            raise ServiceOSException("VALIDATION_ERROR", "A reason is required to escalate.", status_code=422)
        await self._svc._transition(db, c, STATUS_UNDER_ADMIN_REVIEW, ACTOR_ADMIN, actor_id, reason=reason)
        c.admin_escalation_at = datetime.now(timezone.utc)
        await db.commit()
        return c.to_dict()

    async def propose_resolution(self, db: AsyncSession, scope: VerticalScope, complaint_id: uuid.UUID, *,
                                 resolution_type: str, description: str,
                                 customer_visible_notes: str | None, internal_notes: str | None,
                                 actor_id: uuid.UUID) -> dict:
        await self._scoped_complaint(db, scope, complaint_id)
        r = await self._svc.admin_propose_resolution(
            db, actor_id, complaint_id, resolution_type, description,
            customer_visible_notes=customer_visible_notes, internal_notes=internal_notes)
        return r.to_dict()

    async def resolve(self, db: AsyncSession, scope: VerticalScope, complaint_id: uuid.UUID,
                      reason: str | None, actor_id: uuid.UUID) -> dict:
        await self._scoped_complaint(db, scope, complaint_id)
        c = await self._svc.admin_resolve_complaint(db, actor_id, complaint_id, reason=reason)
        return c.to_dict()

    async def close(self, db: AsyncSession, scope: VerticalScope, complaint_id: uuid.UUID,
                    reason: str | None, actor_id: uuid.UUID) -> dict:
        await self._scoped_complaint(db, scope, complaint_id)
        c = await self._svc.close_complaint(db, actor_id, ACTOR_ADMIN, complaint_id, reason=reason)
        return c.to_dict()

    async def reject(self, db: AsyncSession, scope: VerticalScope, complaint_id: uuid.UUID,
                     reason: str, actor_id: uuid.UUID) -> dict:
        await self._scoped_complaint(db, scope, complaint_id)
        c = await self._svc.admin_reject_complaint(db, actor_id, complaint_id, reason)
        return c.to_dict()

    async def reopen(self, db: AsyncSession, scope: VerticalScope, complaint_id: uuid.UUID,
                     reason: str, actor_id: uuid.UUID) -> dict:
        # "Resolved/Closed -> Reopened only with permission and reason":
        # deliberately NOT added to the shared ALLOWED_TRANSITIONS map (that
        # map is also used by the customer/provider-facing transition paths
        # -- adding a generic closed/resolved -> under_admin_review edge
        # there would let a customer's own resolution-reject path reopen an
        # already-closed complaint). This action is gated instead by the
        # dedicated `home_services:complaints:reopen` permission and a
        # mandatory reason, and writes the transition directly.
        c = await self._scoped_complaint(db, scope, complaint_id)
        if not reason or not reason.strip():
            from app.exceptions import ServiceOSException
            raise ServiceOSException("VALIDATION_ERROR", "A reason is required to reopen a complaint.", status_code=422)
        if c.status not in ("resolved", "closed"):
            from app.exceptions import ServiceOSException
            raise ServiceOSException("INVALID_STATE_TRANSITION",
                                     f"Cannot reopen: current status is '{c.status}', expected resolved or closed.",
                                     status_code=422)
        old_status = c.status
        c.status = STATUS_UNDER_ADMIN_REVIEW
        await db.flush()
        await self._svc._log_event(db, complaint_id, c.tenant_id, ACTOR_ADMIN, actor_id,
                                   "complaint_reopened", old_status, STATUS_UNDER_ADMIN_REVIEW, None, None,
                                   reason=reason)
        await db.commit()
        return c.to_dict()

    async def issue_customer_credit(self, db: AsyncSession, scope: VerticalScope, complaint_id: uuid.UUID, *,
                                    amount: str, reason: str, actor_id: uuid.UUID, actor_role: str,
                                    request_id: str) -> dict:
        """Customer Service Credit -- NEVER a cash refund. Writes through the
        canonical CustomerCreditService ledger (CustomerCreditLedger), not a
        direct balance write."""
        c = await self._scoped_complaint(db, scope, complaint_id)
        from app.engines.customer_credits.service import CustomerCreditService
        svc = CustomerCreditService(db, actor_id=actor_id, actor_role=actor_role, request_id=request_id)
        credit = await svc.issue_credit_manual(c.customer_id, {
            "amount": amount, "credit_type": "complaint_resolution",
            "issued_reason": reason, "customer_message": f"Service credit for complaint {c.complaint_number}",
        })
        db.add(ComplaintEvent(
            complaint_id=complaint_id, tenant_id=c.tenant_id, actor_type=ACTOR_ADMIN, actor_user_id=actor_id,
            event_type="customer_service_credit_issued", new_value={"credit_number": credit["credit_number"], "amount": amount},
            reason=reason, request_id=request_id,
        ))
        await db.commit()
        return credit

    async def apply_tenant_credit_adjustment(self, db: AsyncSession, scope: VerticalScope, complaint_id: uuid.UUID, *,
                                             direction: str, credit_units: str, reason_code: str,
                                             detailed_reason: str, actor_id: uuid.UUID) -> dict:
        """Reuses the canonical Home Services usage-credit ledger (same
        mechanism as Home Services Finance > Credits & Top-ups > Adjustments)
        -- never a direct balance write."""
        c = await self._scoped_complaint(db, scope, complaint_id)
        if not c.tenant_id:
            from app.exceptions import ServiceOSException
            raise ServiceOSException("VALIDATION_ERROR", "Complaint has no linked provider tenant.", status_code=422)
        from decimal import Decimal
        from app.engines.finance_hub.home_services_finance_service import HomeServicesFinanceService
        finance = HomeServicesFinanceService(db=db, actor_id=actor_id, actor_role=ACTOR_ADMIN)
        entry = await finance.create_manual_adjustment(
            tenant_id=c.tenant_id, direction=direction, credit_units=Decimal(str(credit_units)),
            reason_code=reason_code, detailed_reason=detailed_reason,
            supporting_reference=f"complaint:{c.complaint_number}",
        )
        db.add(ComplaintEvent(
            complaint_id=complaint_id, tenant_id=c.tenant_id, actor_type=ACTOR_ADMIN, actor_user_id=actor_id,
            event_type="tenant_credit_adjusted", new_value={"direction": direction, "credit_units": str(credit_units)},
            reason=detailed_reason,
        ))
        await db.commit()
        return entry
