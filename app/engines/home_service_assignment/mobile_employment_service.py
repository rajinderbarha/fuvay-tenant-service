"""Technician Mobile App Phase S — Employment Details.

Reuses `ProviderTeamMember` (employment identity), the real capability-
resolution SQL already proven in `team_directory_router.py::get_capabilities`
(tenant_services -> master_services -> service_groups/service_types), the
canonical `technician` role permission list in `app/core/permissions.py`, and
adds only the genuinely-missing pieces confirmed by audit: per-skill
verification (`StaffSkillRecord`) and a generic field-correction-request
workflow (`StaffCorrectionRequest`). Never a second staff/employment model.
"""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ServiceOSException
from app.engines.home_service_assignment.employment_correction_models import (
    StaffCorrectionRequest,
    CORRECTABLE_FIELDS, AUTO_APPLY_FIELDS,
    CORRECTION_STATUS_PENDING_REVIEW, CORRECTION_STATUS_APPROVED,
    CORRECTION_STATUS_CHANGES_REQUESTED, CORRECTION_STATUS_REJECTED,
    CORRECTION_STATUS_APPLIED, SKILL_STATUS_VERIFIED,
)

# Real values confirmed by audit (staff_model.py / service.py / team_directory_router.py):
# only "active"/"inactive" are ever written or compared -- "suspended"/"invited"/
# "pending" appear only in a stale docstring comment, never in code. Any other
# stored value is unmapped and must fail safe, not be assumed "active".
STATUS_ACTIVE = "active"
STATUS_INACTIVE = "inactive"
KNOWN_STATUSES = (STATUS_ACTIVE, STATUS_INACTIVE)

# Human-readable capability groups (spec section 9), derived from the real
# technician permission list in app/core/permissions.py -- not a second
# permission system. Permissions not present for the technician role are
# rendered as explicit "Restricted" entries below.
_CAPABILITY_LABELS = {
    "field_ops:jobs:read": ("jobs", "View assigned jobs"),
    "field_ops:jobs:update": ("jobs", "Update permitted workflow stages"),
    "field_ops:jobs:close": ("jobs", "Record direct-payment confirmation and close jobs"),
    "field_ops:photos:create": ("jobs", "Upload inspection evidence"),
    "field_ops:parts:add": ("jobs", "Add parts to jobs"),
    "field_ops:quotes:manage": ("jobs", "Create estimates, when permitted"),
    "booking:bookings:read": ("schedule", "View assigned schedule"),
    "chat:messages:read": ("customer_privacy", "View workflow-required customer messages"),
    "chat:messages:write": ("customer_privacy", "Use relay contact"),
    "review:read": ("customer_privacy", "View reviews on completed jobs"),
    "inventory:items:read": ("jobs", "View inventory for job parts"),
}
_RESTRICTED_LABELS = [
    "Cannot reassign jobs", "Cannot change pricing policy",
    "Cannot manage other staff", "Cannot alter catalog configuration",
    "No customer directory access",
]


def _tenant_correctable_current_value(field_key: str, staff, capabilities: dict) -> str | None:
    if field_key == "designation":
        return staff.designation
    if field_key == "reports_to":
        if staff.reports_to_display_name:
            return f"{staff.reports_to_display_name} · {staff.reports_to_designation or ''}".strip(" ·")
        return None
    if field_key == "joined_at":
        return staff.created_at.isoformat() if staff.created_at else None
    if field_key == "service_area":
        return capabilities.get("service_area_summary")
    return None


class MobileEmploymentService:
    async def _resolve_staff(self, db: AsyncSession, user_id: uuid.UUID, tenant_id: uuid.UUID):
        from app.engines.home_service_assignment.staff_model import ProviderTeamMember
        res = await db.execute(select(ProviderTeamMember).where(
            ProviderTeamMember.user_id == user_id, ProviderTeamMember.tenant_id == tenant_id,
        ))
        return res.scalars().first()

    async def _resolve_assignments(self, db: AsyncSession, tenant_id: uuid.UUID, staff) -> dict:
        offering_ids = staff.supported_offering_ids or []
        type_ids = set(staff.supported_type_ids or [])
        service_groups: dict[str, dict] = {}
        job_types: dict[str, dict] = {}

        if offering_ids:
            rows = (await db.execute(text(
                "SELECT ts.id::text AS offering_id, "
                "COALESCE(ts.tenant_display_name, ms.service_name) AS service_name, "
                "sg.id::text AS service_group_id, sg.name AS service_group_name "
                "FROM tenant_services ts "
                "JOIN master_services ms ON ms.id = ts.master_service_id "
                "LEFT JOIN service_groups sg ON sg.id = ms.service_group_id "
                "WHERE ts.tenant_id=:tid AND ts.id = ANY(:ids)"
            ), {"tid": str(tenant_id), "ids": offering_ids})).fetchall()

            for r in rows:
                if r.service_group_id:
                    service_groups[r.service_group_id] = {"id": r.service_group_id, "code": None, "name": r.service_group_name}

                if type_ids:
                    types = (await db.execute(text(
                        "SELECT tst.id::text AS id, st.id::text AS type_id, st.name AS name "
                        "FROM tenant_service_types tst JOIN service_types st ON st.id = tst.service_type_id "
                        "WHERE tst.tenant_service_id=:oid AND tst.is_enabled=true"
                    ), {"oid": r.offering_id})).fetchall()
                    for t in types:
                        if t.id in type_ids:
                            job_types[t.type_id] = {"id": t.type_id, "code": None, "name": t.name}

        return {
            "service_groups": list(service_groups.values()),
            "job_types": list(job_types.values()),
        }

    async def _skills(self, db: AsyncSession, tenant_id: uuid.UUID, staff_id: uuid.UUID) -> list[dict]:
        # Catalog assignments are canonical. Older free-text verification rows
        # remain visible when no matching catalog assignment exists, so staff
        # created before the catalog migration do not lose historical proof.
        rows = (await db.execute(text("""
            SELECT cs.id::text, cs.code, cs.name, cs.requires_verification,
                   COALESCE(ssr.verification_status, a.verification_status) AS verification_status,
                   ssr.verified_at, ssr.expires_at
              FROM provider_team_member_skills a
              JOIN category_skills cs ON cs.id=a.skill_id
              LEFT JOIN staff_skill_records ssr
                ON ssr.tenant_id=a.tenant_id AND ssr.staff_member_id=a.staff_member_id
               AND lower(ssr.skill_name)=lower(cs.name)
             WHERE a.tenant_id=:tid AND a.staff_member_id=:sid
            UNION ALL
            SELECT ssr.id::text, NULL AS code, ssr.skill_name AS name,
                   true AS requires_verification, ssr.verification_status,
                   ssr.verified_at, ssr.expires_at
              FROM staff_skill_records ssr
             WHERE ssr.tenant_id=:tid AND ssr.staff_member_id=:sid
               AND NOT EXISTS (
                   SELECT 1
                     FROM provider_team_member_skills a
                     JOIN category_skills cs ON cs.id=a.skill_id
                    WHERE a.tenant_id=ssr.tenant_id
                      AND a.staff_member_id=ssr.staff_member_id
                      AND lower(cs.name)=lower(ssr.skill_name)
               )
             ORDER BY name
        """), {"tid": str(tenant_id), "sid": str(staff_id)})).mappings().all()
        return [{
            "id": row["id"], "code": row["code"], "name": row["name"],
            "requires_verification": row["requires_verification"],
            "verification_status": row["verification_status"],
            "verified_at": row["verified_at"].isoformat() if row["verified_at"] else None,
            "expires_at": row["expires_at"].isoformat() if row["expires_at"] else None,
        } for row in rows]

    def _effective_permissions(self) -> dict:
        from app.core.permissions import ROLE_PERMISSIONS
        # No per-technician override table is wired to the "technician" role
        # today (confirmed by audit -- StaffPermission overrides only apply
        # when user.role == "staff"). Effective permissions for a technician
        # are therefore the role default list, disclosed as such rather than
        # fabricating a deny-precedence calculation that doesn't run.
        granted = list(ROLE_PERMISSIONS.get("technician", []))
        groups: dict[str, list[str]] = {"jobs": [], "schedule": [], "customer_privacy": []}
        for code in granted:
            mapping = _CAPABILITY_LABELS.get(code)
            if mapping:
                group, label = mapping
                if label not in groups[group]:
                    groups[group].append(label)
        # Real Phase P features not gated by a distinct permission code, but
        # genuinely available to every technician account.
        groups["schedule"].append("Request time off")
        return {
            "capability_count": len(granted),
            "groups": [
                {"key": "jobs", "label": "Jobs", "items": groups["jobs"]},
                {"key": "schedule", "label": "Schedule", "items": groups["schedule"]},
                {"key": "customer_privacy", "label": "Customer privacy", "items": groups["customer_privacy"]},
                {"key": "restricted", "label": "Restricted", "items": _RESTRICTED_LABELS},
            ],
        }

    async def get_employment_details(self, db: AsyncSession, user_id: uuid.UUID, tenant_id: uuid.UUID) -> dict:
        from app.engines.tenant_engine.models import Tenant
        from app.engines.vertical_catalog.models import Vertical, TenantVerticalEnrollment

        tenant = await db.get(Tenant, tenant_id)
        staff = await self._resolve_staff(db, user_id, tenant_id)

        vertical_row = (await db.execute(
            select(Vertical.key, Vertical.label)
            .join(TenantVerticalEnrollment, TenantVerticalEnrollment.vertical_id == Vertical.id)
            .where(TenantVerticalEnrollment.tenant_id == tenant_id)
        )).first()

        if not staff:
            return {
                "business": {
                    "tenant_id": str(tenant_id),
                    "name": tenant.business_name if tenant else None,
                    "logo_url": getattr(tenant, "logo_url", None) if tenant else None,
                    "vertical_code": vertical_row.key if vertical_row else None,
                    "vertical_label": vertical_row.label if vertical_row else None,
                },
                "employment": None,
                "status_known": False,
                "assignments": {"service_groups": [], "job_types": [], "verified_skills": []},
                "scope": None,
                "permissions": None,
                "allowed_actions": {"request_correction": False},
            }

        status_known = staff.status in KNOWN_STATUSES
        is_active = staff.status == STATUS_ACTIVE

        assignments = await self._resolve_assignments(db, tenant_id, staff)
        skills = await self._skills(db, tenant_id, staff.id)

        working_hours_row = (await db.execute(text(
            "SELECT day_of_week, start_time, end_time FROM provider_availability_rules "
            "WHERE tenant_id=:tid AND scope_type='staff_member' AND scope_id=:sid AND is_active=true "
            "ORDER BY day_of_week LIMIT 1"
        ), {"tid": str(tenant_id), "sid": str(staff.id)})).first()
        working_schedule_summary = None
        if working_hours_row:
            working_schedule_summary = f"Mon–Sat · {working_hours_row.start_time}–{working_hours_row.end_time}"

        service_area_summary = None
        if staff.service_area_ids:
            service_area_summary = f"{len(staff.service_area_ids)} service area(s) assigned"

        capabilities = {"service_area_summary": service_area_summary}
        permissions = self._effective_permissions()

        response = {
            "business": {
                "tenant_id": str(tenant_id),
                "name": tenant.business_name if tenant else None,
                "logo_url": getattr(tenant, "logo_url", None) if tenant else None,
                "vertical_code": vertical_row.key if vertical_row else None,
                "vertical_label": vertical_row.label if vertical_row else None,
            },
            "employment": {
                "staff_id": str(staff.id),
                "staff_reference": str(staff.id)[:8].upper(),
                "staff_type": staff.member_type,
                "designation": staff.designation,
                "status": staff.status if status_known else "unknown",
                "status_known": status_known,
                "joined_at": staff.created_at.isoformat() if staff.created_at else None,
                "reports_to": (
                    {"display_name": staff.reports_to_display_name, "designation": staff.reports_to_designation}
                    if staff.reports_to_display_name else None
                ),
            },
            "status_known": status_known,
            "assignments": {
                "service_groups": assignments["service_groups"] if is_active else [],
                "job_types": assignments["job_types"] if is_active else [],
                "verified_skills": skills if is_active else [],
            },
            "scope": {
                "service_area_summary": service_area_summary,
                "working_schedule_summary": working_schedule_summary,
                "effective_capability_count": permissions["capability_count"],
            } if is_active else None,
            "permissions": permissions if is_active else None,
            "allowed_actions": {"request_correction": status_known},
        }
        return response

    async def get_permissions_summary(self, db: AsyncSession, user_id: uuid.UUID, tenant_id: uuid.UUID) -> dict:
        staff = await self._resolve_staff(db, user_id, tenant_id)
        if not staff or staff.status != STATUS_ACTIVE:
            raise ServiceOSException("PERMISSIONS_UNAVAILABLE", "Permissions summary is unavailable for your current employment status.", status_code=409)
        return self._effective_permissions()

    # ── Correction requests ────────────────────────────────────────────────

    async def submit_correction(self, db: AsyncSession, user_id: uuid.UUID, tenant_id: uuid.UUID, *,
                                 field_key: str, requested_value: str, reason: str) -> dict:
        if field_key not in CORRECTABLE_FIELDS:
            raise ServiceOSException("INVALID_FIELD", f"'{field_key}' cannot be corrected from this app.", status_code=400)
        staff = await self._resolve_staff(db, user_id, tenant_id)
        if not staff:
            raise ServiceOSException("NOT_FOUND", "Employment record not found.", status_code=404)

        existing = (await db.execute(select(StaffCorrectionRequest).where(
            StaffCorrectionRequest.tenant_id == tenant_id,
            StaffCorrectionRequest.staff_member_id == staff.id,
            StaffCorrectionRequest.field_key == field_key,
            StaffCorrectionRequest.status == CORRECTION_STATUS_PENDING_REVIEW,
        ))).scalars().first()
        if existing:
            raise ServiceOSException("DUPLICATE_PENDING_REQUEST", "You already have a pending correction request for this field.", status_code=409)

        assignments = await self._resolve_assignments(db, tenant_id, staff)
        capabilities = {"service_area_summary": (f"{len(staff.service_area_ids)} service area(s) assigned" if staff.service_area_ids else None)}
        current_value = _tenant_correctable_current_value(field_key, staff, capabilities)

        req = StaffCorrectionRequest(
            tenant_id=tenant_id, staff_member_id=staff.id, requested_by_user_id=user_id,
            field_key=field_key, current_value=current_value, requested_value=requested_value.strip(),
            reason=reason.strip(),
        )
        db.add(req)
        await db.commit()
        await db.refresh(req)
        return req.to_dict()

    async def list_my_corrections(self, db: AsyncSession, user_id: uuid.UUID, tenant_id: uuid.UUID) -> list[dict]:
        staff = await self._resolve_staff(db, user_id, tenant_id)
        if not staff:
            return []
        res = await db.execute(select(StaffCorrectionRequest).where(
            StaffCorrectionRequest.tenant_id == tenant_id, StaffCorrectionRequest.staff_member_id == staff.id,
        ).order_by(StaffCorrectionRequest.created_at.desc()))
        return [r.to_dict() for r in res.scalars().all()]

    async def decide_correction(self, db: AsyncSession, tenant_id: uuid.UUID, request_id: uuid.UUID, *,
                                 decision: str, reviewer_user_id: uuid.UUID, reviewer_note: str | None) -> dict:
        from app.engines.home_service_assignment.staff_model import ProviderTeamMember

        req = (await db.execute(select(StaffCorrectionRequest).where(
            StaffCorrectionRequest.id == request_id, StaffCorrectionRequest.tenant_id == tenant_id,
        ))).scalars().first()
        if not req:
            raise ServiceOSException("NOT_FOUND", "Correction request not found.", status_code=404)
        if req.status != CORRECTION_STATUS_PENDING_REVIEW:
            raise ServiceOSException("INVALID_STATE", "This request has already been decided.", status_code=409)
        if req.requested_by_user_id == reviewer_user_id:
            raise ServiceOSException("SELF_REVIEW_FORBIDDEN", "You cannot review your own correction request.", status_code=403)

        decision_map = {
            "approve": CORRECTION_STATUS_APPROVED,
            "reject": CORRECTION_STATUS_REJECTED,
            "request_changes": CORRECTION_STATUS_CHANGES_REQUESTED,
        }
        if decision not in decision_map:
            raise ServiceOSException("INVALID_DECISION", "Unknown decision.", status_code=400)
        if decision == "reject" and not (reviewer_note or "").strip():
            raise ServiceOSException("REASON_REQUIRED", "A reason is required to reject a correction request.", status_code=400)

        req.status = decision_map[decision]
        req.reviewer_note = reviewer_note
        req.reviewed_by_user_id = reviewer_user_id
        req.reviewed_at = dt.datetime.now(dt.timezone.utc)

        if decision == "approve" and req.field_key in AUTO_APPLY_FIELDS:
            staff = await db.get(ProviderTeamMember, req.staff_member_id)
            if staff:
                if req.field_key == "designation":
                    staff.designation = req.requested_value
                elif req.field_key == "reports_to":
                    name, _, designation = req.requested_value.partition("·")
                    staff.reports_to_display_name = name.strip() or None
                    staff.reports_to_designation = designation.strip() or None
                req.status = CORRECTION_STATUS_APPLIED
                req.applied_at = dt.datetime.now(dt.timezone.utc)

        await db.commit()
        await db.refresh(req)

        await self._notify_decision(db, req, decision)
        return req.to_dict()

    async def _notify_decision(self, db: AsyncSession, req: StaffCorrectionRequest, decision: str) -> None:
        from app.engines.platform_notifications.notification_service import NotificationService
        from app.engines.platform_notifications.constants import (
            EVT_CORRECTION_APPROVED, EVT_CORRECTION_CHANGES_REQUESTED, EVT_CORRECTION_REJECTED,
        )
        event_key = {
            "approve": EVT_CORRECTION_APPROVED,
            "reject": EVT_CORRECTION_REJECTED,
            "request_changes": EVT_CORRECTION_CHANGES_REQUESTED,
        }[decision]
        await NotificationService().fire_event(
            db, event_key, {"field_key": req.field_key}, tenant_id=req.tenant_id,
            actor_user_id=req.reviewed_by_user_id,
            source_record_type="staff_correction_request", source_record_id=req.id,
            recipients=[{"user_id": str(req.requested_by_user_id), "recipient_type": "staff"}],
        )
