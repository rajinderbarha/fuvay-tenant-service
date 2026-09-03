"""Technician Mobile App Phase R — Profile & Account Hub.

Reuses the canonical `User` (auth engine), `ProviderTeamMember` (employment
identity), `UserSession`/MFA (auth engine), `provider_availability_rules`
(Phase P), and adds only the two genuinely-missing pieces confirmed by
audit: per-staff documents (`StaffDocument`) and a personal profile-
completeness calculation. Never a second identity/session/document system.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

# Technician screening belongs to the provider. Documents remain available as
# optional private records, but none are a Fuvay readiness requirement.
REQUIRED_DOCUMENT_TYPES: list[str] = []


def _mask_phone(phone: str | None) -> str | None:
    if not phone or len(phone) < 4:
        return phone
    return f"••••• {phone[-5:]}"


class MobileProfileService:
    async def _resolve_staff(self, db: AsyncSession, user_id: uuid.UUID, tenant_id: uuid.UUID):
        from app.engines.home_service_assignment.staff_model import ProviderTeamMember
        res = await db.execute(select(ProviderTeamMember).where(
            ProviderTeamMember.user_id == user_id, ProviderTeamMember.tenant_id == tenant_id,
        ))
        return res.scalars().first()

    async def _documents(self, db: AsyncSession, tenant_id: uuid.UUID, staff_id: uuid.UUID) -> list:
        from app.engines.home_service_assignment.staff_document_models import StaffDocument
        res = await db.execute(select(StaffDocument).where(
            StaffDocument.tenant_id == tenant_id, StaffDocument.staff_member_id == staff_id, StaffDocument.is_current.is_(True),
        ).order_by(StaffDocument.created_at.desc()))
        return list(res.scalars().all())

    async def get_profile(self, db: AsyncSession, user_id: uuid.UUID, tenant_id: uuid.UUID) -> dict:
        from sqlalchemy import text
        from app.engines.auth.models import User, UserSession
        from app.engines.tenant_engine.models import Tenant
        from app.engines.home_service_assignment.staff_document_models import DOC_STATUS_VERIFIED

        user = await db.get(User, user_id)
        tenant = await db.get(Tenant, tenant_id)
        staff = await self._resolve_staff(db, user_id, tenant_id)
        staff_id = staff.id if staff else user_id

        documents = await self._documents(db, tenant_id, staff_id)
        doc_by_type = {d.document_type: d for d in documents}

        required_total = len(REQUIRED_DOCUMENT_TYPES)
        required_verified = len([t for t in REQUIRED_DOCUMENT_TYPES if doc_by_type.get(t) and doc_by_type[t].status == DOC_STATUS_VERIFIED])

        working_hours_count = 0
        if staff:
            working_hours_count = (await db.execute(text(
                "SELECT count(*) FROM provider_availability_rules WHERE tenant_id=:tid AND scope_type='staff_member' AND scope_id=:sid AND is_active=true"
            ), {"tid": str(tenant_id), "sid": str(staff_id)})).scalar() or 0

        session_count = (await db.execute(
            select(func.count()).select_from(UserSession).where(UserSession.user_id == user_id, UserSession.revoked_at.is_(None))
        )).scalar() or 0

        completeness_checks = {
            "has_photo": bool(staff.profile_photo_url) if staff else False,
            "has_assigned_service": bool(staff.supported_offering_ids) if staff else False,
            "has_working_hours": working_hours_count > 0,
        }
        completed = sum(1 for v in completeness_checks.values() if v)
        total = len(completeness_checks)
        percentage = round((completed / total) * 100) if total else 0
        missing = [
            {"code": "PHOTO_MISSING", "label": "Add a profile photo", "destination": "edit_profile"} if not completeness_checks["has_photo"] else None,
            {"code": "NO_ASSIGNED_SERVICE", "label": "No services assigned yet", "destination": "employment"} if not completeness_checks["has_assigned_service"] else None,
            {"code": "NO_WORKING_HOURS", "label": "Working hours not configured", "destination": "availability"} if not completeness_checks["has_working_hours"] else None,
        ]
        missing = [m for m in missing if m]

        return {
            "identity": {
                "user_id": str(user.id), "full_name": user.full_name,
                "photo_url": staff.profile_photo_url if staff else user.avatar_url,
                "masked_mobile": _mask_phone(user.phone),
                "email_verified": bool(user.is_verified), "mobile_verified": bool(user.is_verified),
                "status": staff.status if staff else user.account_status,
            },
            "employment": {
                "tenant_id": str(tenant_id), "business_name": tenant.business_name if tenant else None,
                "staff_type": staff.member_type if staff else None,
                "designation": staff.designation if staff else None,
                "joined_at": staff.created_at.isoformat() if staff and staff.created_at else None,
                "assigned_service_count": len(staff.supported_offering_ids or []) if staff else 0,
                "staff_reference": str(staff_id)[:8].upper() if staff else None,
            },
            "readiness": {
                "profile_percentage": percentage, "completed": completed, "required": total,
                "verified_documents": required_verified, "required_documents": required_total,
                "account_verified": bool(user.is_verified), "missing": missing,
            },
            "documents": [d.to_dict() for d in documents],
            "required_document_types": REQUIRED_DOCUMENT_TYPES,
            "security": {
                "mfa_enabled": bool(user.is_mfa_enabled), "active_session_count": int(session_count),
            },
        }

    async def add_document(self, db: AsyncSession, user_id: uuid.UUID, tenant_id: uuid.UUID, *,
                            document_type: str, media_id: uuid.UUID, expiry_date=None) -> dict:
        from app.engines.home_service_assignment.staff_document_models import StaffDocument
        staff = await self._resolve_staff(db, user_id, tenant_id)
        staff_id = staff.id if staff else user_id

        existing = await db.execute(select(StaffDocument).where(
            StaffDocument.tenant_id == tenant_id, StaffDocument.staff_member_id == staff_id,
            StaffDocument.document_type == document_type, StaffDocument.is_current.is_(True),
        ))
        for row in existing.scalars().all():
            row.is_current = False
            import datetime as dt
            row.superseded_at = dt.datetime.now(dt.timezone.utc)
            db.add(row)

        doc = StaffDocument(
            tenant_id=tenant_id, staff_member_id=staff_id, document_type=document_type,
            media_id=media_id, status="pending_review", expiry_date=expiry_date,
            submitted_by_user_id=user_id,
        )
        db.add(doc)
        await db.commit()
        return doc.to_dict()
