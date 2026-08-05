"""Team member readiness + service-coverage calculation.

Single source of truth for "is this staff/technician ready" — consumed by
the tenant onboarding Staff & Technicians step (roster + coverage card) AND
implicitly proven correct by the same eligibility gate
home_service_assignment.service.list_eligible_staff_for_job uses at job-
assignment time, so readiness shown during onboarding cannot drift from
what actually gates a real assignment.
"""
from __future__ import annotations

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

TECHNICIAN_DESIGNATIONS = {"technician"}
VALID_MEMBER_TYPES = {"technician", "staff", "manager"}


async def compute_member_readiness(db: AsyncSession, tenant_id: uuid.UUID, member: dict) -> dict:
    """Returns {status, missing: [...]}. `status` is the single readiness
    value the roster/coverage card render — never a bare `active` boolean."""
    missing = []

    if member["status"] in ("inactive",):
        return {"status": "access_disabled", "missing": ["reactivate_access"]}
    if member.get("deleted_at"):
        return {"status": "offboarded", "missing": []}

    if not member.get("full_name") or not (member.get("phone") or member.get("email")):
        missing.append("identity")

    member_type = (member.get("member_type") or "").lower()
    if member_type not in VALID_MEMBER_TYPES:
        missing.append("role")

    is_technician = member_type in TECHNICIAN_DESIGNATIONS
    if is_technician:
        offering_ids = member.get("supported_offering_ids") or []
        valid_ids = await _validate_offering_ids(db, tenant_id, offering_ids)
        if not valid_ids:
            missing.append("service_assignment")

        has_availability = (await db.execute(text(
            "SELECT 1 FROM provider_availability_rules "
            "WHERE tenant_id=:tid AND scope_type='staff_member' AND scope_id=:sid AND is_active=true LIMIT 1"
        ), {"tid": str(tenant_id), "sid": member["id"]})).fetchone()
        if not has_availability:
            missing.append("availability")

    if member.get("user_id"):
        user_row = (await db.execute(text(
            "SELECT is_active FROM users WHERE id=:uid"
        ), {"uid": str(member["user_id"])})).fetchone()
        if user_row and not user_row.is_active:
            return {"status": "access_disabled", "missing": ["reactivate_access"]}
    elif member.get("email") or member.get("phone"):
        # Has contact info but no linked login yet and no login was ever
        # requested — not itself blocking (operational profile without
        # login access is explicitly allowed), so this alone is not "missing".
        pass

    if missing:
        # Report the first/most-fundamental gap as the headline status —
        # identity and role block everything else from being meaningful.
        order = ["identity", "role", "service_assignment", "availability"]
        headline = next((m for m in order if m in missing), missing[0])
        return {"status": f"needs_{headline}", "missing": missing}

    return {"status": "ready", "missing": []}


async def _validate_offering_ids(db: AsyncSession, tenant_id: uuid.UUID, offering_ids: list[str]) -> list[str]:
    """Never trust supported_offering_ids at face value — only offerings that
    are still real, enabled TenantService rows for THIS tenant count."""
    if not offering_ids:
        return []
    rows = (await db.execute(text(
        "SELECT id::text FROM tenant_services WHERE tenant_id=:tid AND is_enabled=true "
        "AND deleted_at IS NULL AND id = ANY(:ids)"
    ), {"tid": str(tenant_id), "ids": [str(i) for i in offering_ids]})).fetchall()
    return [r[0] for r in rows]


async def compute_team_summary(db: AsyncSession, tenant_id: uuid.UUID) -> dict:
    members_rows = (await db.execute(text(
        "SELECT * FROM provider_team_members WHERE tenant_id=:tid AND deleted_at IS NULL"
    ), {"tid": str(tenant_id)})).fetchall()
    members = [dict(r._mapping) for r in members_rows]

    counts = {"total": len(members), "ready": 0, "needs_setup": 0, "invitation_pending": 0, "disabled": 0}
    per_member = {}
    for m in members:
        readiness = await compute_member_readiness(db, tenant_id, m)
        per_member[str(m["id"])] = readiness
        if readiness["status"] == "ready":
            counts["ready"] += 1
        elif readiness["status"] == "access_disabled":
            counts["disabled"] += 1
        elif readiness["status"] == "invitation_pending":
            counts["invitation_pending"] += 1
        else:
            counts["needs_setup"] += 1

    return {"counts": counts, "per_member": per_member}


async def compute_service_coverage(db: AsyncSession, tenant_id: uuid.UUID) -> list[dict]:
    """One row per enabled tenant offering whose job type requires a
    technician, with the count of READY technicians who can perform it."""
    # NOTE: job_types has no "technician_required" column -- there is no
    # canonical per-job-type signal for this yet, so every enabled offering
    # is conservatively treated as requiring a technician (matches the same
    # conservative default used in home_services_setup_service.py's
    # staff-required gate).
    offerings = (await db.execute(text(
        "SELECT ts.id::text AS id, "
        "COALESCE(ts.tenant_display_name, ms.service_name) AS name, "
        "true AS technician_required "
        "FROM tenant_services ts "
        "JOIN master_services ms ON ms.id = ts.master_service_id "
        "WHERE ts.tenant_id=:tid AND ts.is_enabled=true AND ts.deleted_at IS NULL"
    ), {"tid": str(tenant_id)})).fetchall()

    members_rows = (await db.execute(text(
        "SELECT * FROM provider_team_members WHERE tenant_id=:tid AND deleted_at IS NULL AND status='active'"
    ), {"tid": str(tenant_id)})).fetchall()
    members = [dict(r._mapping) for r in members_rows]

    coverage = []
    for o in offerings:
        if not o.technician_required:
            continue
        ready_count = 0
        for m in members:
            if (m.get("member_type") or "").lower() != "technician":
                continue
            offering_ids = m.get("supported_offering_ids") or []
            if o.id not in offering_ids:
                continue
            readiness = await compute_member_readiness(db, tenant_id, m)
            if readiness["status"] == "ready":
                ready_count += 1
        coverage.append({"offering_id": o.id, "name": o.name, "ready_technician_count": ready_count})
    return coverage
