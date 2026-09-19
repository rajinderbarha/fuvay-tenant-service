"""Private staff feedback after a completed home-service job.

This is not a customer review or a payment declaration. Payment is read from
the reconciled payment record and cannot be set by the technician here.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.execution.mobile_direct_payment_service import MobileDirectPaymentService
from app.engines.platform_commerce.models import CustomerBehaviorAssessment
from app.exceptions import ServiceOSException


BEHAVIOR_CHOICES = (
    {"code": "respectful", "label": "Respectful and cooperative"},
    {"code": "neutral", "label": "No concern"},
    {"code": "difficult", "label": "Difficult interaction"},
    {"code": "unsafe", "label": "Unsafe or abusive behaviour"},
)
NEGATIVE_REASONS = (
    {"code": "rude_language", "label": "Rude or abusive language"},
    {"code": "access_denied", "label": "Access or cooperation issue"},
    {"code": "safety_concern", "label": "Safety concern"},
    {"code": "other", "label": "Other"},
)


class MobileCustomerAssessmentService:
    async def _assigned(self, db: AsyncSession, user_id: uuid.UUID, tenant_id: uuid.UUID, job_id: uuid.UUID):
        return await MobileDirectPaymentService()._get_assigned_job(db, user_id, tenant_id, job_id)

    async def get_status(self, db: AsyncSession, user_id: uuid.UUID, tenant_id: uuid.UUID, job_id: uuid.UUID) -> dict:
        from app.engines.invoice_payment.models import ServicePaymentRecord

        job, staff_id = await self._assigned(db, user_id, tenant_id, job_id)
        assessment = (await db.execute(select(CustomerBehaviorAssessment).where(
            CustomerBehaviorAssessment.job_id == job.id,
            CustomerBehaviorAssessment.tenant_id == tenant_id,
        ))).scalars().first()
        payment = (await db.execute(select(ServicePaymentRecord).where(
            ServicePaymentRecord.job_id == job.id,
            ServicePaymentRecord.tenant_id == tenant_id,
            ServicePaymentRecord.customer_id == job.customer_id,
        ).order_by(ServicePaymentRecord.created_at.desc()))).scalars().first()
        payment_state = (
            "confirmed" if payment and (payment.reconciliation_status == "confirmed" or payment.payment_status == "verified")
            else "unresolved" if payment and payment.reconciliation_status in {"mismatched", "disputed"}
            else "not_confirmed" if payment else "not_recorded"
        )
        eligible = job.status == "completed"
        return {
            "job_id": str(job.id),
            "eligible": eligible,
            "submitted": assessment is not None,
            "show_prompt": eligible and assessment is None,
            "payment": {"status": payment_state, "read_only": True},
            "behavior_choices": BEHAVIOR_CHOICES if eligible and assessment is None else [],
            "negative_reason_choices": NEGATIVE_REASONS if eligible and assessment is None else [],
            "assessment": (
                {"behavior_code": assessment.behavior_code,
                 "reason_code": assessment.reason_code,
                 "note": assessment.note,
                 "submitted_at": assessment.created_at.isoformat() if assessment.created_at else None}
                if assessment is not None and assessment.staff_member_id == staff_id else None
            ),
            "privacy_note": "Private staff feedback. Not shown in public reviews.",
        }

    async def submit(
        self, db: AsyncSession, user_id: uuid.UUID, tenant_id: uuid.UUID, job_id: uuid.UUID,
        behavior_code: str, reason_code: str | None, note: str | None,
    ) -> dict:
        job, staff_id = await self._assigned(db, user_id, tenant_id, job_id)
        if job.status != "completed":
            raise ServiceOSException("JOB_NOT_COMPLETED", "Customer feedback is available after job completion.", status_code=409)
        allowed_behaviors = {choice["code"] for choice in BEHAVIOR_CHOICES}
        if behavior_code not in allowed_behaviors:
            raise ServiceOSException("ASSESSMENT_BEHAVIOR_INVALID", "Choose one of the available behaviour options.", status_code=422)
        negative = behavior_code in {"difficult", "unsafe"}
        reasons = {choice["code"] for choice in NEGATIVE_REASONS}
        if negative and (reason_code not in reasons or not note):
            raise ServiceOSException("ASSESSMENT_REASON_REQUIRED", "Select a reason and add a short factual note.", status_code=422)
        if not negative and (reason_code or note):
            raise ServiceOSException("ASSESSMENT_UNEXPECTED_DETAIL", "Reason and note are for concerns only.", status_code=422)
        if behavior_code == "unsafe" and reason_code != "safety_concern":
            raise ServiceOSException("ASSESSMENT_SAFETY_REASON_REQUIRED", "Select safety concern for unsafe behaviour.", status_code=422)

        statement = insert(CustomerBehaviorAssessment).values(
            job_id=job.id, tenant_id=tenant_id, customer_id=job.customer_id,
            staff_member_id=staff_id, behavior_code=behavior_code,
            reason_code=reason_code, note=note,
        ).on_conflict_do_nothing(index_elements=["job_id"]).returning(CustomerBehaviorAssessment.id)
        inserted = (await db.execute(statement)).scalar_one_or_none()
        if inserted is None:
            existing = (await db.execute(select(CustomerBehaviorAssessment).where(
                CustomerBehaviorAssessment.job_id == job.id,
            ))).scalar_one()
            if (existing.staff_member_id, existing.behavior_code, existing.reason_code, existing.note) != (
                staff_id, behavior_code, reason_code, note,
            ):
                raise ServiceOSException("ASSESSMENT_ALREADY_SUBMITTED", "Feedback for this job has already been submitted.", status_code=409)
        else:
            from app.engines.platform_commerce.service import CommerceService
            await CommerceService(db).recompute_customer_health(job.customer_id, tenant_id)
        return {"job_id": str(job.id), "submitted": True, "idempotent": inserted is None}
