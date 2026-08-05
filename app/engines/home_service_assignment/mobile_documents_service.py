"""Technician Mobile App Phase T — Documents & Certifications.

Consolidates onto the CANONICAL `TenantDocument` model (migration 189,
extended by 203 with `staff_member_id`) and the real requirement manifest in
`app/engines/vertical_catalog/document_requirements.py::resolve_technician_requirements`
-- both already used by the tenant-side `/v1/tenant/documents/*` workspace.

Audit finding worth recording: Phase R's `StaffDocument` model
(home_service_assignment/staff_document_models.py, migration 214) is a
SEPARATE, non-versioned technician-document table that duplicates this
concept. It is NOT extended further here and Phase R's profile readiness
calculation is repointed (in mobile_profile_service.py) to read from
TenantDocument instead, so there is exactly one live technician-document
system going forward. The `staff_documents` table/model is left in place
(no destructive drop) but is no longer written to by any current code path.
"""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ServiceOSException, NotFoundException
from app.engines.tenant_engine.models import TenantDocument
from app.engines.vertical_catalog.document_requirements import resolve_technician_requirements

DOCUMENT_MEDIA_CONTEXT = "provider_document"
# No backend-configurable per-requirement threshold exists yet (genuine gap,
# disclosed) -- a single policy-wide default is used instead of a fabricated
# per-requirement value.
DEFAULT_EXPIRY_WARNING_DAYS = 30


def _doc_dict(d: TenantDocument) -> dict:
    return {
        "id": str(d.id),
        "doc_type": d.doc_type,
        "version": d.version,
        "status": d.status,
        "document_number": d.document_number,
        "issue_date": d.issue_date.date().isoformat() if d.issue_date else None,
        "expiry_date": d.expiry_date.date().isoformat() if d.expiry_date else None,
        "submitted_at": d.created_at.isoformat() if d.created_at else None,
        "verified_at": d.verified_at.isoformat() if d.verified_at else None,
        "rejection_reason": d.rejection_reason,
        "review_notes": d.review_notes,
        "media_asset_id": str(d.media_asset_id) if d.media_asset_id else None,
        "is_current": d.is_current,
    }


def _display_condition(doc: TenantDocument | None, warning_days: int) -> str | None:
    """Computed, non-persisted projection over a verified version (spec
    section 5) -- never overwrites `status` in the database."""
    if not doc or doc.status != "verified" or not doc.expiry_date:
        return None
    now = dt.datetime.now(dt.timezone.utc)
    days_left = (doc.expiry_date - now).days
    if days_left < 0:
        return "expired"
    if days_left <= warning_days:
        return "expiring_soon"
    return None


class MobileDocumentsService:
    async def _resolve_staff(self, db: AsyncSession, user_id: uuid.UUID, tenant_id: uuid.UUID):
        from app.engines.home_service_assignment.staff_model import ProviderTeamMember
        res = await db.execute(select(ProviderTeamMember).where(
            ProviderTeamMember.user_id == user_id, ProviderTeamMember.tenant_id == tenant_id,
        ))
        return res.scalars().first()

    async def _current_docs(self, db: AsyncSession, tenant_id: uuid.UUID, staff_id: uuid.UUID) -> dict[str, TenantDocument]:
        rows = (await db.execute(select(TenantDocument).where(
            TenantDocument.tenant_id == tenant_id, TenantDocument.staff_member_id == staff_id,
            TenantDocument.is_current == True,  # noqa: E712
        ))).scalars().all()
        return {d.doc_type: d for d in rows}

    async def get_documents(self, db: AsyncSession, user_id: uuid.UUID, tenant_id: uuid.UUID) -> dict:
        from app.engines.tenant_engine.models import Tenant
        tenant = await db.get(Tenant, tenant_id)
        staff = await self._resolve_staff(db, user_id, tenant_id)
        if not staff:
            return {"readiness": {"percentage": 0, "complete": 0, "required": 0, "action_needed": 0, "pending": 0, "verified": 0}, "requirements": []}

        vertical = getattr(tenant, "vertical", None) or "home_services"
        manifest = resolve_technician_requirements(vertical=vertical)
        current_by_type = await self._current_docs(db, tenant_id, staff.id)

        requirements = []
        complete = required_total = action_needed = pending = verified = 0
        for req in manifest:
            doc = current_by_type.get(req["key"])
            display_condition = _display_condition(doc, DEFAULT_EXPIRY_WARNING_DAYS)
            status = doc.status if doc else "missing"

            if req["required"]:
                required_total += 1
                is_complete = status == "verified" and display_condition != "expired"
                if is_complete:
                    complete += 1
                elif status in ("rejected", "changes_requested", "missing") or display_condition == "expired":
                    action_needed += 1
                elif status == "pending_review":
                    pending += 1

            if status == "verified":
                verified += 1

            if not doc:
                allowed_actions = ["upload"]
            else:
                allowed_actions = ["view", "history"]
                needs_replacement = status in ("rejected", "changes_requested") or display_condition in ("expiring_soon", "expired")
                if needs_replacement:
                    allowed_actions.append("replace")

            days_until_expiry = None
            if doc and doc.expiry_date:
                days_until_expiry = (doc.expiry_date - dt.datetime.now(dt.timezone.utc)).days

            requirements.append({
                "requirement_id": req["key"],
                "code": req["key"],
                "label": req["label"],
                "required": req["required"],
                "requires_expiry": req["requires_expiry"],
                "requires_document_number": req["requires_document_number"],
                "current_document_id": str(doc.id) if doc else None,
                "current_version": doc.version if doc else None,
                "review_status": status,
                "display_condition": display_condition,
                "submitted_at": doc.created_at.isoformat() if doc and doc.created_at else None,
                "verified_at": doc.verified_at.isoformat() if doc and doc.verified_at else None,
                "expires_at": doc.expiry_date.date().isoformat() if doc and doc.expiry_date else None,
                "days_until_expiry": days_until_expiry,
                "reviewer_note": (doc.rejection_reason or doc.review_notes) if doc else None,
                "allowed_actions": allowed_actions,
            })

        percentage = round((complete / required_total) * 100) if required_total else 0
        return {
            "readiness": {
                "percentage": percentage, "complete": complete, "required": required_total,
                "action_needed": action_needed, "pending": pending, "verified": verified,
            },
            "requirements": requirements,
        }

    async def submit_document(self, db: AsyncSession, user_id: uuid.UUID, tenant_id: uuid.UUID, *,
                               doc_type: str, media_asset_id: uuid.UUID,
                               document_number: str | None, issue_date: dt.datetime | None,
                               expiry_date: dt.datetime | None) -> dict:
        from app.engines.tenant_engine.models import Tenant
        from app.engines.media.models import MediaAsset

        staff = await self._resolve_staff(db, user_id, tenant_id)
        if not staff:
            raise NotFoundException("StaffMember", str(user_id))

        tenant = await db.get(Tenant, tenant_id)
        vertical = getattr(tenant, "vertical", None) or "home_services"
        known_keys = {r["key"] for r in resolve_technician_requirements(vertical=vertical)}
        if doc_type not in known_keys:
            raise ServiceOSException("DOC_TYPE_NOT_APPLICABLE", "This document type is not part of your requirements.", status_code=422)

        if expiry_date and issue_date and expiry_date < issue_date:
            raise ServiceOSException("INVALID_DATES", "Expiry date cannot precede issue date.", status_code=422)

        asset = (await db.execute(select(MediaAsset).where(MediaAsset.id == media_asset_id))).scalar_one_or_none()
        if not asset or asset.tenant_id != tenant_id or asset.status != "active":
            raise ServiceOSException("MEDIA_ASSET_NOT_FOUND", "The uploaded file could not be found.", status_code=404)
        if asset.media_context != DOCUMENT_MEDIA_CONTEXT:
            raise ServiceOSException("MEDIA_CONTEXT_MISMATCH", "This file was not uploaded as a verification document.", status_code=422)

        existing = (await db.execute(select(TenantDocument).where(
            TenantDocument.tenant_id == tenant_id, TenantDocument.staff_member_id == staff.id,
            TenantDocument.doc_type == doc_type, TenantDocument.is_current == True,  # noqa: E712
        ))).scalar_one_or_none()

        new_doc = TenantDocument(
            tenant_id=tenant_id, doc_type=doc_type, staff_member_id=staff.id,
            media_asset_id=media_asset_id, file_url=f"/v1/media/{media_asset_id}/view",
            document_number=document_number, issue_date=issue_date, expiry_date=expiry_date,
            version=(existing.version + 1) if existing else 1,
            is_current=True, status="pending_review",
            uploaded_by_user_id=user_id,
        )
        db.add(new_doc)
        await db.flush()

        if existing:
            existing.is_current = False
            existing.status = "superseded"
            existing.superseded_by_id = new_doc.id

        from app.engines.tenant_engine.models import TenantAuditLog
        db.add(TenantAuditLog(
            tenant_id=tenant_id, actor_id=user_id, actor_role="technician",
            action_type="document.submitted", entity_type="tenant_document", entity_id=str(new_doc.id),
            before_state=None, after_state={"status": "pending_review", "doc_type": doc_type},
        ))
        await db.commit()
        await db.refresh(new_doc)
        return _doc_dict(new_doc)

    async def list_versions(self, db: AsyncSession, user_id: uuid.UUID, tenant_id: uuid.UUID, doc_type: str) -> list[dict]:
        staff = await self._resolve_staff(db, user_id, tenant_id)
        if not staff:
            return []
        rows = (await db.execute(select(TenantDocument).where(
            TenantDocument.tenant_id == tenant_id, TenantDocument.staff_member_id == staff.id,
            TenantDocument.doc_type == doc_type,
        ).order_by(TenantDocument.version.desc()))).scalars().all()
        return [_doc_dict(d) for d in rows]

    # ── Tenant review (spec section 10) ─────────────────────────────────────

    async def review_document(self, db: AsyncSession, tenant_id: uuid.UUID, document_id: uuid.UUID, *,
                               decision: str, reviewer_user_id: uuid.UUID, reason: str | None) -> dict:
        if decision not in ("verified", "rejected", "changes_requested"):
            raise ServiceOSException("INVALID_DECISION", "decision must be 'verified', 'rejected' or 'changes_requested'.", status_code=422)

        doc = (await db.execute(select(TenantDocument).where(
            TenantDocument.id == document_id, TenantDocument.tenant_id == tenant_id,
            TenantDocument.staff_member_id.is_not(None),
        ))).scalar_one_or_none()
        if not doc:
            raise NotFoundException("Document", str(document_id))
        if not doc.is_current:
            raise ServiceOSException("STALE_VERSION", "A newer version of this document has since been submitted.", status_code=409)
        if doc.status not in ("pending_review", "changes_requested"):
            raise ServiceOSException("ALREADY_DECIDED", "This document has already been decided.", status_code=409)
        if doc.uploaded_by_user_id == reviewer_user_id:
            raise ServiceOSException("SELF_REVIEW_FORBIDDEN", "You cannot review your own submitted document.", status_code=403)
        if decision == "rejected" and not (reason or "").strip():
            raise ServiceOSException("REASON_REQUIRED", "A reason is required to reject a document.", status_code=400)

        before = {"status": doc.status}
        if decision == "verified":
            doc.status = "verified"
            doc.verified_at = dt.datetime.now(dt.timezone.utc)
            doc.rejection_reason = None
            doc.review_notes = None
        elif decision == "changes_requested":
            doc.status = "changes_requested"
            doc.review_notes = reason or "Changes requested by reviewer."
            doc.rejection_reason = None
            doc.verified_at = None
        else:
            doc.status = "rejected"
            doc.rejection_reason = reason or "Document rejected by reviewer."
            doc.review_notes = None
            doc.verified_at = None
        doc.reviewed_by = reviewer_user_id

        from app.engines.tenant_engine.models import TenantAuditLog
        db.add(TenantAuditLog(
            tenant_id=tenant_id, actor_id=reviewer_user_id, actor_role="tenant_owner",
            action_type=f"document.{decision}", entity_type="tenant_document", entity_id=str(doc.id),
            before_state=before, after_state={"status": doc.status},
            notes=doc.rejection_reason or doc.review_notes,
        ))
        await db.commit()
        await db.refresh(doc)

        await self._notify_technician(db, doc, decision)
        return _doc_dict(doc)

    async def _notify_technician(self, db: AsyncSession, doc: TenantDocument, decision: str) -> None:
        from app.engines.platform_notifications.notification_service import NotificationService
        event_key = {"verified": "document.verified", "changes_requested": "document.changes_requested", "rejected": "document.rejected"}[decision]
        try:
            await NotificationService().fire_event(
                db, event_key, {"doc_type": doc.doc_type}, tenant_id=doc.tenant_id,
                actor_user_id=doc.reviewed_by,
                source_record_type="tenant_document", source_record_id=doc.id,
                recipients=[{"user_id": str(doc.uploaded_by_user_id), "recipient_type": "staff"}],
            )
        except Exception:
            pass
