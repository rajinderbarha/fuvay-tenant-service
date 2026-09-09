"""VERTICAL-DIRECTORY-FRAMEWORK: one directory service per domain
(Providers/Staff/Customers/Complaints), every method requiring a
VerticalScope. Scoping is applied BEFORE search/filter/pagination/
aggregation -- never after, and never derived from a client-supplied
vertical id.
"""
from __future__ import annotations

import uuid
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
from app.engines.complaints.models import CustomerComplaint
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

    async def _member_tenant_ids(self, db: AsyncSession, scope: VerticalScope) -> Any:
        """Return tenants that genuinely belong to this vertical.

        Team members do not need a second copied vertical row to become
        visible. Their tenant membership is the authoritative vertical
        boundary, matching the provider directory and provider 360 team tab.
        """
        enrolled = select(TenantVerticalEnrollment.tenant_id.label("id")).where(
            TenantVerticalEnrollment.vertical_id == scope.vertical.id)
        legacy = select(Tenant.id.label("id")).where(
            Tenant.vertical == scope.vertical_key,
            Tenant.id.notin_(select(TenantVerticalEnrollment.tenant_id)),
        )
        return enrolled.union(legacy)

    async def _team_query(self, db: AsyncSession, scope: VerticalScope):
        member_tenants = await self._member_tenant_ids(db, scope)
        return (
            select(ProviderTeamMember, StaffBusinessVertical, Tenant, User)
            .join(Tenant, Tenant.id == ProviderTeamMember.tenant_id)
            .outerjoin(
                StaffBusinessVertical,
                and_(
                    StaffBusinessVertical.staff_id == ProviderTeamMember.id,
                    StaffBusinessVertical.vertical_id == scope.vertical.id,
                ),
            )
            .outerjoin(User, User.id == ProviderTeamMember.user_id)
            .where(
                ProviderTeamMember.tenant_id.in_(member_tenants),
                ProviderTeamMember.deleted_at.is_(None),
            )
        )

    @staticmethod
    def _effective_verification(
        sbv: StaffBusinessVertical | None, ptm: ProviderTeamMember, user: User | None,
    ) -> str:
        if sbv:
            return sbv.verification_status
        if not ptm.user_id:
            return "not_started"
        return "verified" if user and user.is_active else "access_disabled"

    @staticmethod
    def _effective_assignment(sbv: StaffBusinessVertical | None, ptm: ProviderTeamMember) -> str:
        return sbv.assignment_status if sbv else ptm.status

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

    async def _workloads_for_members(
        self, db: AsyncSession, members: list[ProviderTeamMember],
    ) -> dict[uuid.UUID, dict[str, Any]]:
        """Aggregate jobs assigned using either historical staff id space.

        Service jobs have used both ``provider_team_members.id`` and the
        linked ``users.id`` over time. Counting only one hides real work.
        """
        assignment_owner: dict[uuid.UUID, uuid.UUID] = {}
        for member in members:
            assignment_owner[member.id] = member.id
            if member.user_id:
                assignment_owner[member.user_id] = member.id
        if not assignment_owner:
            return {}
        wl_sub = (await self._workload_subquery(db)).subquery()
        rows = (await db.execute(
            select(wl_sub).where(wl_sub.c.staff_id.in_(list(assignment_owner)))
        )).all()
        result: dict[uuid.UUID, dict[str, Any]] = {}
        for row in rows:
            owner = assignment_owner.get(row.staff_id)
            if not owner:
                continue
            current = result.setdefault(owner, {
                "total_jobs": 0, "completed_jobs": 0, "active_jobs": 0, "next_job_date": None,
            })
            current["total_jobs"] += int(row.total_jobs or 0)
            current["completed_jobs"] += int(row.completed_jobs or 0)
            current["active_jobs"] += int(row.active_jobs or 0)
            if row.next_job_date and (
                current["next_job_date"] is None or row.next_job_date < current["next_job_date"]
            ):
                current["next_job_date"] = row.next_job_date
        return result

    def _derive_availability(
        self, ptm: ProviderTeamMember, sbv: StaffBusinessVertical | None, active_jobs: int,
    ) -> str:
        # Assignment-level state always wins over live job load -- a
        # suspended/restricted assignment is never "available" no matter
        # what ServiceJob says.
        assignment_status = self._effective_assignment(sbv, ptm)
        if assignment_status in ("suspended", "deactivated", "inactive"):
            return "offline"
        if assignment_status == "restricted" or not ptm.can_receive_assignment:
            return "unavailable"
        if sbv and not sbv.is_active:
            return "offline"
        if active_jobs > 0:
            return "on_job"
        return ptm.availability_state or "available"

    async def list_staff(self, db: AsyncSession, scope: VerticalScope, *,
                         search: str | None = None, verification_status: str | None = None,
                         assignment_status: str | None = None, availability: str | None = None,
                         member_type: str | None = None,
                         page: int = 1, page_size: int = 25) -> dict:
        _require_scope_domain(scope, "staff")
        q = await self._team_query(db, scope)
        if search:
            like = f"%{search}%"
            q = q.where(ProviderTeamMember.full_name.ilike(like) | ProviderTeamMember.email.ilike(like)
                        | ProviderTeamMember.phone.ilike(like) | Tenant.business_name.ilike(like))
        if member_type:
            q = q.where(func.lower(ProviderTeamMember.member_type) == member_type.lower())
        if verification_status:
            effective_verification = case(
                (StaffBusinessVertical.id.isnot(None), StaffBusinessVertical.verification_status),
                (ProviderTeamMember.user_id.is_(None), "not_started"),
                (User.is_active.is_(True), "verified"),
                else_="access_disabled",
            )
            q = q.where(effective_verification == verification_status)
        if assignment_status:
            q = q.where(func.coalesce(
                StaffBusinessVertical.assignment_status, ProviderTeamMember.status,
            ) == assignment_status)

        total = await db.scalar(select(func.count()).select_from(q.subquery()))
        rows = (await db.execute(q.order_by(ProviderTeamMember.created_at.desc())
                                 .offset((page - 1) * page_size).limit(page_size))).all()

        workload_by_staff = await self._workloads_for_members(db, [ptm for ptm, _, _, _ in rows])

        items = []
        for ptm, sbv, tenant, user in rows:
            wl = workload_by_staff.get(ptm.id, {})
            active_jobs = int(wl.get("active_jobs", 0))
            avail = self._derive_availability(ptm, sbv, active_jobs)
            if availability and avail != availability:
                continue
            items.append({
                "staff_id": str(ptm.id), "full_name": ptm.full_name, "tenant_id": str(ptm.tenant_id),
                "provider_name": tenant.business_name or tenant.tenant_name,
                "member_type": ptm.member_type, "designation": ptm.designation,
                "is_active": (sbv.is_active if sbv else ptm.status == "active"),
                "verification_status": self._effective_verification(sbv, ptm, user),
                "assignment_status": self._effective_assignment(sbv, ptm),
                "login_status": ("not_created" if not ptm.user_id else "enabled" if user and user.is_active else "disabled"),
                "availability_status": avail,
                "active_jobs": active_jobs, "completed_jobs": int(wl.get("completed_jobs", 0)),
                "has_capabilities": bool(
                    ptm.supported_offering_ids or ptm.supported_type_ids or ptm.supported_brand_ids
                    or (sbv and (sbv.job_type_capabilities or sbv.service_capabilities))
                ),
                "updated_at": ptm.updated_at.isoformat() if ptm.updated_at else None,
            })
        # availability filter is applied post-join (derived, not stored) --
        # total/pagination reflect the pre-filter set, consistent with how
        # every other derived-column filter in this codebase behaves when
        # the filter can't be pushed into SQL without duplicating the CASE.
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    async def get_staff(
        self, db: AsyncSession, scope: VerticalScope, staff_id: uuid.UUID,
    ) -> tuple[StaffBusinessVertical | None, ProviderTeamMember, Tenant, User | None]:
        _require_scope_domain(scope, "staff")
        q = await self._team_query(db, scope)
        row = (await db.execute(q.where(ProviderTeamMember.id == staff_id))).first()
        if not row:
            raise ServiceOSException("CROSS_VERTICAL_ACCESS_DENIED",
                                     f"Staff member is not assigned to vertical '{scope.vertical_key}'.", status_code=403)
        ptm, sbv, tenant, user = row
        return sbv, ptm, tenant, user

    async def get_staff_detail(self, db: AsyncSession, scope: VerticalScope, staff_id: uuid.UUID) -> dict:
        sbv, ptm, tenant, user = await self.get_staff(db, scope, staff_id)
        wl = (await self._workloads_for_members(db, [ptm])).get(ptm.id, {})
        active_jobs = int(wl.get("active_jobs", 0))
        return {
            "id": str(sbv.id) if sbv else None, "staff_id": str(ptm.id), "tenant_id": str(ptm.tenant_id),
            "vertical_id": str(scope.vertical.id), "full_name": ptm.full_name,
            "provider_name": tenant.business_name or tenant.tenant_name,
            "member_type": ptm.member_type, "designation": ptm.designation,
            "email": ptm.email, "phone": ptm.phone, "employee_code": ptm.username,
            "joined_at": ptm.created_at.isoformat() if ptm.created_at else None,
            "verification_status": self._effective_verification(sbv, ptm, user),
            "assignment_status": self._effective_assignment(sbv, ptm),
            "login_status": "not_created" if not ptm.user_id else "enabled" if user and user.is_active else "disabled",
            "availability_status": self._derive_availability(ptm, sbv, active_jobs),
            "active_jobs": active_jobs, "completed_jobs": int(wl.get("completed_jobs", 0)),
            "next_job_date": wl["next_job_date"].isoformat() if wl.get("next_job_date") else None,
        }

    async def get_capabilities(self, db: AsyncSession, scope: VerticalScope, staff_id: uuid.UUID) -> dict:
        """Resolves through the Vertical -> Service Group -> Master Service
        -> Job Type catalog by looking up the exact JobTypeDefinition rows
        named in StaffBusinessVertical.job_type_capabilities -- never a
        broad category mapping."""
        from app.engines.admin_catalog.models import JobTypeDefinition, MasterService
        sbv, ptm, _, _ = await self.get_staff(db, scope, staff_id)
        job_type_ids = [uuid.UUID(x) for x in ((sbv.job_type_capabilities if sbv else []) or []) if x]
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
        return {
            "job_types": job_types,
            "service_capabilities": (sbv.service_capabilities if sbv else None) or ptm.supported_offering_ids or [],
            "supported_type_ids": ptm.supported_type_ids or [],
            "supported_brand_ids": ptm.supported_brand_ids or [],
        }

    async def get_workload(self, db: AsyncSession, scope: VerticalScope, staff_id: uuid.UUID) -> dict:
        _, ptm, _, _ = await self.get_staff(db, scope, staff_id)  # ownership check
        assignment_ids = [ptm.id] + ([ptm.user_id] if ptm.user_id else [])
        jobs = (await db.execute(
            select(ServiceJob).where(ServiceJob.assigned_staff_id.in_(assignment_ids))
            .order_by(ServiceJob.scheduled_date.asc().nulls_last()).limit(50)
        )).scalars().all()
        active = [j for j in jobs if j.status in _ACTIVE_JOB_STATUSES]
        return {
            "active_jobs": [{"job_id": str(j.id), "job_number": j.job_number, "status": j.status,
                             "scheduled_date": j.scheduled_date.isoformat() if j.scheduled_date else None} for j in active],
            "capacity_active": len(active),
        }

    async def get_performance(self, db: AsyncSession, scope: VerticalScope, staff_id: uuid.UUID) -> dict:
        _, ptm, _, _ = await self.get_staff(db, scope, staff_id)  # ownership check
        assignment_ids = [ptm.id] + ([ptm.user_id] if ptm.user_id else [])
        jobs = (await db.execute(select(ServiceJob).where(
            ServiceJob.assigned_staff_id.in_(assignment_ids)
        ))).scalars().all()
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
        _, ptm, _, _ = await self.get_staff(db, scope, staff_id)
        rows = (await db.execute(
            select(VerticalAuditLog).where(
                VerticalAuditLog.vertical_id == scope.vertical.id,
                VerticalAuditLog.tenant_id == ptm.tenant_id,
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
        rows = (await db.execute(await self._team_query(db, scope))).all()
        workloads = await self._workloads_for_members(db, [ptm for ptm, _, _, _ in rows])
        total = len(rows)
        active = pending_verification = suspended = capability_incomplete = 0
        technicians = staff_members = available = assigned = unavailable = 0
        for ptm, sbv, _, user in rows:
            assignment = self._effective_assignment(sbv, ptm)
            verification = self._effective_verification(sbv, ptm, user)
            active += int(assignment == "active")
            pending_verification += int(verification in ("not_started", "in_review", "changes_requested"))
            suspended += int(assignment in ("suspended", "deactivated", "inactive"))
            technicians += int(ptm.member_type == "technician")
            staff_members += int(ptm.member_type != "technician")
            capability_incomplete += int(ptm.member_type == "technician" and not ptm.supported_offering_ids)
            aj = int(workloads.get(ptm.id, {}).get("active_jobs", 0))
            av = self._derive_availability(ptm, sbv, aj)
            if av == "available": available += 1
            elif av == "on_job": assigned += 1
            else: unavailable += 1

        return {
            "total_staff": total, "active": active, "pending_verification": pending_verification,
            "available": available, "assigned": assigned, "unavailable": unavailable,
            "capability_incomplete": capability_incomplete, "suspended": suspended,
            "technicians": technicians, "staff_members": staff_members,
        }

    # ── Mutations (Super Admin review actions; never silent, always audited) ──

    async def _apply_transition(self, db: AsyncSession, scope: VerticalScope, staff_id: uuid.UUID, *,
                                action: str, field: str, new_value: str, reason: str,
                                allowed_from: tuple[str, ...] | None, actor) -> dict:
        sbv, ptm, _, _ = await self.get_staff(db, scope, staff_id)
        if sbv is None:
            # The provider roster is canonical.  The vertical assignment row
            # is an optional admin-review overlay and is created lazily only
            # when an administrator actually records a review decision.
            sbv = StaffBusinessVertical(
                staff_id=ptm.id,
                tenant_id=ptm.tenant_id,
                vertical_id=scope.vertical.id,
                designation=ptm.designation,
                service_capabilities=ptm.supported_offering_ids or [],
                is_active=ptm.status == "active",
                verification_status="verified" if ptm.user_id else "not_started",
                assignment_status=ptm.status,
                availability_status=ptm.availability_state or "available",
            )
            db.add(sbv)
            await db.flush()
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
            # Enforcement must affect the roster read by matching/dispatch,
            # not only an admin-only overlay table.
            ptm.status = "inactive"
            ptm.can_receive_assignment = False
        elif field == "assignment_status" and new_value == "active":
            sbv.is_active = True
            ptm.status = "active"
            ptm.can_receive_assignment = True
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
# End of active provider, staff, and customer directory services.
# ═══════════════════════════════════════════════════════════════════════════
