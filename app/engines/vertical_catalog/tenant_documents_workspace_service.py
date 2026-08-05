"""TENANT-DOCUMENTS-WORKSPACE-01 — post-activation Documents & Verification.

Reuses the canonical TenantDocument model/table (migration 189, extended by
migration 203 with staff_member_id/reviewed_by/review_notes) and the
document_requirements resolver end to end. This module adds NO new document
table and NO new verification lifecycle -- it only projects the existing
review_status/rejection_reason/expiry_date fields into the richer
effective_status / activation_impact / allowed_actions shape the workspace
page needs, and adds the technician-scoped view on top of the same rows.

Distinct from app.engines.vertical_catalog.tenant_documents_router, which is
the ONBOARDING step (gated by require_vertical_not_active) and stays as-is
for that flow. This module is the permanent, post-activation management
surface and has no such gate -- a tenant must be able to see/manage its
documents whether or not Home Services is active yet.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.tenant_engine.models import TenantDocument
from app.engines.vertical_catalog.document_requirements import (
    resolve_requirements, resolve_technician_requirements, POLICY_VERSION,
)

EXPIRING_SOON_WINDOW_DAYS = 30
utcnow = lambda: datetime.now(timezone.utc)


def _effective_status(doc: TenantDocument | None) -> str:
    """review_status and validity_status are separate concepts (per spec);
    this collapses them into ONE display status only where that's actually
    unambiguous -- expiry always wins over a stale 'verified' review_status
    once the date has passed, since an expired document is not verified in
    any meaningful sense a tenant should see."""
    if doc is None:
        return "not_uploaded"
    if doc.expiry_date and doc.expiry_date < utcnow() and doc.status == "verified":
        return "expired"
    return doc.status


def _validity_status(doc: TenantDocument | None) -> str | None:
    if doc is None or not doc.expiry_date:
        return "no_expiry" if doc is not None else None
    if doc.expiry_date < utcnow():
        return "expired"
    if doc.expiry_date < utcnow() + timedelta(days=EXPIRING_SOON_WINDOW_DAYS):
        return "expiring_soon"
    return "valid"


def _allowed_actions(effective_status: str) -> list[str]:
    if effective_status == "not_uploaded":
        return ["UPLOAD"]
    if effective_status in ("rejected", "changes_requested", "expired"):
        return ["UPLOAD_REPLACEMENT", "VIEW_HISTORY"]
    if effective_status == "pending_review":
        return ["VIEW_HISTORY"]
    return ["UPLOAD_REPLACEMENT", "VIEW_HISTORY"]  # verified, still-valid


def _activation_impact(required: bool, effective_status: str) -> dict:
    if not required:
        return {
            "level": "optional", "blocks_activation": False, "blocks_new_jobs": False,
            "human_message": "Optional — informational only.",
        }
    if effective_status == "not_uploaded":
        return {
            "level": "required_for_activation", "blocks_activation": True, "blocks_new_jobs": False,
            "human_message": "Required before activation. Upload to proceed.",
        }
    if effective_status in ("rejected", "expired"):
        return {
            "level": "required_for_continued_operation", "blocks_activation": False, "blocks_new_jobs": True,
            "human_message": "This document needs a replacement to keep operating without restriction.",
        }
    if effective_status == "pending_review":
        return {
            "level": "required_for_continued_operation", "blocks_activation": False, "blocks_new_jobs": False,
            "human_message": "Under review — no interruption while your previous valid version remains on file.",
        }
    if effective_status == "changes_requested":
        return {
            "level": "required_for_continued_operation", "blocks_activation": False, "blocks_new_jobs": False,
            "human_message": "Changes requested — respond to avoid a future restriction.",
        }
    return {
        "level": "required_for_continued_operation", "blocks_activation": False, "blocks_new_jobs": False,
        "human_message": "Verified and current.",
    }


def _doc_row_dict(doc: TenantDocument | None) -> dict | None:
    if doc is None:
        return None
    return {
        "id": str(doc.id), "doc_type": doc.doc_type, "label": doc.label,
        "media_asset_id": str(doc.media_asset_id) if doc.media_asset_id else None,
        "preview_url": f"/v1/media/{doc.media_asset_id}/view" if doc.media_asset_id else None,
        "document_number": _mask_identifier(doc.document_number),
        "issue_date": doc.issue_date.isoformat() if doc.issue_date else None,
        "expiry_date": doc.expiry_date.isoformat() if doc.expiry_date else None,
        "version": doc.version,
        "review_status": doc.status,
        "rejection_reason": doc.rejection_reason,
        "review_notes": doc.review_notes,
        "uploaded_by_user_id": str(doc.uploaded_by_user_id) if doc.uploaded_by_user_id else None,
        "uploaded_at": doc.created_at.isoformat() if doc.created_at else None,
        "reviewed_by": str(doc.reviewed_by) if doc.reviewed_by else None,
        "verified_at": doc.verified_at.isoformat() if doc.verified_at else None,
    }


def _mask_identifier(value: str | None) -> str | None:
    if not value:
        return value
    if len(value) <= 4:
        return "*" * len(value)
    return "*" * (len(value) - 4) + value[-4:]


async def _current_business_documents(db: AsyncSession, tid: uuid.UUID) -> dict[str, TenantDocument]:
    r = await db.execute(select(TenantDocument).where(
        TenantDocument.tenant_id == tid, TenantDocument.is_current == True,  # noqa: E712
        TenantDocument.staff_member_id.is_(None),
    ))
    return {d.doc_type: d for d in r.scalars().all()}


async def _current_staff_documents(db: AsyncSession, tid: uuid.UUID, staff_id: uuid.UUID) -> dict[str, TenantDocument]:
    r = await db.execute(select(TenantDocument).where(
        TenantDocument.tenant_id == tid, TenantDocument.is_current == True,  # noqa: E712
        TenantDocument.staff_member_id == staff_id,
    ))
    return {d.doc_type: d for d in r.scalars().all()}


async def _tenant_row(db: AsyncSession, tid: uuid.UUID):
    return (await db.execute(
        text("SELECT id, vertical, business_type, country FROM tenants WHERE id=:tid"),
        {"tid": str(tid)},
    )).fetchone()


def _build_items(reqs: list[dict], by_type: dict[str, TenantDocument]) -> list[dict]:
    items = []
    for req in reqs:
        doc = by_type.get(req["key"])
        eff = _effective_status(doc)
        items.append({
            **req,
            "document": _doc_row_dict(doc),
            "effective_status": eff,
            "validity_status": _validity_status(doc),
            "allowed_actions": _allowed_actions(eff),
            "activation_impact": _activation_impact(req["required"], eff),
            "updated_at": doc.created_at.isoformat() if doc else None,
        })
    return items


def _summary_counts(items: list[dict]) -> dict:
    total = len(items)
    verified = sum(1 for i in items if i["effective_status"] == "verified")
    under_review = sum(1 for i in items if i["effective_status"] == "pending_review")
    expiring_soon = sum(1 for i in items if i["validity_status"] == "expiring_soon")
    action_required = sum(1 for i in items if i["effective_status"] in
                           ("not_uploaded", "rejected", "changes_requested", "expired"))
    return {
        "total_documents": total, "verified": verified, "under_review": under_review,
        "expiring_soon": expiring_soon, "action_required": action_required,
    }


async def get_business_documents(db: AsyncSession, tid: uuid.UUID) -> dict:
    tenant_row = await _tenant_row(db, tid)
    reqs = resolve_requirements(vertical=tenant_row.vertical, business_type=tenant_row.business_type,
                                 country=tenant_row.country)
    by_type = await _current_business_documents(db, tid)
    items = _build_items(reqs, by_type)
    additional = [_doc_row_dict(d) for d in by_type.values() if d.doc_type == "additional"]
    return {"items": items, "additional_documents": additional, "policy_version": POLICY_VERSION}


async def get_technician_documents_summary(db: AsyncSession, tid: uuid.UUID) -> dict:
    tenant_row = await _tenant_row(db, tid)
    reqs = resolve_technician_requirements(vertical=tenant_row.vertical)
    staff = (await db.execute(text(
        "SELECT id, full_name, designation, status FROM provider_team_members "
        "WHERE tenant_id=:tid AND member_type='technician' ORDER BY full_name"
    ), {"tid": str(tid)})).fetchall()

    rows = []
    for s in staff:
        by_type = await _current_staff_documents(db, tid, s.id)
        items = _build_items(reqs, by_type)
        required = [i for i in items if i["required"]]
        verified = sum(1 for i in required if i["effective_status"] == "verified")
        expiring = sum(1 for i in items if i["validity_status"] == "expiring_soon")
        action_required = sum(1 for i in required if i["effective_status"] in
                               ("not_uploaded", "rejected", "changes_requested", "expired"))
        rows.append({
            "staff_member_id": str(s.id), "full_name": s.full_name,
            "role": s.designation or "Technician", "status": s.status,
            "required_documents": len(required), "verified": verified,
            "expiring": expiring, "action_required": action_required,
            "assignment_eligible": action_required == 0 and len(required) > 0,
        })
    return {"items": rows, "policy_version": POLICY_VERSION}


async def get_technician_documents_detail(db: AsyncSession, tid: uuid.UUID, staff_id: uuid.UUID) -> dict | None:
    staff = (await db.execute(text(
        "SELECT id, full_name, designation FROM provider_team_members WHERE id=:sid AND tenant_id=:tid"
    ), {"sid": str(staff_id), "tid": str(tid)})).fetchone()
    if not staff:
        return None
    tenant_row = await _tenant_row(db, tid)
    reqs = resolve_technician_requirements(vertical=tenant_row.vertical)
    by_type = await _current_staff_documents(db, tid, staff_id)
    items = _build_items(reqs, by_type)
    return {
        "staff_member_id": str(staff.id), "full_name": staff.full_name,
        "role": staff.designation or "Technician", "items": items,
    }


async def get_summary(db: AsyncSession, tid: uuid.UUID) -> dict:
    biz = await get_business_documents(db, tid)
    tech_summary = await get_technician_documents_summary(db, tid)
    all_items = list(biz["items"])
    for row in tech_summary["items"]:
        detail = await get_technician_documents_detail(db, tid, uuid.UUID(row["staff_member_id"]))
        all_items.extend(detail["items"])
    return _summary_counts(all_items)


async def get_expiry_calendar(db: AsyncSession, tid: uuid.UUID, window_days: int = 90) -> list[dict]:
    rows = (await db.execute(select(TenantDocument).where(
        TenantDocument.tenant_id == tid, TenantDocument.is_current == True,  # noqa: E712
        TenantDocument.expiry_date.is_not(None),
        TenantDocument.expiry_date < utcnow() + timedelta(days=window_days),
        TenantDocument.status != "superseded",
    ).order_by(TenantDocument.expiry_date.asc()))).scalars().all()

    tenant_row = await _tenant_row(db, tid)
    biz_reqs = {r["key"]: r for r in resolve_requirements(
        vertical=tenant_row.vertical, business_type=tenant_row.business_type, country=tenant_row.country)}
    tech_reqs = {r["key"]: r for r in resolve_technician_requirements(vertical=tenant_row.vertical)}

    staff_names: dict[str, str] = {}
    staff_ids = {str(d.staff_member_id) for d in rows if d.staff_member_id}
    if staff_ids:
        staff_rows = (await db.execute(text(
            "SELECT id, full_name FROM provider_team_members WHERE id = ANY(:ids)"
        ), {"ids": list(staff_ids)})).fetchall()
        staff_names = {str(s.id): s.full_name for s in staff_rows}

    out = []
    for d in rows:
        req = (tech_reqs if d.staff_member_id else biz_reqs).get(d.doc_type)
        days_remaining = (d.expiry_date - utcnow()).days
        out.append({
            "document_id": str(d.id), "doc_type": d.doc_type,
            "label": d.label or (req["label"] if req else d.doc_type),
            "subject": staff_names.get(str(d.staff_member_id), "Business") if d.staff_member_id else "Business",
            "expiry_date": d.expiry_date.isoformat(),
            "days_remaining": days_remaining,
            "activation_impact": _activation_impact(bool(req and req["required"]), _effective_status(d))["level"],
        })
    return out


async def get_activity(db: AsyncSession, tid: uuid.UUID, limit: int = 50) -> list[dict]:
    rows = (await db.execute(text(
        "SELECT id, actor_id, actor_role, action_type, entity_type, entity_id, "
        "before_state, after_state, notes, created_at FROM tenant_audit_logs "
        "WHERE tenant_id = :tid AND entity_type = 'tenant_document' "
        "ORDER BY created_at DESC LIMIT :lim"
    ), {"tid": str(tid), "lim": limit})).fetchall()
    return [{
        "id": str(r.id), "actor_id": str(r.actor_id) if r.actor_id else None,
        "actor_role": r.actor_role, "action_type": r.action_type,
        "entity_id": r.entity_id, "before_state": r.before_state, "after_state": r.after_state,
        "notes": r.notes, "occurred_at": r.created_at.isoformat() if r.created_at else None,
    } for r in rows]
