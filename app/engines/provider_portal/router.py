"""Provider Portal Router — Sprint 11/12 provider-facing endpoints.

Covers team-members, availability, offerings, status, onboarding/status,
and packages/status. All data is tenant-scoped via JWT.
"""
from __future__ import annotations

import hashlib
import json
import secrets
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select, update, delete, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.engines.vertical_catalog.pricing_readiness import PUBLISHED_PRICED_SERVICES_SQL

from app.dependencies.auth import get_current_user, UserContext
from app.dependencies.db import get_db
from app.schemas.base import ok
from app.exceptions import ServiceOSException
from app.core.permissions import P, require_tenant_mutation_permission, require_tenant_owner_mutation
from app.core.audit import record_platform_audit
from app.config import get_settings
from app.models.base import utcnow
from app.engines.admin_catalog.skill_catalog_router import (
    member_skill_ids, replace_member_skills, resolve_team_category_id,
    validate_skill_ids,
)

from app.dependencies.setup_sequence import enforce_setup_sequence

router = APIRouter(prefix="/v1/provider", tags=["Provider Portal"])

# Mirrors the provider_team_members.max_concurrent_jobs DB default (NOT NULL
# DEFAULT 4). Kept as a named constant so the fallback is explicit at the one
# call site that needs it instead of a bare magic number.
DEFAULT_MAX_CONCURRENT_JOBS = 4
VALID_MEMBER_TYPES = {"technician", "staff", "manager"}
DESIGNATIONS_BY_MEMBER_TYPE = {
    "technician": {
        "Technician", "Junior Technician", "Senior Technician", "Lead Technician",
        "AC Technician", "Installation Specialist", "Maintenance Specialist", "Field Supervisor",
    },
    "staff": {
        "Operations Coordinator", "Dispatcher", "Customer Support Executive", "Back Office Executive",
    },
    "manager": {
        "Team Manager", "Operations Manager", "Service Manager", "Branch Manager",
    },
}
settings = get_settings()


def _validate_designation(member_type: str, value: Any) -> str | None:
    designation = str(value or "").strip()
    if not designation:
        return None  # Role and assignment are authoritative; designation is optional legacy data.
    if designation not in DESIGNATIONS_BY_MEMBER_TYPE.get(member_type, set()):
        raise ServiceOSException(
            "INVALID_TEAM_DESIGNATION",
            "The selected designation is not available for this team-member role.",
            status_code=422,
        )
    return designation


def _validate_availability_time_range(start_time: str | None, end_time: str | None) -> None:
    """HS5 fix — end_time must be after start_time. Previously unvalidated,
    an availability rule could be created/updated with end before start."""
    if not start_time or not end_time:
        return
    if end_time <= start_time:
        raise ServiceOSException(
            "INVALID_AVAILABILITY_TIME_RANGE",
            "End time must be after start time.",
            status_code=422)


def _validate_break_time(start_time: str | None, end_time: str | None,
                          break_start: str | None, break_end: str | None) -> None:
    """HS5B — break_start_time/break_end_time must both be present or both
    null, break must fall inside the working start/end window, and
    break_end must be after break_start."""
    if break_start is None and break_end is None:
        return
    if (break_start is None) != (break_end is None):
        raise ServiceOSException(
            "INVALID_BREAK_TIME_RANGE",
            "Break start and break end must both be set, or both left empty.",
            status_code=422)
    if break_end <= break_start:
        raise ServiceOSException(
            "INVALID_BREAK_TIME_RANGE",
            "Break end time must be after break start time.",
            status_code=422)
    if start_time and end_time and not (start_time <= break_start and break_end <= end_time):
        raise ServiceOSException(
            "INVALID_BREAK_TIME_RANGE",
            "Break time must be inside working hours.",
            status_code=422)


def _tid(user: UserContext) -> uuid.UUID:
    if not user.tenant_id:
        raise HTTPException(403, "No tenant context")
    return uuid.UUID(user.tenant_id)


def _member_row(row) -> dict:
    """Shape a provider_team_members row for the frontend.

    Real bug fixed here: every endpoint returned a raw `SELECT *` mapping,
    whose primary key column is `id` -- but the frontend's
    ProviderTeamMember type (and all of its call sites) read `member_id`,
    which was therefore ALWAYS undefined. The visible effect was severe:
    AddTeamMemberWizard does `setMemberId(res.member.member_id)` after step
    1, then every later step early-returns on `if (!memberId) return;` -- so
    role, services, availability and login were silently never saved, and
    the tenant was left with a name-only technician who could not be
    assigned any work. `member_id` is exposed alongside `id` (rather than
    renaming) so nothing already reading `id` breaks.
    """
    d = dict(row._mapping)
    if "id" in d:
        d["member_id"] = str(d["id"])
    return d


async def _validate_offering_ids(
    db: AsyncSession, tenant_id: uuid.UUID, offering_ids: list[str]
) -> list[str]:
    """Keep service assignments inside the current tenant's enabled catalog."""
    if not offering_ids:
        return []
    rows = (await db.execute(text(
        "SELECT id::text FROM tenant_services "
        "WHERE tenant_id=:tid AND is_enabled=true AND deleted_at IS NULL "
        "AND id = ANY(:ids)"
    ), {"tid": str(tenant_id), "ids": [str(value) for value in offering_ids]})).fetchall()
    return [row[0] for row in rows]


# ── Team Members ──────────────────────────────────────────────────────────────

@router.get("/team-members")
async def list_team_members(
    request: Request,
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    tid = _tid(user)
    q = (
        "SELECT ptm.*, (SELECT u.is_active FROM users u WHERE u.id=ptm.user_id) AS login_active "
        "FROM provider_team_members ptm WHERE ptm.tenant_id = :tid AND ptm.deleted_at IS NULL"
    )
    params: Dict[str, Any] = {"tid": str(tid)}
    if status:
        q += " AND status = :status"
        params["status"] = status
    q += " ORDER BY created_at DESC"
    result = await db.execute(text(q), params)
    rows = [_member_row(r) for r in result.fetchall()]
    skills_by_member = await member_skill_ids(db, tid, [row["member_id"] for row in rows])
    for row in rows:
        row["skill_ids"] = skills_by_member.get(row["member_id"], [])
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    return ok({"members": rows, "count": len(rows)}, request_id=rid)


@router.post("/team-members", status_code=201, dependencies=[Depends(enforce_setup_sequence)])
async def create_team_member(
    payload: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_owner_mutation),
):
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    if not str(payload.get("full_name") or "").strip():
        raise HTTPException(400, "full_name is required.")

    member_type = str(payload.get("member_type") or "technician").lower()
    if member_type not in VALID_MEMBER_TYPES:
        raise ServiceOSException(
            "INVALID_MEMBER_TYPE", "Choose technician, staff, or manager.", status_code=422
        )

    cat_id = str(await resolve_team_category_id(db, tid))

    requested_offering_ids = [str(value) for value in (payload.get("supported_offering_ids") or [])]
    valid_offering_ids = await _validate_offering_ids(db, tid, requested_offering_ids)
    if set(valid_offering_ids) != set(requested_offering_ids):
        raise ServiceOSException(
            "INVALID_SERVICE_ASSIGNMENT",
            "One or more selected services are not enabled for this workspace.",
            status_code=422,
        )
    designation = _validate_designation(member_type, payload.get("designation"))
    if member_type == "technician" and not valid_offering_ids:
        raise ServiceOSException(
            "TECHNICIAN_SERVICE_REQUIRED",
            "Select at least one enabled service this technician can perform.",
            status_code=422,
        )

    requested_skill_ids = [str(value) for value in (payload.get("skill_ids") or [])]
    selected_skills = await validate_skill_ids(db, uuid.UUID(cat_id), requested_skill_ids)

    # Technicians resolve business hours dynamically. Team creation precedes
    # coverage setup, so no schedule is required or copied during this step.

    # Capacity is validated the same way the PUT path validates it -- it
    # feeds the assignment resolver, and 0/negative would make the member
    # permanently unassignable with no visible reason.
    capacity = payload.get("max_concurrent_jobs")
    if capacity is not None and capacity != "":
        try:
            capacity = int(capacity)
        except (TypeError, ValueError):
            raise HTTPException(400, "INVALID_CAPACITY: max_concurrent_jobs must be a whole number.")
        if capacity < 1:
            raise HTTPException(400, "INVALID_CAPACITY: max_concurrent_jobs must be at least 1.")
    else:
        # provider_team_members.max_concurrent_jobs is NOT NULL in the live
        # schema (DEFAULT 4), so a blank capacity must fall back to that
        # default -- binding an explicit NULL overrides the column default
        # and fails the constraint outright. (The ORM model declares this
        # column nullable=True, which does NOT match the live DB; the DB is
        # authoritative here.)
        capacity = DEFAULT_MAX_CONCURRENT_JOBS

    # JSON array params are passed as real JSON via json.dumps rather than
    # str(list).replace("'", '"'), which corrupts any value containing an
    # apostrophe (a genuinely common case in names/skills).
    def _arr(key: str) -> str:
        v = payload.get(key) or []
        return json.dumps(v if isinstance(v, list) else [])

    # Seat gate. Technician headcount is bought with a top-up plan rather than
    # unlocked by a deposit (migration 317), and each seat is also one more job
    # bookable per slot -- so this is the capacity limit, not just a billing
    # one. Checked only for technician-type members: an owner or dispatcher
    # occupies no seat because they take no job.
    # Uses the SHARED predicate. Lowercasing the designation and comparing it
    # to snake_case keys let every MULTI-WORD title through: a "Senior
    # Technician" or "Field Engineer" folded to "senior technician", matched
    # nothing, and was created without consuming a seat -- so the seat limit
    # could be walked straight past. `member_type` counts too, so a technician
    # whose provider left the free-text designation blank is caught as well.
    from app.engines.vertical_catalog.seat_enforcement import assert_seat_available
    from app.engines.home_service_assignment.eligibility import is_technician_role

    if is_technician_role(payload.get("designation"), payload.get("member_type")):
        await assert_seat_available(db, tid)

    new_id = str(uuid.uuid4())
    # profile_photo_url / max_concurrent_jobs / reports_to_* were previously
    # absent from this INSERT even though they are real columns the UI
    # collects and the assignment resolver reads -- so they were silently
    # dropped on create and only ever settable by a later PUT.
    await db.execute(text("""
        INSERT INTO provider_team_members
            (id, tenant_id, member_type, full_name, phone, email, designation,
             status, can_receive_assignment, skills, supported_offering_ids,
             supported_type_ids, supported_brand_ids, service_area_ids, category_id,
             profile_photo_url, max_concurrent_jobs,
             reports_to_display_name, reports_to_designation)
        VALUES (:id, :tid, :member_type, :full_name, :phone, :email, :designation,
                :status, :recv, :skills, :offering_ids,
                :type_ids, :brand_ids, :area_ids, :cat_id,
                :photo, :capacity, :reports_name, :reports_desig)
    """), {
        "id": new_id, "tid": str(tid),
        "member_type": member_type,
        "full_name": str(payload.get("full_name")).strip(),
        "phone": payload.get("phone"),
        "email": payload.get("email"),
        "designation": designation,
        "status": payload.get("status") or "active",
        "recv": payload.get("can_receive_assignment", True),
        "skills": json.dumps([skill["name"] for skill in selected_skills]),
        "offering_ids": json.dumps(valid_offering_ids),
        "type_ids": _arr("supported_type_ids"),
        "brand_ids": _arr("supported_brand_ids"),
        "area_ids": _arr("service_area_ids"),
        "cat_id": cat_id,
        "photo": payload.get("profile_photo_url"),
        "capacity": capacity,
        "reports_name": payload.get("reports_to_display_name"),
        "reports_desig": payload.get("reports_to_designation"),
    })

    await replace_member_skills(
        db, tenant_id=tid, member_id=uuid.UUID(new_id), selected=selected_skills,
        actor_id=user.user_id,
    )
    await record_platform_audit(
        db, operation="provider_team_member.created", engine_id="provider_portal",
        tenant_id=tid, entity_type="provider_team_member", entity_id=new_id,
        actor_id=uuid.UUID(str(user.user_id)), actor_role=user.role, request_id=rid,
        after={"full_name": str(payload.get("full_name")).strip(), "member_type": member_type,
               "designation": designation, "status": payload.get("status") or "active"},
    )
    await db.commit()
    row = await db.execute(text("SELECT * FROM provider_team_members WHERE id=:id"), {"id": new_id})
    member = _member_row(row.fetchone())
    member["skill_ids"] = [skill["id"] for skill in selected_skills]
    return ok({"member": member}, request_id=rid)


@router.get("/team-members/service-coverage")
async def get_team_member_service_coverage(
    request: Request,
    include_availability: bool = Query(True),
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    """Return the real per-service ready-technician rollup used by setup.

    This route intentionally appears before ``/{member_id}`` so the static
    path can never be parsed as a UUID member id.
    """
    from app.engines.home_service_assignment.team_readiness_service import (
        compute_service_coverage,
        compute_team_summary,
    )

    team_summary = await compute_team_summary(
        db, _tid(user), include_availability=include_availability,
    )
    coverage = await compute_service_coverage(
        db, _tid(user), team_summary=team_summary,
    )
    rid = (getattr(request.state, "request_id", None)
           or request.headers.get("X-Request-ID", "—"))
    return ok({"coverage": coverage}, request_id=rid)


@router.get("/team-members/readiness")
async def get_team_member_readiness(
    request: Request,
    include_availability: bool = Query(True),
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    """Canonical onboarding roster readiness, without directory pagination.

    The setup page previously reconstructed this from the first page of the
    operational team directory and returned a different counts shape than its
    own UI consumed. A workspace with more than 50 people therefore displayed
    incomplete member states and ``undefined`` totals.
    """
    from app.engines.home_service_assignment.team_readiness_service import (
        compute_team_summary,
    )

    summary = await compute_team_summary(
        db, _tid(user), include_availability=include_availability,
    )
    rid = (getattr(request.state, "request_id", None)
           or request.headers.get("X-Request-ID", "â€”"))
    return ok(summary, request_id=rid)


@router.post("/team-members/activate")
async def activate_team_member_account(
    payload: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Public, one-time activation endpoint for tenant-created team logins."""
    from app.engines.auth.models import PasswordResetToken, User
    from app.engines.auth.utils import hash_password, validate_password_strength

    token_plain = str(payload.get("activation_token") or "").strip()
    new_password = str(payload.get("new_password") or "")
    token_hash = hashlib.sha256(token_plain.encode()).hexdigest()
    token = (await db.execute(select(PasswordResetToken).where(
        PasswordResetToken.token_hash == token_hash,
        PasswordResetToken.purpose == "team_member_activation",
        PasswordResetToken.status == "active",
    ))).scalar_one_or_none()

    invalid_message = "This activation link is invalid or has expired."
    if token is None or token.expires_at <= utcnow():
        raise ServiceOSException("INVALID_ACTIVATION_TOKEN", invalid_message, status_code=400)
    account = (await db.execute(select(User).where(User.id == token.user_id))).scalar_one_or_none()
    if account is None:
        raise ServiceOSException("INVALID_ACTIVATION_TOKEN", invalid_message, status_code=400)

    password_errors = validate_password_strength(new_password, account.full_name, account.email)
    if password_errors:
        raise ServiceOSException("WEAK_PASSWORD", password_errors[0], status_code=422)

    account.hashed_password = hash_password(new_password)
    account.password_history = [account.hashed_password]
    account.is_active = True
    account.is_verified = True
    account.force_password_change = False
    account.password_changed_at = utcnow()
    token.status = "used"
    token.used_at = utcnow()
    # Activating login credentials must not reactivate the operational roster
    # row. Only the owner-controlled activate endpoint may do that because it
    # rechecks the paid-seat and usage-credit gates first.
    await db.execute(text(
        "UPDATE provider_team_members SET password_generated=false, updated_at=now() "
        "WHERE user_id=:uid AND deleted_at IS NULL"
    ), {"uid": str(account.id)})
    await db.commit()
    rid = (getattr(request.state, "request_id", None)
           or request.headers.get("X-Request-ID", "—"))
    return ok({"activated": True}, request_id=rid)


@router.get("/team-members/{member_id}")
async def get_team_member(
    member_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    result = await db.execute(
        text("SELECT * FROM provider_team_members WHERE id=:id AND tenant_id=:tid AND deleted_at IS NULL"),
        {"id": str(member_id), "tid": str(tid)}
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(404, "Team member not found")
    member = _member_row(row)
    member["skill_ids"] = (await member_skill_ids(db, tid, [member["member_id"]])).get(member["member_id"], [])
    return ok(member, request_id=rid)


@router.put("/team-members/{member_id}", dependencies=[Depends(enforce_setup_sequence)])
async def update_team_member(
    member_id: uuid.UUID,
    payload: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_owner_mutation),
):
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    existing_member = (await db.execute(text(
        "SELECT member_type, designation, status, can_receive_assignment "
        "FROM provider_team_members "
        "WHERE id=:id AND tenant_id=:tid AND deleted_at IS NULL"
    ), {"id": str(member_id), "tid": str(tid)})).fetchone()
    if existing_member is None:
        raise HTTPException(404, "Team member not found")
    # Real bug fixed here: `max_concurrent_jobs` is a real column on
    # provider_team_members and the Team page has always offered it as an
    # editable field, but it was missing from this allow-list -- so saving a
    # technician's capacity silently did nothing (or 400'd with "No valid
    # fields to update" when it was the only field changed). Capacity is what
    # the assignment resolver reads to decide who can take another job, so
    # this was silently pinning every technician at the default.
    allowed = {"full_name", "phone", "email", "designation", "member_type",
                "can_receive_assignment", "supported_offering_ids",
                "supported_type_ids", "supported_brand_ids", "service_area_ids",
                "max_concurrent_jobs",
                # Same class of omission as max_concurrent_jobs above: real
                # columns the Team form collects, previously silently
                # unsaveable because they were missing from this allow-list.
                "profile_photo_url", "reports_to_display_name",
                "reports_to_designation", "status"}
    # Capacity feeds the assignment resolver's "can this member take another
    # job?" check, and it lands in a raw SQL UPDATE below -- so it is
    # validated here rather than trusted. Zero or negative would make the
    # member permanently unassignable with no visible reason.
    if "max_concurrent_jobs" in payload:
        raw = payload["max_concurrent_jobs"]
        if raw is not None:
            try:
                payload["max_concurrent_jobs"] = int(raw)
            except (TypeError, ValueError):
                raise HTTPException(400, "INVALID_CAPACITY: max_concurrent_jobs must be a whole number.")
            if payload["max_concurrent_jobs"] < 1:
                raise HTTPException(400, "INVALID_CAPACITY: max_concurrent_jobs must be at least 1.")

    if "member_type" in payload:
        payload["member_type"] = str(payload["member_type"] or "").lower()
        if payload["member_type"] not in VALID_MEMBER_TYPES:
            raise ServiceOSException(
                "INVALID_MEMBER_TYPE", "Choose technician, staff, or manager.", status_code=422
            )

    # Editing a free staff/manager row into an active technician must consume
    # a seat exactly like creating or reactivating a technician. Without this
    # check the plan limit could be bypassed through the edit form.
    from app.engines.home_service_assignment.eligibility import is_technician_role
    effective_member_type = payload.get("member_type", existing_member.member_type)
    effective_designation = payload.get("designation", existing_member.designation)
    was_technician = is_technician_role(existing_member.designation, existing_member.member_type)
    was_seat_consumer = (
        was_technician and existing_member.status == "active"
        and bool(existing_member.can_receive_assignment)
    )
    becomes_active_technician = (
        is_technician_role(effective_designation, effective_member_type)
        and payload.get("status", existing_member.status) == "active"
        and bool(payload.get("can_receive_assignment", existing_member.can_receive_assignment))
    )
    if becomes_active_technician and not was_seat_consumer:
        from app.engines.vertical_catalog.seat_enforcement import assert_seat_available
        await assert_seat_available(db, tid)
    if "supported_offering_ids" in payload:
        requested = [str(value) for value in (payload["supported_offering_ids"] or [])]
        valid = await _validate_offering_ids(db, tid, requested)
        if set(valid) != set(requested):
            raise ServiceOSException(
                "INVALID_SERVICE_ASSIGNMENT",
                "One or more selected services are not enabled for this workspace.",
                status_code=422,
            )
        payload["supported_offering_ids"] = valid

    selected_skills = None
    if "skill_ids" in payload:
        current_type = payload.get("member_type")
        if not current_type:
            current_type = (await db.execute(text(
                "SELECT member_type FROM provider_team_members WHERE id=:id AND tenant_id=:tid AND deleted_at IS NULL"
            ), {"id": str(member_id), "tid": str(tid)})).scalar()
        cat_id = await resolve_team_category_id(db, tid)
        requested_skill_ids = [str(value) for value in (payload.get("skill_ids") or [])]
        selected_skills = await validate_skill_ids(db, cat_id, requested_skill_ids)

    if becomes_active_technician and not was_technician:
        if not payload.get("supported_offering_ids"):
            raise ServiceOSException(
                "TECHNICIAN_SERVICE_REQUIRED",
                "Select at least one enabled service this technician can perform.",
                status_code=422,
            )

    if "designation" in payload or "member_type" in payload:
        effective_type = payload.get("member_type")
        current = None
        if not effective_type or "designation" not in payload:
            current = existing_member
        effective_type = effective_type or current.member_type
        effective_designation = payload.get("designation") if "designation" in payload else current.designation
        payload["designation"] = _validate_designation(effective_type, effective_designation)
        payload.pop("skill_ids", None)

    sets = ", ".join(f"{k}=:{k}" for k in payload if k in allowed)
    if not sets and selected_skills is None:
        raise HTTPException(400, "No valid fields to update")
    params = {k: v for k, v in payload.items() if k in allowed}
    # These columns are JSONB in PostgreSQL.  Raw ``text()`` statements do
    # not run values through the ORM JSON serializer, so asyncpg expects an
    # encoded JSON string here (the POST path already does the same thing).
    # Passing a Python list raises ``'list' object has no attribute encode``
    # and made every edit to a technician's service assignment fail with a
    # 500 response.
    json_array_fields = {
        "supported_offering_ids",
        "supported_type_ids",
        "supported_brand_ids",
        "service_area_ids",
    }
    for field in json_array_fields.intersection(params):
        value = params[field]
        params[field] = json.dumps(value if isinstance(value, list) else [])
    params["id"] = str(member_id)
    params["tid"] = str(tid)
    if sets:
        await db.execute(text(f"UPDATE provider_team_members SET {sets}, updated_at=now() WHERE id=:id AND tenant_id=:tid"), params)
    if selected_skills is not None:
        await replace_member_skills(
            db, tenant_id=tid, member_id=member_id, selected=selected_skills,
            actor_id=user.user_id,
        )
    row = await db.execute(text("SELECT * FROM provider_team_members WHERE id=:id AND tenant_id=:tid"),
                            {"id": str(member_id), "tid": str(tid)})
    fetched = row.fetchone()
    if fetched is None:
        raise HTTPException(404, "Team member not found")
    member = _member_row(fetched)
    member["skill_ids"] = (await member_skill_ids(db, tid, [member["member_id"]])).get(member["member_id"], [])
    await record_platform_audit(
        db, operation="provider_team_member.updated", engine_id="provider_portal",
        tenant_id=tid, entity_type="provider_team_member", entity_id=str(member_id),
        actor_id=uuid.UUID(str(user.user_id)), actor_role=user.role, request_id=rid,
        after={key: member.get(key) for key in (
            "full_name", "member_type", "designation", "status", "can_receive_assignment", "supported_offering_ids"
        )},
    )
    await db.commit()
    return ok(member, request_id=rid)


@router.delete("/team-members/{member_id}", dependencies=[Depends(enforce_setup_sequence)])
async def delete_team_member(
    member_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_owner_mutation),
):
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    result = await db.execute(
        text("UPDATE provider_team_members SET deleted_at=now() WHERE id=:id AND tenant_id=:tid"),
        {"id": str(member_id), "tid": str(tid)}
    )
    if result.rowcount == 0:
        raise HTTPException(404, "Team member not found")
    await record_platform_audit(
        db, operation="provider_team_member.offboarded", engine_id="provider_portal",
        tenant_id=tid, entity_type="provider_team_member", entity_id=str(member_id),
        actor_id=uuid.UUID(str(user.user_id)), actor_role=user.role, request_id=rid,
    )
    await db.commit()
    return ok({"deleted": True}, request_id=rid)


@router.post("/team-members/{member_id}/activate", dependencies=[Depends(enforce_setup_sequence)])
async def activate_team_member(
    member_id: uuid.UUID, request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_owner_mutation),
):
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))

    # Activating consumes a seat, so it has to answer to the same two limits as
    # creating. Without this the roster gate was trivially defeated: deactivate
    # everyone, then activate more people than the plan pays for, since only
    # ACTIVE members count against the entitlement. Re-activating was also the
    # one-click undo for a credit suspension.
    member = (await db.execute(text(
        "SELECT designation, member_type, status FROM provider_team_members "
        "WHERE id = :id AND tenant_id = :tid AND deleted_at IS NULL"
    ), {"id": str(member_id), "tid": str(tid)})).fetchone()
    if member is None:
        raise HTTPException(404, "Team member not found")

    if member.status != "active":
        from app.engines.home_service_assignment.eligibility import is_technician_role
        if is_technician_role(member.designation, member.member_type):
            from app.engines.vertical_catalog.seat_enforcement import (
                assert_seat_available, get_credit_state,
            )
            await assert_seat_available(db, tid)
            credit = await get_credit_state(db, tid)
            if credit["credit_balance"] <= 0:
                raise ServiceOSException(
                    "TEAM_SUSPENDED_NO_CREDIT",
                    "This workspace has no usage credit, so technicians cannot be activated.",
                    status_code=409,
                    blocking_rule="credit.team_suspension",
                    resolution="Add credit with a top-up plan, and suspended technicians "
                               "are restored automatically.",
                    context=credit,
                )

    # `credit_suspended_at` is cleared: this is now a deliberate activation, and
    # a later restore must not treat the member as one the system had suspended.
    result = await db.execute(text(
        "UPDATE provider_team_members SET status='active', credit_suspended_at=NULL, "
        "updated_at=now() WHERE id=:id AND tenant_id=:tid AND deleted_at IS NULL"
    ), {"id": str(member_id), "tid": str(tid)})
    if result.rowcount == 0:
        raise HTTPException(404, "Team member not found")
    await record_platform_audit(
        db, operation="provider_team_member.activated", engine_id="provider_portal",
        tenant_id=tid, entity_type="provider_team_member", entity_id=str(member_id),
        actor_id=uuid.UUID(str(user.user_id)), actor_role=user.role, request_id=rid,
        after={"status": "active"},
    )
    await db.commit()
    row = await db.execute(text("SELECT * FROM provider_team_members WHERE id=:id AND tenant_id=:tid"),
                            {"id": str(member_id), "tid": str(tid)})
    fetched = row.fetchone()
    if fetched is None:
        raise HTTPException(404, "Team member not found")
    return ok(_member_row(fetched), request_id=rid)


@router.post("/team-members/{member_id}/deactivate", dependencies=[Depends(enforce_setup_sequence)])
async def deactivate_team_member(
    member_id: uuid.UUID, request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_owner_mutation),
):
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    member_row = await db.execute(
        text("SELECT user_id FROM provider_team_members WHERE id=:id AND tenant_id=:tid"),
        {"id": str(member_id), "tid": str(tid)}
    )
    member = member_row.fetchone()
    if member is None:
        raise HTTPException(404, "Team member not found")
    await db.execute(text("UPDATE provider_team_members SET status='inactive', updated_at=now() WHERE id=:id AND tenant_id=:tid"), {"id": str(member_id), "tid": str(tid)})
    if member.user_id:
        # Slice 2F-2, Workstream 6: a deactivated team member's linked login
        # (provider_team_members.user_id) must have its sessions revoked --
        # the same DB+Redis pattern proven for AuthService.deactivate_staff
        # in Slice 2F/2F-1. Without this, an already-issued JWT for the
        # deactivated member keeps authenticating until natural expiry.
        from app.engines.auth.models import UserSession
        from app.engines.auth.constants import ACCESS_TOKEN_EXPIRE_MINUTES
        from app.redis_client import get_redis
        from app.models.base import utcnow
        active_sessions = await db.execute(
            select(UserSession.id).where(UserSession.user_id == member.user_id, UserSession.revoked_at.is_(None))
        )
        session_ids = [row[0] for row in active_sessions]
        if session_ids:
            await db.execute(
                update(UserSession).where(
                    UserSession.user_id == member.user_id, UserSession.revoked_at.is_(None)
                ).values(revoked_at=utcnow(), revocation_reason="team_member_deactivated")
            )
            redis = get_redis()
            for sid in session_ids:
                try:
                    await redis.setex(f"serviceos:session:revoked:{sid}", ACCESS_TOKEN_EXPIRE_MINUTES * 60, "1")
                except Exception:
                    pass
    await record_platform_audit(
        db, operation="provider_team_member.deactivated", engine_id="provider_portal",
        tenant_id=tid, entity_type="provider_team_member", entity_id=str(member_id),
        actor_id=uuid.UUID(str(user.user_id)), actor_role=user.role, request_id=rid,
        after={"status": "inactive", "sessions_revoked": bool(member.user_id)},
    )
    await db.commit()
    row = await db.execute(text("SELECT * FROM provider_team_members WHERE id=:id AND tenant_id=:tid"),
                            {"id": str(member_id), "tid": str(tid)})
    fetched = row.fetchone()
    if fetched is None:
        raise HTTPException(404, "Team member not found")
    return ok(_member_row(fetched), request_id=rid)


# Maps provider_team_members.member_type -> users.role. Only "technician"
# and "staff" exist as real role keys with permission defaults (see
# app/core/permissions.py ROLE_DEFAULTS); trainer/counsellor/agent/manager
# are vertical-flavoured job titles, not distinct permission sets, so they
# all resolve to "staff" rather than silently creating a role with ZERO
# permissions (the exact bug the "technician" comment in permissions.py
# documents having already been hit once).
_MEMBER_TYPE_TO_ROLE = {"technician": "technician"}


@router.post("/team-members/{member_id}/create-login", dependencies=[Depends(enforce_setup_sequence)])
async def create_member_login(
    member_id: uuid.UUID, request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_owner_mutation),
):
    """Create a real login (users row) for an existing team member and link
    it back via provider_team_members.user_id.

    Previously a hardcoded stub that returned {"credentials": None} and
    created nothing -- so the tenant-portal "Login access" option silently
    did nothing, AND the member never gained a users row, which is why
    tenant-created team members never appeared on the super-admin Staff
    page (app/engines/auth/admin_staff_router.py selects FROM users).
    provider_team_members.user_id was always meant to hold a real users.id
    -- deactivate_team_member above already revokes that user's sessions
    -- there was simply no path that ever populated it.

    Creates an inactive account plus a one-time activation token. A temporary
    password is never returned to the tenant owner or stored in plaintext.
    """
    from app.engines.auth.models import PasswordResetToken, User
    from app.engines.auth.utils import hash_password

    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))

    row = await db.execute(
        text("SELECT id, full_name, email, phone, member_type, user_id "
             "FROM provider_team_members WHERE id=:id AND tenant_id=:tid AND deleted_at IS NULL"),
        {"id": str(member_id), "tid": str(tid)},
    )
    member = row.fetchone()
    if member is None:
        raise HTTPException(404, "Team member not found")

    full_name = (member.full_name or "").strip()
    if not full_name:
        raise ServiceOSException("TEAM_MEMBER_NAME_REQUIRED",
                                 "This team member has no name, so a login cannot be created.",
                                 status_code=422)

    email = (member.email or "").lower().strip()
    if not email:
        raise ServiceOSException(
            "TEAM_MEMBER_EMAIL_REQUIRED",
            "Add the team member's email before sending app access.",
            status_code=422,
        )

    linked_user = await db.get(User, member.user_id) if member.user_id else None
    if linked_user and linked_user.is_active:
        return ok({
            "member_id": str(member_id), "user_id": str(linked_user.id),
            "activation_sent": False, "already_had_login": True,
            "access_active": True, "invite_resent": False,
        }, request_id=rid)

    existing = await db.execute(select(User).where(User.email == email))
    existing_user = existing.scalar_one_or_none()
    if existing_user and (not linked_user or existing_user.id != linked_user.id):
        if str(existing_user.tenant_id) != str(tid):
            raise ServiceOSException(
                "CROSS_TENANT_ACCOUNT_EXISTS",
                "That email already belongs to an account in another workspace.",
                status_code=409,
            )
        raise ServiceOSException(
            "TEAM_MEMBER_EMAIL_IN_USE",
            f"A user with email {email} already exists. Change this member's email, "
            "or link the existing account instead.",
            status_code=409)

    invite_resent = linked_user is not None
    if linked_user:
        # Supports the deliberate "add email later" flow and repairs legacy
        # placeholder accounts without ever creating a duplicate user.
        linked_user.email = email
        linked_user.phone = member.phone
        linked_user.full_name = full_name
        linked_user.role = _MEMBER_TYPE_TO_ROLE.get(member.member_type, "staff")
        linked_user.is_active = False
        linked_user.is_verified = False
        new_user = linked_user
        old_tokens = (await db.execute(select(PasswordResetToken).where(
            PasswordResetToken.user_id == linked_user.id,
            PasswordResetToken.purpose == "team_member_activation",
            PasswordResetToken.status == "active",
        ))).scalars().all()
        for old_token in old_tokens:
            old_token.status = "revoked"
    else:
        # No account is created until a deliverable email exists. This keeps
        # an operational technician profile independent from optional app access.
        unusable_password = secrets.token_urlsafe(48)
        new_user = User(
            email=email,
            phone=member.phone,
            full_name=full_name,
            role=_MEMBER_TYPE_TO_ROLE.get(member.member_type, "staff"),
            tenant_id=tid,
            hashed_password=hash_password(unusable_password),
            is_active=False,
            is_verified=False,
            force_password_change=False,
        )
        db.add(new_user)
        await db.flush()

    token_plain = secrets.token_urlsafe(32)
    activation_token = PasswordResetToken(
        user_id=new_user.id,
        token_hash=hashlib.sha256(token_plain.encode()).hexdigest(),
        purpose="team_member_activation",
        status="active",
        expires_at=utcnow() + timedelta(hours=24),
        created_by_user_id=uuid.UUID(user.user_id),
        created_ip=request.client.host if request.client else None,
    )
    db.add(activation_token)

    await db.execute(
        text("UPDATE provider_team_members "
             "SET user_id=:uid, username=:uname, password_generated=true, updated_at=now() "
             "WHERE id=:id AND tenant_id=:tid"),
        {"uid": str(new_user.id), "uname": email, "id": str(member_id), "tid": str(tid)},
    )
    await db.commit()

    activation_sent = False
    try:
        from app.email_client import send_email
        activation_sent = await send_email(
            email,
            "Activate your Fuvay team account",
            (f"Hi {full_name},\n\nYour Fuvay team account is ready. "
             f"Open the team activation page and enter this one-time code:\n\n"
             f"{token_plain}\n\nThis code expires in 24 hours."),
        )
    except Exception:
        activation_sent = False

    return ok({
        "member_id": str(member_id),
        "user_id": str(new_user.id),
        "activation_sent": activation_sent,
        "activation_token": token_plain if settings.DEBUG else None,
        "expires_at": activation_token.expires_at.isoformat(),
        "already_had_login": False,
        "access_active": False,
        "invite_resent": invite_resent,
    }, request_id=rid)


# ── Availability ──────────────────────────────────────────────────────────────

@router.get("/availability")
async def list_availability(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    params = {"tid": str(tid)}
    where = "tenant_id=:tid"
    select_clause = "SELECT *"
    order_by = "day_of_week, start_time"
    if str(user.role) in ("Role.STAFF", "Role.TECHNICIAN", "staff", "technician"):
        # All technicians inherit the current business schedule.
        where += " AND scope_type='provider' AND scope_id IS NULL"
        # Setup presets can leave historical rows for the same weekday. The
        # staff view is an effective weekly schedule, not the provider's rule
        # editor, so expose only the newest row for each day.
        select_clause = "SELECT DISTINCT ON (day_of_week) *"
        order_by = "day_of_week, updated_at DESC, start_time"
    result = await db.execute(
        text(f"{select_clause} FROM provider_availability_rules WHERE {where} ORDER BY {order_by}"),
        params,
    )
    rows = [dict(r._mapping) for r in result.fetchall()]
    if str(user.role) in ("Role.STAFF", "Role.TECHNICIAN", "staff", "technician"):
        from app.engines.home_service_booking.provider_slot_service import _slots_from_rule
        for rule in rows:
            rule["provider_daily_limit"] = rule.get("max_jobs_per_day")
            rule["max_jobs_per_day"] = len(_slots_from_rule(rule)) if rule.get("is_active") else 0
            rule["slot_duration_minutes"] = 120
            rule["inherited_from_business"] = True
    return ok({"rules": rows, "count": len(rows)}, request_id=rid)


@router.get("/availability/slot-preview")
async def preview_business_slots(
    day: date, request: Request,
    db: AsyncSession = Depends(get_db), user: UserContext = Depends(get_current_user),
):
    from app.engines.home_service_booking.provider_slot_service import daily_slot_preview
    return ok(await daily_slot_preview(db, _tid(user), day), request_id=getattr(request.state, "request_id", None))


async def _validate_slot_capacity(db, tenant_id, max_bookings_per_slot) -> None:
    """A provider cannot promise more simultaneous visits than it has people.

    Refused on SAVE, not quietly clamped at booking time. The engine already caps the
    effective number, but a form that stores 5 while 2 is enforced shows the provider a
    figure that is not in force -- and they plan around the number they can see.

    Fewer than the team is always allowed: choosing to run one visit at a time with four
    technicians is a legitimate way to work.

    The count comes from `provider_slot_service.assignable_technician_count`, the same
    function the booking engine caps with, so the limit stated here and the limit applied
    there can never drift apart.
    """
    if max_bookings_per_slot is None:
        return
    try:
        requested = int(max_bookings_per_slot)
    except (TypeError, ValueError):
        raise ServiceOSException(
            "INVALID_MAX_BOOKINGS_PER_SLOT",
            "max_bookings_per_slot must be a whole number.", status_code=422)
    if requested <= 0:
        raise ServiceOSException(
            "INVALID_MAX_BOOKINGS_PER_SLOT",
            "max_bookings_per_slot must be at least 1.", status_code=422)

    from app.engines.home_service_booking.provider_slot_service import (
        assignable_technician_count,
    )
    technicians = await assignable_technician_count(db, tenant_id)
    # -1 means the team could not be read. The rule stands rather than blocking a save on
    # a failed query -- the booking engine makes the same choice for the same reason.
    if technicians < 0:
        return
    if requested > technicians:
        raise ServiceOSException(
            "CAPACITY_EXCEEDS_TEAM",
            (f"You have {technicians} technician(s) who can take assignments, so a slot "
             f"cannot hold {requested} bookings."),
            status_code=422,
            resolution="Add technicians to your team, or lower the bookings per slot.",
        )


async def _validate_daily_job_capacity(db, tid, rule):
    if rule.get("scope_type", "provider") != "provider" or rule.get("max_jobs_per_day") is None:
        return
    from app.engines.home_service_booking.provider_slot_service import _slots_from_rule
    from app.engines.vertical_catalog.seat_enforcement import get_seat_usage
    usage = await get_seat_usage(db, tid)
    maximum = len(_slots_from_rule(rule)) * min(usage["entitled_seats"], usage["used_seats"])
    requested = rule["max_jobs_per_day"]
    if isinstance(requested, bool) or not isinstance(requested, int) or requested < 1 or requested > maximum:
        raise ServiceOSException("DAILY_CAPACITY_EXCEEDS_TEAM", f"Maximum jobs per day must be a whole number between 1 and {maximum}. Leave it automatic if no technician capacity is configured.", status_code=422)


@router.post("/availability", status_code=201, dependencies=[Depends(enforce_setup_sequence)])
async def create_availability(
    payload: dict, request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_owner_mutation),
):
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    start_time, end_time = payload.get("start_time", "09:00"), payload.get("end_time", "18:00")
    break_start, break_end = payload.get("break_start_time"), payload.get("break_end_time")
    _validate_availability_time_range(start_time, end_time)
    _validate_break_time(start_time, end_time, break_start, break_end)
    if payload.get("max_jobs_per_day") is not None and payload["max_jobs_per_day"] <= 0:
        raise ServiceOSException("INVALID_MAX_JOBS_PER_DAY", "max_jobs_per_day must be positive.", status_code=422)
    await _validate_slot_capacity(db, tid, payload.get("max_bookings_per_slot"))
    await _validate_daily_job_capacity(db, tid, payload)
    new_id = str(uuid.uuid4())
    await db.execute(text("""
        INSERT INTO provider_availability_rules
            (id, tenant_id, scope_type, scope_id, day_of_week, start_time, end_time,
             slot_duration_minutes, max_bookings_per_slot, is_active, category_id,
             break_start_time, break_end_time, max_jobs_per_day, timezone, emergency_available)
        VALUES (:id, :tid, :scope_type, :scope_id, :dow, :start, :end, :slot, :max, :active, :cat_id,
                :break_start, :break_end, :max_jobs, :tz, :emergency)
    """), {
        "id": new_id, "tid": str(tid),
        "scope_type": payload.get("scope_type", "provider"),
        "scope_id": payload.get("scope_id"),
        "dow": payload.get("day_of_week", 0),
        "start": start_time,
        "end": end_time,
        "slot": payload.get("slot_duration_minutes"),
        "max": payload.get("max_bookings_per_slot"),
        "active": payload.get("is_active", True),
        "cat_id": payload.get("category_id"),
        "break_start": break_start, "break_end": break_end,
        "max_jobs": payload.get("max_jobs_per_day"),
        "tz": payload.get("timezone", "Asia/Kolkata"),
        "emergency": payload.get("emergency_available", False),
    })
    await db.commit()
    row = await db.execute(text("SELECT * FROM provider_availability_rules WHERE id=:id"), {"id": new_id})
    return ok(dict(row.fetchone()._mapping), request_id=rid)


# Declared BEFORE `/availability/{rule_id}`, and it has to stay that way.
#
# FastAPI matches routes in declaration order. This route used to sit further down the
# file, below the `{rule_id}` route, so `GET /availability/exceptions` matched
# `{rule_id}` first, tried to parse the literal string "exceptions" as a UUID, and
# returned 422 for every caller. Holidays and closure dates could therefore never be
# listed, and the Coverage & Availability page -- which loads areas, rules and exceptions
# together -- failed its entire load on that one rejection and rendered "We couldn't load
# your coverage and availability settings" instead of the page.
#
# A literal path segment must be registered before the parameterised one that would
# otherwise swallow it. The POST/PUT/DELETE exception routes below do not collide: those
# are two or three segments deep and the `{rule_id}` routes are one.
@router.get("/availability/exceptions")
async def list_availability_exceptions(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    result = await db.execute(
        text("SELECT * FROM tenant_availability_exceptions WHERE tenant_id=:tid AND status='active' ORDER BY date"),
        {"tid": str(tid)})
    rows = [dict(r._mapping) for r in result.fetchall()]
    return ok({"exceptions": rows, "count": len(rows)}, request_id=rid)


@router.get("/availability/{rule_id}")
async def get_availability(
    rule_id: uuid.UUID, request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    row = await db.execute(text("SELECT * FROM provider_availability_rules WHERE id=:id AND tenant_id=:tid"), {"id": str(rule_id), "tid": str(tid)})
    r = row.fetchone()
    if not r:
        raise HTTPException(404, "Availability rule not found")
    return ok(dict(r._mapping), request_id=rid)


@router.put("/availability/{rule_id}", dependencies=[Depends(enforce_setup_sequence)])
async def update_availability(
    rule_id: uuid.UUID, payload: dict, request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_owner_mutation),
):
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    allowed = {"scope_type", "scope_id", "day_of_week", "start_time", "end_time", "slot_duration_minutes",
               "max_bookings_per_slot", "is_active", "break_start_time", "break_end_time",
               "max_jobs_per_day", "timezone", "emergency_available"}
    if payload.keys() & {"max_jobs_per_day", "start_time", "end_time", "break_start_time", "break_end_time"}:
        capacity_row = (await db.execute(text(
            "SELECT * FROM provider_availability_rules WHERE id=:id AND tenant_id=:tid"
        ), {"id": str(rule_id), "tid": str(tid)})).fetchone()
        if capacity_row:
            await _validate_daily_job_capacity(db, tid, {**dict(capacity_row._mapping), **payload})
    # Same ceiling on edit as on create: raising an existing rule past the team is the
    # likelier route to an impossible promise, since the rule already exists and looks
    # settled.
    if "max_bookings_per_slot" in payload:
        await _validate_slot_capacity(db, tid, payload.get("max_bookings_per_slot"))
    if payload.keys() & {"start_time", "end_time", "break_start_time", "break_end_time"}:
        existing_row = (await db.execute(
            text("SELECT start_time, end_time, break_start_time, break_end_time "
                 "FROM provider_availability_rules WHERE id=:id AND tenant_id=:tid"),
            {"id": str(rule_id), "tid": str(tid)})).fetchone()
        if existing_row:
            start_time = payload.get("start_time", existing_row.start_time)
            end_time = payload.get("end_time", existing_row.end_time)
            break_start = payload.get("break_start_time", existing_row.break_start_time)
            break_end = payload.get("break_end_time", existing_row.break_end_time)
            _validate_availability_time_range(start_time, end_time)
            _validate_break_time(start_time, end_time, break_start, break_end)
    if payload.get("max_jobs_per_day") is not None and payload["max_jobs_per_day"] <= 0:
        raise ServiceOSException("INVALID_MAX_JOBS_PER_DAY", "max_jobs_per_day must be positive.", status_code=422)
    sets = ", ".join(f"{k}=:{k}" for k in payload if k in allowed)
    if sets:
        params = {k: v for k, v in payload.items() if k in allowed}
        params["id"] = str(rule_id)
        params["tid"] = str(tid)
        await db.execute(text(f"UPDATE provider_availability_rules SET {sets}, updated_at=now() WHERE id=:id AND tenant_id=:tid"), params)
        await db.commit()
    row = await db.execute(text("SELECT * FROM provider_availability_rules WHERE id=:id AND tenant_id=:tid"),
                            {"id": str(rule_id), "tid": str(tid)})
    fetched = row.fetchone()
    if fetched is None:
        raise HTTPException(404, "Availability rule not found")
    return ok(dict(fetched._mapping), request_id=rid)


@router.delete("/availability/{rule_id}", dependencies=[Depends(enforce_setup_sequence)])
async def delete_availability(
    rule_id: uuid.UUID, request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_owner_mutation),
):
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    await db.execute(text("DELETE FROM provider_availability_rules WHERE id=:id AND tenant_id=:tid"), {"id": str(rule_id), "tid": str(tid)})
    await db.commit()
    return ok({"deleted": True}, request_id=rid)


# ── Availability Exceptions / Holidays (HS5B) ─────────────────────────────────
# The GET for this group lives above the `/availability/{rule_id}` route, which is the
# only place it can work from; see the note there.


def _parse_date(value):
    """Accepts an ISO date string ('2026-08-20') or an already-parsed
    datetime.date (e.g. read back from a DB row) — asyncpg needs a real
    date object for a `date` column, not a bare string."""
    import datetime as _dt
    if isinstance(value, _dt.date):
        return value
    return _dt.date.fromisoformat(str(value))


def _validate_exception_payload(payload: dict) -> None:
    if not payload.get("date"):
        raise ServiceOSException("EXCEPTION_DATE_REQUIRED", "Date is required.", status_code=422)
    if not payload.get("reason"):
        raise ServiceOSException("EXCEPTION_REASON_REQUIRED", "Reason is required.", status_code=422)
    full_day = payload.get("full_day_closed", True)
    if not full_day:
        if not payload.get("start_time") or not payload.get("end_time"):
            raise ServiceOSException("EXCEPTION_TIME_REQUIRED",
                "Start time and end time are required for a partial-day exception.", status_code=422)
        if payload["end_time"] <= payload["start_time"]:
            raise ServiceOSException("INVALID_EXCEPTION_TIME_RANGE",
                "Exception end time must be after start time.", status_code=422)


@router.post("/availability/exceptions", status_code=201, dependencies=[Depends(enforce_setup_sequence)])
async def create_availability_exception(
    payload: dict, request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_owner_mutation),
):
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    _validate_exception_payload(payload)
    new_id = str(uuid.uuid4())
    await db.execute(text("""
        INSERT INTO tenant_availability_exceptions
            (id, tenant_id, date, reason, full_day_closed, start_time, end_time,
             affected_service_area_ids, affected_service_ids, status)
        VALUES (:id, :tid, :date, :reason, :full_day, :start, :end,
                CAST(:areas AS jsonb), CAST(:services AS jsonb), 'active')
    """), {
        "id": new_id, "tid": str(tid),
        "date": _parse_date(payload["date"]), "reason": payload["reason"],
        "full_day": payload.get("full_day_closed", True),
        "start": payload.get("start_time"), "end": payload.get("end_time"),
        "areas": json.dumps(payload.get("affected_service_area_ids") or []),
        "services": json.dumps(payload.get("affected_service_ids") or []),
    })
    await db.commit()
    row = await db.execute(text("SELECT * FROM tenant_availability_exceptions WHERE id=:id"), {"id": new_id})
    return ok(dict(row.fetchone()._mapping), request_id=rid)


@router.put("/availability/exceptions/{exception_id}", dependencies=[Depends(enforce_setup_sequence)])
async def update_availability_exception(
    exception_id: uuid.UUID, payload: dict, request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_owner_mutation),
):
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    existing = (await db.execute(
        text("SELECT * FROM tenant_availability_exceptions WHERE id=:id AND tenant_id=:tid"),
        {"id": str(exception_id), "tid": str(tid)})).fetchone()
    if not existing:
        raise HTTPException(404, "Exception not found")
    merged = {**dict(existing._mapping), **payload}
    _validate_exception_payload(merged)
    await db.execute(text("""
        UPDATE tenant_availability_exceptions
        SET date=:date, reason=:reason, full_day_closed=:full_day, start_time=:start, end_time=:end,
            affected_service_area_ids=CAST(:areas AS jsonb), affected_service_ids=CAST(:services AS jsonb),
            updated_at=now()
        WHERE id=:id AND tenant_id=:tid
    """), {
        "id": str(exception_id), "tid": str(tid),
        "date": _parse_date(merged["date"]), "reason": merged["reason"], "full_day": merged.get("full_day_closed", True),
        "start": merged.get("start_time"), "end": merged.get("end_time"),
        "areas": json.dumps(merged.get("affected_service_area_ids") or []),
        "services": json.dumps(merged.get("affected_service_ids") or []),
    })
    await db.commit()
    row = await db.execute(text("SELECT * FROM tenant_availability_exceptions WHERE id=:id"), {"id": str(exception_id)})
    return ok(dict(row.fetchone()._mapping), request_id=rid)


@router.delete("/availability/exceptions/{exception_id}", dependencies=[Depends(enforce_setup_sequence)])
async def delete_availability_exception(
    exception_id: uuid.UUID, request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_owner_mutation),
):
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    await db.execute(
        text("UPDATE tenant_availability_exceptions SET status='deleted', updated_at=now() WHERE id=:id AND tenant_id=:tid"),
        {"id": str(exception_id), "tid": str(tid)})
    await db.commit()
    return ok({"deleted": True}, request_id=rid)


# ── Booking Window Settings (HS5B) ────────────────────────────────────────────

@router.get("/booking-window")
async def get_booking_window(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    row = (await db.execute(
        text("SELECT * FROM tenant_booking_window_settings WHERE tenant_id=:tid"), {"tid": str(tid)})).fetchone()
    if row:
        data = dict(row._mapping)
    else:
        data = {
            "tenant_id": str(tid), "minimum_notice_minutes": 120, "maximum_advance_booking_days": 7,
            "slot_duration_minutes": 60, "buffer_minutes_between_jobs": 30,
            "allow_same_day_booking": True, "emergency_booking_allowed": False, "timezone": "Asia/Kolkata",
        }
    return ok(data, request_id=rid)


def _validate_booking_window(payload: dict) -> None:
    if payload.get("minimum_notice_minutes") is not None and payload["minimum_notice_minutes"] < 0:
        raise ServiceOSException("INVALID_MINIMUM_NOTICE", "minimum_notice_minutes must be >= 0.", status_code=422)
    if payload.get("maximum_advance_booking_days") is not None and payload["maximum_advance_booking_days"] < 1:
        raise ServiceOSException("INVALID_ADVANCE_BOOKING_DAYS", "maximum_advance_booking_days must be >= 1.", status_code=422)
    if payload.get("slot_duration_minutes") is not None and payload["slot_duration_minutes"] <= 0:
        raise ServiceOSException("INVALID_SLOT_DURATION", "slot_duration_minutes must be > 0.", status_code=422)
    if payload.get("buffer_minutes_between_jobs") is not None and payload["buffer_minutes_between_jobs"] < 0:
        raise ServiceOSException("INVALID_BUFFER_MINUTES", "buffer_minutes_between_jobs must be >= 0.", status_code=422)


@router.put("/booking-window", dependencies=[Depends(enforce_setup_sequence)])
async def update_booking_window(
    payload: dict, request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_owner_mutation),
):
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    _validate_booking_window(payload)
    defaults = {
        "minimum_notice_minutes": 120, "maximum_advance_booking_days": 7, "slot_duration_minutes": 60,
        "buffer_minutes_between_jobs": 30, "allow_same_day_booking": True,
        "emergency_booking_allowed": False, "timezone": "Asia/Kolkata",
    }
    merged = {**defaults, **payload}
    existing = (await db.execute(
        text("SELECT id FROM tenant_booking_window_settings WHERE tenant_id=:tid"), {"tid": str(tid)})).fetchone()
    if existing:
        await db.execute(text("""
            UPDATE tenant_booking_window_settings SET
                minimum_notice_minutes=:mn, maximum_advance_booking_days=:mad, slot_duration_minutes=:sd,
                buffer_minutes_between_jobs=:bm, allow_same_day_booking=:sdb,
                emergency_booking_allowed=:eba, timezone=:tz, updated_at=now()
            WHERE tenant_id=:tid
        """), {"tid": str(tid), "mn": merged["minimum_notice_minutes"], "mad": merged["maximum_advance_booking_days"],
                "sd": merged["slot_duration_minutes"], "bm": merged["buffer_minutes_between_jobs"],
                "sdb": merged["allow_same_day_booking"], "eba": merged["emergency_booking_allowed"], "tz": merged["timezone"]})
    else:
        await db.execute(text("""
            INSERT INTO tenant_booking_window_settings
                (tenant_id, minimum_notice_minutes, maximum_advance_booking_days, slot_duration_minutes,
                 buffer_minutes_between_jobs, allow_same_day_booking, emergency_booking_allowed, timezone)
            VALUES (:tid, :mn, :mad, :sd, :bm, :sdb, :eba, :tz)
        """), {"tid": str(tid), "mn": merged["minimum_notice_minutes"], "mad": merged["maximum_advance_booking_days"],
                "sd": merged["slot_duration_minutes"], "bm": merged["buffer_minutes_between_jobs"],
                "sdb": merged["allow_same_day_booking"], "eba": merged["emergency_booking_allowed"], "tz": merged["timezone"]})
    await db.commit()
    row = await db.execute(text("SELECT * FROM tenant_booking_window_settings WHERE tenant_id=:tid"), {"tid": str(tid)})
    return ok(dict(row.fetchone()._mapping), request_id=rid)


# ── Per-Area Service / Type / Brand Coverage (HS5B) ──────────────────────────

@router.get("/service-areas/{area_id}/coverage")
async def get_area_coverage(
    area_id: uuid.UUID, request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    result = await db.execute(
        text("SELECT * FROM tenant_service_area_services WHERE tenant_service_area_id=:aid AND tenant_id=:tid"),
        {"aid": str(area_id), "tid": str(tid)})
    rows = [dict(r._mapping) for r in result.fetchall()]
    return ok({"coverage": rows, "count": len(rows)}, request_id=rid)


@router.put("/service-areas/{area_id}/coverage", dependencies=[Depends(enforce_setup_sequence)])
async def set_area_coverage(
    area_id: uuid.UUID, payload: dict, request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_mutation_permission(P.TENANT_SERVICE_AREA_SERVICE_UPDATE)),
):
    """HS5B — per-area service/type/brand coverage. Validates the type
    belongs to the selected service and the brand belongs to the selected
    service (reusing the real master_service_types/master_service_brands
    mapping tables — the same source of truth the admin catalog uses),
    matching the type-dependent-scoping pattern established in migration 120."""
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))

    area = (await db.execute(
        text("SELECT id FROM tenant_service_areas WHERE id=:aid AND tenant_id=:tid"),
        {"aid": str(area_id), "tid": str(tid)})).fetchone()
    if not area:
        raise HTTPException(404, "Service area not found")

    service_id = payload.get("service_id")
    if not service_id:
        raise ServiceOSException("COVERAGE_SERVICE_REQUIRED", "service_id is required.", status_code=422)
    tenant_svc = (await db.execute(
        text("SELECT job_type FROM tenant_services WHERE tenant_id=:tid AND master_service_id=:sid AND is_active=true"),
        {"tid": str(tid), "sid": service_id})).fetchone()
    if not tenant_svc:
        raise ServiceOSException("SERVICE_NOT_TENANT_ENABLED",
            "This service is not enabled by your business.", status_code=422)

    service_type_id = payload.get("service_type_id")
    if service_type_id:
        type_match = (await db.execute(
            text("SELECT 1 FROM master_service_types WHERE master_service_id=:sid AND service_type_id=:stid AND is_active=true"),
            {"sid": service_id, "stid": service_type_id})).fetchone()
        if not type_match:
            raise ServiceOSException("INVALID_SERVICE_TYPE_FOR_COVERAGE",
                "Selected service type does not belong to this service.", status_code=422)

    brand_id = payload.get("brand_id")
    if brand_id:
        brand_match = (await db.execute(
            text("SELECT 1 FROM master_service_brands WHERE master_service_id=:sid AND brand_id=:bid AND is_active=true"),
            {"sid": service_id, "bid": brand_id})).fetchone()
        if not brand_match:
            raise ServiceOSException("INVALID_BRAND_FOR_COVERAGE",
                "Selected brand is not valid for this service type.", status_code=422)

    existing = (await db.execute(
        text("SELECT id FROM tenant_service_area_services WHERE tenant_service_area_id=:aid "
             "AND service_id=:sid AND service_type_id IS NOT DISTINCT FROM :stid AND brand_id IS NOT DISTINCT FROM :bid"),
        {"aid": str(area_id), "sid": service_id, "stid": service_type_id, "bid": brand_id})).fetchone()
    if existing:
        await db.execute(text(
            "UPDATE tenant_service_area_services SET is_available=:avail, updated_at=now() WHERE id=:id"
        ), {"avail": payload.get("is_available", True), "id": existing.id})
        row_id = existing.id
    else:
        row_id = str(uuid.uuid4())
        await db.execute(text("""
            INSERT INTO tenant_service_area_services
                (id, tenant_service_area_id, tenant_id, service_id, service_type_id, brand_id, job_type, is_available)
            VALUES (:id, :aid, :tid, :sid, :stid, :bid, :jt, :avail)
        """), {"id": row_id, "aid": str(area_id), "tid": str(tid), "sid": service_id,
                "stid": service_type_id, "bid": brand_id, "jt": tenant_svc.job_type,
                "avail": payload.get("is_available", True)})
    await db.commit()
    row = await db.execute(text("SELECT * FROM tenant_service_area_services WHERE id=:id"), {"id": str(row_id)})
    return ok(dict(row.fetchone()._mapping), request_id=rid)


# Preset definitions — identifies rules created by each preset key.
_PRESET_DEFS: dict[str, dict] = {
    "standard":  {"start_time": "09:00", "end_time": "18:00", "slot_duration_minutes": 60, "days": [1,2,3,4,5,6]},
    "weekdays":  {"start_time": "09:00", "end_time": "18:00", "slot_duration_minutes": 60, "days": [1,2,3,4,5]},
    "emergency": {"start_time": "08:00", "end_time": "22:00", "slot_duration_minutes": 30, "days": [0,1,2,3,4,5,6]},
}


@router.post("/availability/preset/{preset_key}", status_code=200, dependencies=[Depends(enforce_setup_sequence)])
async def apply_availability_preset(
    preset_key: str, request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_owner_mutation),
):
    """Idempotent preset apply — deletes any existing matching rules first, then
    creates one rule per day.  Safe to call multiple times without duplicates."""
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    defn = _PRESET_DEFS.get(preset_key)
    if not defn:
        raise HTTPException(400, f"Unknown preset key: {preset_key!r}")

    # Delete existing rules that exactly match this preset pattern for this tenant.
    await db.execute(text("""
        DELETE FROM provider_availability_rules
        WHERE tenant_id=:tid
          AND scope_type='provider'
          AND scope_id IS NULL
          AND start_time=:start
          AND end_time=:end
          AND slot_duration_minutes=:slot
    """), {"tid": str(tid), "start": defn["start_time"], "end": defn["end_time"], "slot": defn["slot_duration_minutes"]})

    # Insert one rule per day.
    created_ids: list[str] = []
    for dow in defn["days"]:
        new_id = str(uuid.uuid4())
        await db.execute(text("""
            INSERT INTO provider_availability_rules
                (id, tenant_id, scope_type, scope_id, day_of_week, start_time, end_time,
                 slot_duration_minutes, max_bookings_per_slot, is_active)
            VALUES (:id, :tid, 'provider', NULL, :dow, :start, :end, :slot, :max, TRUE)
        """), {
            "id": new_id, "tid": str(tid),
            "dow": dow,
            "start": defn["start_time"],
            "end": defn["end_time"],
            "slot": defn["slot_duration_minutes"],
            "max": 5,
        })
        created_ids.append(new_id)

    await db.commit()
    return ok({"preset_key": preset_key, "status": "applied", "rule_count": len(created_ids)}, request_id=rid)


@router.delete("/availability/preset/{preset_key}", status_code=200, dependencies=[Depends(enforce_setup_sequence)])
async def delete_availability_preset(
    preset_key: str, request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_owner_mutation),
):
    """Delete all rules that match the given preset pattern for this tenant."""
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    defn = _PRESET_DEFS.get(preset_key)
    if not defn:
        raise HTTPException(400, f"Unknown preset key: {preset_key!r}")

    result = await db.execute(text("""
        DELETE FROM provider_availability_rules
        WHERE tenant_id=:tid
          AND scope_type='provider'
          AND scope_id IS NULL
          AND start_time=:start
          AND end_time=:end
          AND slot_duration_minutes=:slot
        RETURNING id
    """), {"tid": str(tid), "start": defn["start_time"], "end": defn["end_time"], "slot": defn["slot_duration_minutes"]})
    deleted_ids = [str(r[0]) for r in result.fetchall()]
    await db.commit()
    return ok({"preset_key": preset_key, "deleted_count": len(deleted_ids), "deleted_ids": deleted_ids}, request_id=rid)


# ── Offerings ─────────────────────────────────────────────────────────────────

@router.get("/offerings/available")
async def list_available_offerings(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    # NOTE (Tenant My Offerings enterprise upgrade): this previously queried
    # `master_offerings`, a table that has zero rows in the live database —
    # every tenant saw "0 available offerings" regardless of the real,
    # populated platform catalog. The real, live catalog lives in
    # `master_services` (joined to `service_categories` for vertical scoping,
    # `service_groups` for display grouping). Fixed to query the real table.
    # See TENANT_MY_OFFERINGS_CATALOG_DIAGNOSTIC_REPORT.md.
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    result = await db.execute(text("""
        SELECT
            ms.id AS offering_id,
            ms.service_name AS name,
            ms.slug AS slug,
            ms.job_type AS offering_type,
            ms.pricing_model AS pricing_model,
            ms.category_id AS category_id,
            ms.service_group_id AS service_group_id,
            sg.name AS service_group_name,
            ms.is_type_required AS requires_service_type,
            ms.is_brand_required AS requires_brand,
            true AS requires_staff,
            COALESCE(ms.requires_schedule, false) AS requires_slot,
            ms.base_price AS admin_price,
            ms.visit_fee AS admin_visit_fee,
            NULL::numeric AS admin_appointment_fee,
            NULL::numeric AS admin_lead_fee,
            NULL::text AS primary_engine_key,
            NULL::text AS customer_flow_type,
            COALESCE(canonical.id, peo.id) AS provider_enabled_offering_id,
            COALESCE(canonical.is_enabled, peo.is_enabled, false) AS is_already_enabled,
            ms.job_type_id AS job_type_id
        FROM master_services ms
        JOIN service_categories sc ON sc.id = ms.category_id
        JOIN tenants t ON t.id = :tid
        LEFT JOIN service_groups sg ON sg.id = ms.service_group_id
        LEFT JOIN LATERAL (
            SELECT ts.id, ts.is_enabled
            FROM tenant_services ts
            WHERE ts.master_service_id = ms.id AND ts.tenant_id = :tid
              AND ts.deleted_at IS NULL
            ORDER BY ts.is_enabled DESC, ts.created_at
            LIMIT 1
        ) canonical ON true
        LEFT JOIN provider_enabled_offerings peo
            ON peo.offering_id = ms.id AND peo.tenant_id = :tid AND peo.deleted_at IS NULL
        WHERE ms.is_active = true AND ms.deleted_at IS NULL
          AND sc.is_active = true AND sc.is_provider_registerable = true
          AND sc.vertical_type = t.vertical
        ORDER BY ms.display_order, ms.service_name
    """), {"tid": str(tid)})
    rows = [dict(r._mapping) for r in result.fetchall()]
    return ok({"offerings": rows, "count": len(rows)}, request_id=rid)


async def _canonical_enabled_offering_rows(
    db: AsyncSession,
    tid: uuid.UUID,
    tenant_service_id: uuid.UUID | None = None,
) -> list[dict]:
    """Project canonical tenant setup into the older offering API contract.

    The Home Services wizard writes ``tenant_services``.  The provider and
    admin offering consoles historically read ``provider_enabled_offerings``,
    which is empty in the live system.  This adapter keeps those screens on
    the same source of truth used by setup, matching and booking.
    """
    params = {"tid": str(tid)}
    id_filter = ""
    if tenant_service_id is not None:
        params["service_id"] = str(tenant_service_id)
        id_filter = " AND ts.id=:service_id"
    result = await db.execute(text(f"""
        SELECT
            ts.id AS provider_enabled_offering_id,
            ts.master_service_id AS offering_id,
            COALESCE(ts.tenant_display_name, ms.service_name) AS offering_name,
            ts.job_type AS offering_type,
            CASE
                WHEN ts.admin_suspended_at IS NOT NULL THEN 'suspended'
                WHEN NOT ts.is_enabled OR NOT ts.is_active THEN 'inactive'
                WHEN ts.setup_status='published' THEN 'active'
                ELSE 'draft'
            END AS status,
            ts.tenant_display_name AS provider_display_name,
            ts.tenant_description AS provider_description,
            COALESCE((
                SELECT jsonb_agg(DISTINCT tst.service_type_id::text)
                FROM tenant_service_types tst
                WHERE tst.tenant_service_id=ts.id AND tst.is_enabled=true
            ), '[]'::jsonb) AS supported_type_ids,
            COALESCE((
                SELECT jsonb_agg(DISTINCT tsb.brand_id::text)
                FROM tenant_service_brands tsb
                WHERE tsb.tenant_service_id=ts.id AND tsb.is_enabled=true
            ), '[]'::jsonb) AS supported_brand_ids,
            (ts.tenant_emergency_surcharge IS NOT NULL) AS supports_emergency,
            ts.tenant_base_price AS provider_price_override,
            ts.tenant_min_price AS provider_min_price,
            ts.tenant_max_price AS provider_max_price,
            ts.tenant_visit_fee AS provider_visit_fee,
            NULL::numeric AS provider_appointment_fee,
            NULL::numeric AS provider_lead_fee,
            ts.published_at AS activated_at,
            ts.admin_suspended_at AS suspended_at,
            ts.admin_suspension_reason AS suspension_reason,
            ts.is_enabled,
            ts.is_active,
            ts.created_at,
            ts.updated_at
        FROM tenant_services ts
        JOIN master_services ms ON ms.id=ts.master_service_id
        WHERE ts.tenant_id=:tid AND ts.deleted_at IS NULL{id_filter}
        ORDER BY ms.display_order, ms.service_name, ts.created_at
    """), params)
    rows = result.fetchall()

    provider = await _evaluate_provider_bookability(db, tid)
    coverage = {
        str(item["offering_id"]): int(item["ready_technician_count"])
        for item in provider["service_coverage"]
    }
    projected: list[dict] = []
    for row in rows:
        item = dict(row._mapping)
        item_id = str(item["provider_enabled_offering_id"])
        blockers: list[dict] = []
        if item["status"] == "suspended":
            blockers.append({
                "code": "OFFERING_SUSPENDED",
                "message": item["suspension_reason"] or "This service is suspended by the platform administrator.",
                "route": "/support",
            })
        elif item["status"] == "inactive":
            blockers.append({
                "code": "OFFERING_INACTIVE",
                "message": "Activate this service before it can receive bookings.",
                "route": "/tenant/home-services/setup/services-pricing",
            })
        elif item["status"] == "draft":
            blockers.append({
                "code": "OFFERING_NOT_PUBLISHED",
                "message": "Complete and publish this service setup before it can receive bookings.",
                "route": "/tenant/home-services/setup/services-pricing",
            })
        else:
            blockers.extend(dict(value) for value in provider["bookability_blockers"])
            if coverage.get(item_id, 0) <= 0 and not any(
                value.get("code") == "READY_TECHNICIAN_MISSING" for value in blockers
            ):
                blockers.append({
                    "code": "READY_TECHNICIAN_MISSING",
                    "message": "Assign a fully ready technician to this service.",
                    "route": "/business/team",
                })
        item["readiness_blockers"] = blockers
        item["readiness_status"] = "ready" if not blockers else "not_ready"
        projected.append(item)
    return projected


@router.get("/offerings/enabled")
async def list_enabled_offerings(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    rows = await _canonical_enabled_offering_rows(db, tid)
    return ok({"offerings": rows, "count": len(rows)}, request_id=rid)


@router.post("/offerings/enabled", status_code=201, dependencies=[Depends(enforce_setup_sequence)])
async def enable_offering(
    payload: dict, request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_owner_mutation),
):
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    from app.engines.admin_catalog.tenant_service import TenantCatalogService

    service = TenantCatalogService(
        db=db, request_id=rid,
        actor_id=uuid.UUID(user.user_id) if user.user_id else None,
        actor_role=user.role, actor_tenant_id=tid,
    )
    created = await service.enable_service({
        "master_service_id": payload.get("offering_id"),
        "job_type_id": payload.get("job_type_id"),
        "tenant_display_name": payload.get("provider_display_name"),
        "tenant_description": payload.get("provider_description"),
        "tenant_base_price": payload.get("provider_price_override"),
        "tenant_min_price": payload.get("provider_min_price"),
        "tenant_max_price": payload.get("provider_max_price"),
        "tenant_visit_fee": payload.get("provider_visit_fee"),
    }, tid)
    service_id = uuid.UUID(created["id"])
    if payload.get("supported_type_ids") is not None:
        await service.set_tenant_service_types(service_id, payload["supported_type_ids"])
    if payload.get("supported_brand_ids") is not None:
        await service.set_tenant_service_brands(service_id, payload["supported_brand_ids"])
    if "supports_emergency" in payload:
        await service.update_enabled_service(service_id, {
            "tenant_emergency_surcharge": 0 if payload.get("supports_emergency") else None,
        })
    if payload.get("activate_if_ready"):
        await service.publish_service(service_id)
    await db.commit()
    rows = await _canonical_enabled_offering_rows(db, tid, service_id)
    return ok(rows[0], request_id=rid)


@router.get("/offerings/enabled/{offering_id}")
async def get_enabled_offering(
    offering_id: uuid.UUID, request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    rows = await _canonical_enabled_offering_rows(db, tid, offering_id)
    if not rows:
        raise HTTPException(404, "Offering not found")
    return ok(rows[0], request_id=rid)


@router.put("/offerings/enabled/{offering_id}", dependencies=[Depends(enforce_setup_sequence)])
async def update_enabled_offering(
    offering_id: uuid.UUID, payload: dict, request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_owner_mutation),
):
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    from app.engines.admin_catalog.tenant_service import TenantCatalogService

    service = TenantCatalogService(
        db=db, request_id=rid,
        actor_id=uuid.UUID(user.user_id) if user.user_id else None,
        actor_role=user.role, actor_tenant_id=tid,
    )
    mapped = {
        target: payload[source]
        for source, target in {
            "provider_display_name": "tenant_display_name",
            "provider_description": "tenant_description",
            "provider_price_override": "tenant_base_price",
            "provider_min_price": "tenant_min_price",
            "provider_max_price": "tenant_max_price",
            "provider_visit_fee": "tenant_visit_fee",
        }.items()
        if source in payload
    }
    if "supports_emergency" in payload:
        mapped["tenant_emergency_surcharge"] = 0 if payload.get("supports_emergency") else None
    await service.update_enabled_service(offering_id, mapped)
    if payload.get("supported_type_ids") is not None:
        await service.set_tenant_service_types(offering_id, payload["supported_type_ids"])
    if payload.get("supported_brand_ids") is not None:
        await service.set_tenant_service_brands(offering_id, payload["supported_brand_ids"])
    if payload.get("activate_if_ready"):
        await service.publish_service(offering_id)
    await db.commit()
    rows = await _canonical_enabled_offering_rows(db, tid, offering_id)
    return ok(rows[0], request_id=rid)


@router.post("/offerings/enabled/{offering_id}/activate", dependencies=[Depends(enforce_setup_sequence)])
async def activate_offering(
    offering_id: uuid.UUID, request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_owner_mutation),
):
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    from app.engines.admin_catalog.tenant_service import TenantCatalogService
    service = TenantCatalogService(
        db=db, request_id=rid,
        actor_id=uuid.UUID(user.user_id) if user.user_id else None,
        actor_role=user.role, actor_tenant_id=tid,
    )
    updated = await db.execute(text(
        "UPDATE tenant_services SET is_enabled=true, is_active=true, updated_at=now() "
        "WHERE id=:id AND tenant_id=:tid AND deleted_at IS NULL RETURNING id"
    ), {"id": str(offering_id), "tid": str(tid)})
    if updated.fetchone() is None:
        raise HTTPException(404, "Offering not found")
    await service.publish_service(offering_id)
    await db.commit()
    rows = await _canonical_enabled_offering_rows(db, tid, offering_id)
    return ok(rows[0], request_id=rid)


@router.post("/offerings/enabled/{offering_id}/deactivate", dependencies=[Depends(enforce_setup_sequence)])
async def deactivate_offering(
    offering_id: uuid.UUID, request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_owner_mutation),
):
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    updated = await db.execute(text(
        "UPDATE tenant_services SET is_enabled=false, updated_at=now() "
        "WHERE id=:id AND tenant_id=:tid AND deleted_at IS NULL RETURNING id"
    ), {"id": str(offering_id), "tid": str(tid)})
    if updated.fetchone() is None:
        raise HTTPException(404, "Offering not found")
    await db.commit()
    rows = await _canonical_enabled_offering_rows(db, tid, offering_id)
    return ok(rows[0], request_id=rid)


@router.post("/offerings/enabled/{offering_id}/refresh-readiness", dependencies=[Depends(enforce_setup_sequence)])
async def refresh_offering_readiness(
    offering_id: uuid.UUID, request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_owner_mutation),
):
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    rows = await _canonical_enabled_offering_rows(db, tid, offering_id)
    if not rows:
        raise HTTPException(404, "Offering not found")
    return ok(rows[0], request_id=rid)


# ── Provider Status (Sprint 12) ────────────────────────────────────────────────

@router.get("/status")
async def get_provider_status(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    row = await db.execute(text("SELECT * FROM provider_visibility_statuses WHERE tenant_id=:tid ORDER BY created_at DESC LIMIT 1"), {"tid": str(tid)})
    r = row.fetchone()
    if r:
        data = dict(r._mapping)
    else:
        data = {
            "tenant_id": str(tid), "category_id": None,
            "is_visible": False, "is_bookable": False,
            "visibility_blockers": [], "bookability_blockers": [],
            "override_is_visible": None, "override_is_bookable": None,
            "last_evaluated_at": None,
        }
    return ok(data, request_id=rid)


async def _evaluate_provider_bookability(db: AsyncSession, tid: uuid.UUID) -> dict:
    """HS4B — real bookability/visibility computation, replacing the
    previous no-op stub. Reads real signals from tenants, tenant_billing,
    tenant_limits, tenant_service_areas, provider_availability_rules, and
    tenant_services — no fabricated/mocked status.

    Policy (documented per HS4B ticket requirement — "document final
    policy clearly"):
      is_bookable requires ALL critical checks to pass: tenant not
      suspended/rejected, at least one published service with a
      configured provider price range, at least one active service area,
      at least one availability rule, sufficient usage credits, and at
      least one ready technician who covers every published offering.
      is_visible is a lighter bar: tenant not suspended/rejected, business
      profile complete, and at least one service published — a tenant can
      be visible (discoverable) before being fully bookable.
    """
    tenant_row = (await db.execute(
        text("SELECT status, verification_status, suspended_at, business_name, "
             "address_line1, city, vertical, business_type, country "
             "FROM tenants WHERE id=:tid"),
        {"tid": str(tid)},
    )).fetchone()

    passed: list[str] = []
    visibility_blockers: list[dict] = []
    bookability_blockers: list[dict] = []

    tenant_active = bool(tenant_row) and tenant_row.status == "active" \
        and tenant_row.verification_status in ("approved", "verified") \
        and tenant_row.suspended_at is None
    if tenant_active:
        passed.append("tenant_active_not_suspended")
    else:
        reason = {"code": "TENANT_SUSPENDED_OR_REJECTED",
                  "message": "Your account is suspended or not approved yet.",
                  "severity": "critical", "route": "/support"}
        visibility_blockers.append(reason)
        bookability_blockers.append(reason)

    profile_complete = bool(tenant_row) and bool(tenant_row.business_name) \
        and bool(tenant_row.address_line1) and bool(tenant_row.city)
    if profile_complete:
        passed.append("business_profile_complete")
    else:
        visibility_blockers.append({
            "code": "BUSINESS_PROFILE_INCOMPLETE",
            "message": "Complete your business profile (name, address, city).",
            "severity": "critical", "route": "/profile"})

    # Required business-document state is part of the same bookability
      # decision as pricing, coverage, capacity, and credits. The
    # previous implementation omitted it, so a provider could remain
    # customer-bookable after a required document was rejected or expired.
    # A replacement that is under review (or has changes requested) keeps
    # the previous valid version's grace period and therefore does not block.
    from app.engines.tenant_engine.models import TenantDocument
    from app.engines.vertical_catalog.document_requirements import resolve_requirements

    required_document_types = {
        item["key"] for item in resolve_requirements(
            vertical=(tenant_row.vertical if tenant_row else "home_services"),
            business_type=(tenant_row.business_type if tenant_row else None),
            country=(tenant_row.country if tenant_row else "India"),
        ) if item["required"]
    }
    relevant_documents = (await db.execute(
        select(TenantDocument).where(
            TenantDocument.tenant_id == tid,
            TenantDocument.staff_member_id.is_(None),
            TenantDocument.doc_type.in_(required_document_types),
        )
    )).scalars().all()
    documents_by_type = {
        document.doc_type: document
        for document in relevant_documents
        if document.is_current
    }
    document_blockers: list[str] = []
    now = datetime.now(timezone.utc)
    for document_type in sorted(required_document_types):
        document = documents_by_type.get(document_type)
        if document is None:
            document_blockers.append(document_type)
            continue
        expired = bool(document.expiry_date and document.expiry_date < now)
        current_verified = document.status == "verified" and not expired
        # A pending replacement may use a still-valid previously verified
        # version. A first-ever pending upload has no such grace and cannot
        # make an unverified provider customer-bookable.
        valid_previous = any(
            candidate.doc_type == document_type
            and not candidate.is_current
            and candidate.status == "verified"
            and (candidate.expiry_date is None or candidate.expiry_date >= now)
            for candidate in relevant_documents
        )
        replacement_in_review = document.status in ("pending_review", "changes_requested")
        if not current_verified and not (replacement_in_review and valid_previous):
            document_blockers.append(document_type)

    if not document_blockers:
        passed.append("required_documents_current")
    else:
        bookability_blockers.append({
            "code": "REQUIRED_DOCUMENT_ACTION_NEEDED",
            "message": "Upload or replace every required business document before receiving new bookings.",
            "severity": "critical",
            "route": "/business/verification-documents",
            "document_types": document_blockers,
        })

    published_count = (await db.execute(
        text("SELECT count(*) FROM tenant_services WHERE tenant_id=:tid "
             "AND setup_status='published' AND is_enabled=true AND is_active=true AND deleted_at IS NULL"),
        {"tid": str(tid)},
    )).scalar() or 0
    if published_count > 0:
        passed.append("service_setup_published")
    else:
        reason = {"code": "NO_PUBLISHED_SERVICE",
                  "message": "Publish at least one service before you can be booked.",
                  "severity": "critical", "route": "/tenant/home-services/setup/services-pricing"}
        visibility_blockers.append(reason)
        bookability_blockers.append(reason)

    # Share the provider-owned pricing check with onboarding and activation:
    # default/dimension amounts, inspection fee, or the shared consultation fee.
    priced_count = (await db.execute(
        text(PUBLISHED_PRICED_SERVICES_SQL),
        {"tid": str(tid)},
    )).scalar() or 0
    if priced_count > 0:
        passed.append("provider_price_range_configured")
    else:
        bookability_blockers.append({
            "code": "PROVIDER_PRICE_RANGE_MISSING",
            "message": "Set your provider price range for at least one published service.",
            "severity": "critical", "route": "/tenant/home-services/setup/services-pricing"})

    active_areas = (await db.execute(
        text("SELECT count(*) FROM tenant_service_areas WHERE tenant_id=:tid AND is_active=true"),
        {"tid": str(tid)},
    )).scalar() or 0
    if active_areas > 0:
        passed.append("service_area_configured")
    else:
        bookability_blockers.append({
            "code": "SERVICE_AREA_MISSING",
            "message": "Add at least one active service area before receiving bookings.",
            "severity": "critical", "route": "/business/coverage-hours"})

    availability_count = (await db.execute(
        text("SELECT count(*) FROM provider_availability_rules WHERE tenant_id=:tid AND is_active=true"),
        {"tid": str(tid)},
    )).scalar() or 0
    if availability_count > 0:
        passed.append("availability_configured")
    else:
        bookability_blockers.append({
            "code": "AVAILABILITY_MISSING",
            "message": "Set at least one open availability slot to receive bookings.",
            "severity": "critical", "route": "/home-services/availability"})

    # Business approval is intentionally allowed before an optional seat
    # top-up, but customer bookability must still fail closed until every
    # enabled offering has a genuinely ready technician.  Matching already
    # enforces this per request; exposing the same truth here prevents the
    # dashboard from claiming that an unstaffed provider is bookable.
    from app.engines.home_service_assignment.team_readiness_service import (
        compute_service_coverage,
        compute_team_summary,
    )
    team_summary = await compute_team_summary(db, tid)
    service_coverage = await compute_service_coverage(db, tid, team_summary)
    staff_capacity_ready = bool(service_coverage) and all(
        row["ready_technician_count"] > 0 for row in service_coverage
    )
    if staff_capacity_ready:
        passed.append("ready_technician_capacity")
    else:
        bookability_blockers.append({
            "code": "READY_TECHNICIAN_MISSING",
            "message": "Complete a technician's service assignments and availability before receiving bookings.",
            "severity": "critical", "route": "/business/team"})

    # Approval and setup do not require payment, but bookable capacity must be
    # backed by a live seat entitlement.  The roster can contain pre-created
    # technicians while the provider decides on a plan; it must never turn
    # those unpaid rows into customer-facing capacity.
    from app.engines.vertical_catalog.seat_enforcement import get_seat_usage

    seat_usage = await get_seat_usage(db, tid)
    seat_capacity_ready = (
        seat_usage["entitled_seats"] > 0 and not seat_usage["over_limit"]
    )
    if seat_capacity_ready:
        passed.append("technician_seats_funded")
    else:
        bookability_blockers.append({
            "code": "TECHNICIAN_SEATS_REQUIRED",
            "message": (
                "Buy technician seats or deactivate technicians above your live seat limit "
                "before receiving bookings."
            ),
            "severity": "critical",
            "route": "/home-services/finance?tab=topups",
            "seat_usage": seat_usage,
        })

    # `security_deposit_paid` / `security_deposit_amount` were dropped with the
    # deposit (migration 317/318). Selecting them raised UndefinedColumnError,
    # so recomputing bookability 500'd and a provider's visible/bookable state
    # was frozen at whatever had last been stored.
    billing_row = (await db.execute(
        text("SELECT credit_balance FROM tenant_billing WHERE tenant_id=:tid"),
        {"tid": str(tid)},
    )).fetchone()
    credit_balance = float(billing_row.credit_balance) if billing_row and billing_row.credit_balance is not None else 0.0
    if credit_balance > 0:
        passed.append("usage_credits_available")
    else:
        bookability_blockers.append({
            "code": "USAGE_CREDITS_INSUFFICIENT",
            "message": "Add usage credits to your account to receive bookings.",
            "severity": "critical", "route": "/home-services/finance?tab=usage-credits"})

    is_visible = tenant_active and profile_complete and published_count > 0
    is_bookable = is_visible and priced_count > 0 and active_areas > 0 \
        and availability_count > 0 and credit_balance > 0 \
        and staff_capacity_ready and seat_capacity_ready and not document_blockers

    status_label = "bookable" if is_bookable else ("visible_not_bookable" if is_visible else "not_visible")

    return {
        "is_visible": is_visible, "is_bookable": is_bookable,
        "status": status_label,
        "passed_checks": passed,
        "visibility_blockers": visibility_blockers,
        "bookability_blockers": bookability_blockers,
        # Reused by the per-service status projection so it cannot drift from
        # the provider-level decision.
        "service_coverage": service_coverage,
    }


@router.post("/status/refresh")
async def refresh_provider_status(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_owner_mutation),
):
    """HS4B fix — real computation replacing the previous no-op stub.
    Computes bookability/visibility from real tenant setup data and
    persists the result to provider_visibility_statuses (upsert)."""
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))

    result = await _evaluate_provider_bookability(db, tid)

    existing = (await db.execute(
        text("SELECT id FROM provider_visibility_statuses WHERE tenant_id=:tid ORDER BY created_at DESC LIMIT 1"),
        {"tid": str(tid)},
    )).fetchone()
    if existing:
        await db.execute(text(
            "UPDATE provider_visibility_statuses SET is_visible=:iv, is_bookable=:ib, "
            "visibility_blockers=CAST(:vb AS jsonb), bookability_blockers=CAST(:bb AS jsonb), "
            "last_evaluated_at=now(), last_changed_at=now(), updated_at=now() WHERE id=:id"
        ), {"iv": result["is_visible"], "ib": result["is_bookable"],
            "vb": json.dumps(result["visibility_blockers"]), "bb": json.dumps(result["bookability_blockers"]),
            "id": existing.id})
    else:
        await db.execute(text(
            "INSERT INTO provider_visibility_statuses "
            "(tenant_id, is_visible, is_bookable, visibility_blockers, bookability_blockers, last_evaluated_at, last_changed_at) "
            "VALUES (:tid, :iv, :ib, CAST(:vb AS jsonb), CAST(:bb AS jsonb), now(), now())"
        ), {"tid": str(tid), "iv": result["is_visible"], "ib": result["is_bookable"],
            "vb": json.dumps(result["visibility_blockers"]), "bb": json.dumps(result["bookability_blockers"])})
    await db.commit()

    row = (await db.execute(
        text("SELECT * FROM provider_visibility_statuses WHERE tenant_id=:tid ORDER BY created_at DESC LIMIT 1"),
        {"tid": str(tid)},
    )).fetchone()
    data = dict(row._mapping)
    data["status"] = result["status"]
    data["passed_checks"] = result["passed_checks"]
    data["failed_checks"] = result["bookability_blockers"]
    data["warnings"] = []
    return ok(data, request_id=rid)


# ── Matching Input Readiness (HS5B) ───────────────────────────────────────────
# Not the real provider-matching engine (that's HS6 scope) — this is a
# read-only preview showing whether the tenant's Home Services setup data
# (area coverage, availability, breaks, exceptions, booking window,
# bookability) is internally consistent for a hypothetical customer
# request. HS6 is expected to consume the same underlying tables.

async def get_tenant_home_services_matching_inputs(
    db: AsyncSession, tenant_id: uuid.UUID,
    service_id: uuid.UUID | None, service_type_id: uuid.UUID | None, brand_id: uuid.UUID | None,
    zipcode: str | None, requested_at: str | None,
) -> dict:
    blocking_reasons: list[dict] = []

    # zipcode coverage — any active service area whose zipcode list (comma-
    # separated per the existing tenant_service_areas convention) contains it
    zipcode_covered = True
    if zipcode:
        row = (await db.execute(
            text("SELECT count(*) FROM tenant_service_areas WHERE tenant_id=:tid AND is_active=true AND zipcode=:zip"),
            {"tid": str(tenant_id), "zip": zipcode})).scalar() or 0
        zipcode_covered = row > 0
        if not zipcode_covered:
            blocking_reasons.append({"code": "ZIPCODE_NOT_COVERED", "message": "This zipcode is not in any active service area."})

    # service/type/brand coverage — tenant_service_area_services, scoped by
    # area if we know it's covered; otherwise checked platform-wide for this tenant
    service_covered = True
    type_covered = True
    brand_covered = True
    if service_id:
        svc_row = (await db.execute(
            text("SELECT count(*) FROM tenant_service_area_services tsas "
                 "JOIN tenant_service_areas tsa ON tsa.id = tsas.tenant_service_area_id "
                 "WHERE tsas.tenant_id=:tid AND tsas.service_id=:sid AND tsas.is_available=true AND tsa.is_active=true"),
            {"tid": str(tenant_id), "sid": str(service_id)})).scalar() or 0
        service_covered = svc_row > 0
        if not service_covered:
            blocking_reasons.append({"code": "SERVICE_NOT_COVERED_IN_AREA", "message": "This service is not covered in your active service areas."})

        if service_type_id:
            type_row = (await db.execute(
                text("SELECT count(*) FROM tenant_service_area_services tsas "
                     "JOIN tenant_service_areas tsa ON tsa.id = tsas.tenant_service_area_id "
                     "WHERE tsas.tenant_id=:tid AND tsas.service_id=:sid AND tsas.service_type_id=:stid "
                     "AND tsas.is_available=true AND tsa.is_active=true"),
                {"tid": str(tenant_id), "sid": str(service_id), "stid": str(service_type_id)})).scalar() or 0
            type_covered = type_row > 0
            if not type_covered:
                blocking_reasons.append({"code": "TYPE_NOT_COVERED_IN_AREA", "message": "This service type is not covered in your active service areas."})

        if brand_id:
            brand_row = (await db.execute(
                text("SELECT count(*) FROM tenant_service_area_services tsas "
                     "JOIN tenant_service_areas tsa ON tsa.id = tsas.tenant_service_area_id "
                     "WHERE tsas.tenant_id=:tid AND tsas.service_id=:sid AND tsas.brand_id=:bid "
                     "AND tsas.is_available=true AND tsa.is_active=true"),
                {"tid": str(tenant_id), "sid": str(service_id), "bid": str(brand_id)})).scalar() or 0
            brand_covered = brand_row > 0
            if not brand_covered:
                blocking_reasons.append({"code": "BRAND_NOT_COVERED_IN_AREA", "message": "This brand is not covered in your active service areas."})

    # availability at requested time (day_of_week + time-of-day window)
    available_at_requested_time = True
    blocked_by_break = False
    blocked_by_exception = False
    requested_date = requested_time = None
    if requested_at:
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(requested_at.replace("Z", "+00:00"))
            requested_date = dt.date().isoformat()
            requested_time = dt.strftime("%H:%M")
            dow = dt.isoweekday() % 7  # match provider_availability_rules' 0=Sunday convention
        except ValueError:
            dow = None

        if dow is not None:
            rule = (await db.execute(
                text("SELECT * FROM provider_availability_rules WHERE tenant_id=:tid AND day_of_week=:dow AND is_active=true LIMIT 1"),
                {"tid": str(tenant_id), "dow": dow})).fetchone()
            if not rule:
                available_at_requested_time = False
                blocking_reasons.append({"code": "NOT_AN_OPEN_DAY", "message": "You are not open on this day."})
            elif not (rule.start_time <= requested_time <= rule.end_time):
                available_at_requested_time = False
                blocking_reasons.append({"code": "OUTSIDE_WORKING_HOURS", "message": "Requested time is outside working hours."})
            elif rule.break_start_time and rule.break_end_time and rule.break_start_time <= requested_time <= rule.break_end_time:
                blocked_by_break = True
                available_at_requested_time = False
                blocking_reasons.append({"code": "BLOCKED_BY_BREAK", "message": "Requested time falls inside your break."})

        if requested_date:
            exc = (await db.execute(
                text("SELECT * FROM tenant_availability_exceptions WHERE tenant_id=:tid AND date=:date AND status='active' LIMIT 1"),
                {"tid": str(tenant_id), "date": _parse_date(requested_date)})).fetchone()
            if exc:
                if exc.full_day_closed or (exc.start_time and exc.end_time and exc.start_time <= requested_time <= exc.end_time):
                    blocked_by_exception = True
                    available_at_requested_time = False
                    blocking_reasons.append({"code": "BLOCKED_BY_EXCEPTION", "message": f"You are closed on this date: {exc.reason}"})

    # booking window
    booking_window_valid = True
    bw = (await db.execute(
        text("SELECT * FROM tenant_booking_window_settings WHERE tenant_id=:tid"), {"tid": str(tenant_id)})).fetchone()
    if requested_at and bw:
        try:
            from datetime import datetime, timezone as dt_timezone
            dt = datetime.fromisoformat(requested_at.replace("Z", "+00:00"))
            now = datetime.now(dt_timezone.utc)
            minutes_notice = (dt - now).total_seconds() / 60
            if minutes_notice < bw.minimum_notice_minutes:
                booking_window_valid = False
                blocking_reasons.append({"code": "BELOW_MINIMUM_NOTICE", "message": "Requested time is inside the minimum notice window."})
            if minutes_notice > bw.maximum_advance_booking_days * 24 * 60:
                booking_window_valid = False
                blocking_reasons.append({"code": "BEYOND_ADVANCE_BOOKING_WINDOW", "message": "Requested time is beyond the maximum advance booking window."})
        except ValueError:
            pass

    # bookability (HS4B)
    bookability = await _evaluate_provider_bookability(db, tenant_id)

    is_bookable = (
        zipcode_covered and service_covered and type_covered and brand_covered
        and available_at_requested_time and booking_window_valid and bookability["is_bookable"]
    )
    all_reasons = blocking_reasons + bookability["bookability_blockers"]

    return {
        "tenant_id": str(tenant_id),
        "zipcode_covered": zipcode_covered,
        "service_covered": service_covered,
        "type_covered": type_covered,
        "brand_covered": brand_covered,
        "available_at_requested_time": available_at_requested_time,
        "blocked_by_break": blocked_by_break,
        "blocked_by_exception": blocked_by_exception,
        "booking_window_valid": booking_window_valid,
        "is_bookable": is_bookable,
        "blocking_reasons": all_reasons,
    }


@router.post("/home-services/matching-inputs/preview")
async def preview_matching_inputs(
    payload: dict, request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    result = await get_tenant_home_services_matching_inputs(
        db, tid,
        service_id=uuid.UUID(payload["service_id"]) if payload.get("service_id") else None,
        service_type_id=uuid.UUID(payload["service_type_id"]) if payload.get("service_type_id") else None,
        brand_id=uuid.UUID(payload["brand_id"]) if payload.get("brand_id") else None,
        zipcode=payload.get("zipcode"),
        requested_at=payload.get("requested_at"),
    )
    return ok(result, request_id=rid)


@router.get("/status/offerings")
async def get_offering_statuses(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    # The legacy status table is not populated by the canonical Home Services
    # setup flow. Project each published TenantService from the same live
    # provider/team checks used by matching instead of returning a false zero.
    provider = await _evaluate_provider_bookability(db, tid)
    coverage_by_service = {
        str(row["offering_id"]): int(row["ready_technician_count"])
        for row in provider["service_coverage"]
    }
    service_rows = (await db.execute(text(
        "SELECT ts.id::text AS tenant_service_id, "
        "       ts.master_service_id::text AS master_service_id "
        "FROM tenant_services ts "
        "WHERE ts.tenant_id=:tid AND ts.is_enabled=true AND ts.is_active=true "
        "  AND ts.setup_status='published' AND ts.deleted_at IS NULL "
        "ORDER BY ts.created_at, ts.id"
    ), {"tid": str(tid)})).fetchall()

    evaluated_at = datetime.now(timezone.utc)
    statuses: list[dict] = []
    for service in service_rows:
        tenant_service_id = str(service.tenant_service_id)
        blockers = [dict(item) for item in provider["bookability_blockers"]]
        ready_count = coverage_by_service.get(tenant_service_id, 0)
        if ready_count <= 0 and not any(
            item.get("code") == "READY_TECHNICIAN_MISSING" for item in blockers
        ):
            blockers.append({
                "code": "READY_TECHNICIAN_MISSING",
                "message": "Assign a fully ready technician to this service.",
                "severity": "critical",
                "route": "/business/team",
            })
        statuses.append({
            "id": tenant_service_id,
            "tenant_id": str(tid),
            "provider_enabled_offering_id": tenant_service_id,
            "offering_id": str(service.master_service_id),
            "is_bookable": bool(provider["is_bookable"] and ready_count > 0),
            "blockers": blockers,
            "last_evaluated_at": evaluated_at,
        })
    return ok({"statuses": statuses, "count": len(statuses)}, request_id=rid)


# ── Onboarding Status (Sprint 10) ─────────────────────────────────────────────

async def _build_live_provider_onboarding(db: AsyncSession, tid: uuid.UUID) -> dict:
    """Project the canonical operational gates as provider onboarding."""
    provider = await _evaluate_provider_bookability(db, tid)
    passed = set(provider["passed_checks"])
    category = (await db.execute(text("""
        SELECT sc.id, sc.name, sc.vertical_type
        FROM tenant_services ts
        JOIN service_categories sc ON sc.id=ts.category_id
        WHERE ts.tenant_id=:tid AND ts.deleted_at IS NULL
        ORDER BY ts.created_at LIMIT 1
    """), {"tid": str(tid)})).fetchone()
    definitions = [
        ("business_approved", "Business approved", "provider_verification",
         "tenant_active_not_suspended", "/onboarding/application-status",
         "Your business must be approved and active."),
        ("business_profile", "Business profile complete", "provider_profile",
         "business_profile_complete", "/profile",
         "Add your business name and complete address."),
        ("business_documents", "Business documents verified", "provider_verification",
         "required_documents_current", "/business/verification-documents",
         "Upload valid required business documents."),
        ("services_published", "Services published", "provider_enabled_offerings",
         "service_setup_published", "/tenant/home-services/setup/services-pricing",
         "Complete and publish at least one service."),
        ("pricing_ready", "Service pricing configured", "provider_enabled_offerings",
         "provider_price_range_configured", "/tenant/home-services/setup/services-pricing",
         "Configure an allowed provider price or visit fee."),
        ("service_area", "Service area configured", "provider_service_areas",
         "service_area_configured", "/business/coverage-hours",
         "Add at least one active service area."),
        ("availability", "Availability configured", "provider_appointment_slots",
         "availability_configured", "/home-services/availability",
         "Set at least one open availability period."),
          ("technician_ready", "Technician ready", "provider_staff",
           "ready_technician_capacity", "/business/team",
           "Complete a technician's login, role, service assignments, and availability."),
        ("technician_seats", "Technician seats funded", "provider_monetization",
         "technician_seats_funded", "/home-services/finance?tab=topups",
         "Buy enough live technician seats for the active roster."),
        ("usage_credits", "Usage credits available", "provider_monetization",
         "usage_credits_available", "/home-services/finance?tab=usage-credits",
         "Add usage credits before receiving bookings."),
    ]
    items: list[dict] = []
    for order, (key, title, source, check, route, blocked_reason) in enumerate(definitions, 1):
        completed = check in passed
        items.append({
            "id": key, "checklist_key": key, "title": title,
            "description": blocked_reason, "item_type": "system_check",
            "completion_source": source,
            "status": "completed" if completed else "blocked",
            "is_required": True, "is_blocking": not completed,
            "allows_admin_override": False,
            "provider_action_label": None if completed else "Fix now",
            "provider_action_route": None if completed else route,
            "blocked_reason": None if completed else blocked_reason,
            "completed_at": None, "display_order": order,
        })
    incomplete = [item for item in items if item["status"] != "completed"]
    completed_count = len(items) - len(incomplete)
    progress = round((completed_count / len(items)) * 100) if items else 0
    next_item = incomplete[0] if incomplete else None
    status = {
        "tenant_id": str(tid),
        "category_id": str(category.id) if category else None,
        "category_name": category.name if category else None,
        "category_type": category.vertical_type if category else None,
        "total_items": len(items), "required_items": len(items),
        "completed_items": completed_count, "pending_items": len(incomplete),
        "blocked_items": len(incomplete), "overridden_items": 0,
        "progress_percent": progress, "progress_percentage": progress,
        "onboarding_ready": not incomplete,
        "blockers": [{
            "code": item["checklist_key"].upper(),
            "message": item["blocked_reason"],
            "route": item["provider_action_route"],
        } for item in incomplete],
        "next_action": ({
            "title": next_item["title"],
            "description": next_item["blocked_reason"],
            "route": next_item["provider_action_route"],
            "action_label": "Fix now",
        } if next_item else None),
        "last_refreshed_at": datetime.now(timezone.utc),
    }
    return {"status": status, "items": items}


@router.get("/onboarding/status")
async def get_onboarding_status(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    live = await _build_live_provider_onboarding(db, tid)
    return ok(live["status"], request_id=rid)


@router.get("/onboarding/items")
async def get_onboarding_items(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    live = await _build_live_provider_onboarding(db, tid)
    return ok({"items": live["items"], "count": len(live["items"])}, request_id=rid)


@router.post("/onboarding/refresh")
async def refresh_onboarding(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_owner_mutation),
):
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    live = await _build_live_provider_onboarding(db, _tid(user))
    return ok(live["status"], request_id=rid)


# ── Packages Status (Sprint 9) ────────────────────────────────────────────────

# ── HS9 — Usage Credits (tenant-facing) ───────────────────────────────────────

@router.get("/usage-credits/balance")
async def get_usage_credit_balance(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    from app.engines.tenant_engine.models import TenantBilling
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    res = await db.execute(select(TenantBilling).where(TenantBilling.tenant_id == tid))
    billing = res.scalars().first()
    balance = float(billing.credit_balance) if billing else 0.0
    return ok({
        "tenant_id": str(tid),
        "usage_credit_balance": balance,
        "low_credit": balance < 20,
    }, request_id=rid)


@router.get("/usage-credits/ledger")
async def get_usage_credit_ledger(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    from app.engines.tenant_engine.models import UsageCreditLedger
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    res = await db.execute(
        select(UsageCreditLedger)
        .where(UsageCreditLedger.tenant_id == tid)
        .order_by(UsageCreditLedger.created_at.desc())
        .limit(200)
    )
    entries = [e.to_dict() for e in res.scalars().all()]
    return ok({"tenant_id": str(tid), "entries": entries, "count": len(entries)}, request_id=rid)
