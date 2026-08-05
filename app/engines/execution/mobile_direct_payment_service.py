"""Technician Mobile App Phase O — Direct Payment Confirmation & Final Job
Closure. Thin technician-authorized wrapper over the EXISTING, fully-built
`DirectPaymentsService` (app/engines/invoice_payment/direct_payments_service.py)
and the existing `complete_job` finalization action -- never a second
payment/finance engine, never a second commission trigger.

Gap this closes (audited): `DirectPaymentsService`'s own router requires
`DIRECT_PAYMENTS_*` permissions the technician role does not have (staff/
office-only by design), and none of its methods check job assignment
themselves (only tenant scope). This module adds exactly that missing
authorization layer -- session/tenant/technician/assignment -- around calls
that already do all the real work.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ServiceOSException

_TERMINAL_STATUSES = {"completed", "cancelled", "failed", "closed_estimate_declined"}
_PARTS_UNRESOLVED_STATUSES = {"requested", "customer_approval_pending"}


class MobileDirectPaymentService:
    async def _resolve_staff_member_id(self, db: AsyncSession, user_id: uuid.UUID) -> uuid.UUID:
        from app.engines.home_service_assignment.staff_model import ProviderTeamMember
        res = await db.execute(select(ProviderTeamMember.id).where(ProviderTeamMember.user_id == user_id))
        row = res.scalars().first()
        return row if row else user_id

    async def _get_assigned_job(self, db: AsyncSession, user_id: uuid.UUID, tenant_id: uuid.UUID, job_id: uuid.UUID):
        from app.engines.final_records.models import ServiceJob
        staff_id = await self._resolve_staff_member_id(db, user_id)
        job = await db.get(ServiceJob, job_id)
        if not job or str(job.tenant_id) != str(tenant_id):
            raise ServiceOSException("ENTITY_NOT_FOUND", "Job not found.", status_code=404)
        if str(job.assigned_staff_id) not in (str(staff_id), str(user_id)):
            raise ServiceOSException("ENTITY_NOT_ASSIGNED", "This job is not assigned to you.", status_code=403)
        return job, staff_id

    def _svc(self, db: AsyncSession, tenant_id: uuid.UUID, request_id: str | None):
        from app.engines.invoice_payment.direct_payments_service import DirectPaymentsService
        return DirectPaymentsService(db, tenant_id, request_id or "—")

    async def _completion_proof(self, db: AsyncSession, job_id: uuid.UUID):
        from app.engines.execution.models import CompletionProof
        res = await db.execute(select(CompletionProof).where(CompletionProof.job_id == job_id))
        return res.scalars().first()

    async def _unresolved_parts(self, db: AsyncSession, job_id: uuid.UUID) -> list[str]:
        from app.engines.execution.models import PartsRequest
        rows = (await db.execute(select(PartsRequest).where(PartsRequest.job_id == job_id))).scalars().all()
        return [str(p.id) for p in rows if p.status in _PARTS_UNRESOLVED_STATUSES]

    async def get_detail(self, db: AsyncSession, user_id: uuid.UUID, tenant_id: uuid.UUID, job_id: uuid.UUID) -> dict:
        from app.engines.invoice_payment.models import ServicePaymentRecord
        from app.engines.invoice_payment.direct_payments_constants import RS_CONFIRMED

        job, staff_id = await self._get_assigned_job(db, user_id, tenant_id, job_id)
        svc = self._svc(db, tenant_id, None)

        booking = await svc._booking(job.booking_id) if job.booking_id else None
        invoice = await svc._invoice_for_job(job.id)
        expected = await svc.resolve_expected_amount(job, booking, invoice)

        record = (await db.execute(
            select(ServicePaymentRecord).where(ServicePaymentRecord.job_id == job.id, ServicePaymentRecord.tenant_id == tenant_id)
        )).scalars().first()
        provider_record = await svc._row(record) if record else None
        status = provider_record["status"] if provider_record else "not_declared"

        proof = await self._completion_proof(db, job.id)
        proof_submitted = bool(proof and proof.status == "submitted")
        handover_status = proof.handover_status if proof else "not_requested"
        handover_ok = handover_status in ("acknowledged",)
        unresolved_parts = await self._unresolved_parts(db, job.id)

        blockers = []
        if not proof_submitted:
            blockers.append("COMPLETION_PROOF_NOT_SUBMITTED")
        if not handover_ok:
            blockers.append("CUSTOMER_HANDOVER_NOT_ACKNOWLEDGED")
        if unresolved_parts:
            blockers.append("PARTS_UNRESOLVED")
        if status == "not_declared":
            blockers.append("PAYMENT_NOT_DECLARED")
        elif status != RS_CONFIRMED:
            blockers.append("PAYMENT_NOT_RECONCILED")
        is_terminal = job.status in _TERMINAL_STATUSES
        if is_terminal:
            blockers.append("JOB_ALREADY_COMPLETED" if job.status == "completed" else "JOB_TERMINAL")

        can_submit_provider_record = proof_submitted and record is None and not is_terminal
        can_finalize = not blockers

        allowed_actions: list[str] = []
        if can_submit_provider_record:
            allowed_actions.append("declare_payment")
        if record and status != RS_CONFIRMED and not is_terminal:
            allowed_actions.append("remind_customer")
        if can_finalize:
            allowed_actions.append("finalize_job")

        return {
            "job": {"job_id": str(job.id), "job_reference": job.job_number, "workflow_status": job.status, "is_terminal": is_terminal},
            "amount": expected,
            "prerequisites": {
                "completion_proof_submitted": proof_submitted,
                "customer_handover_status": handover_status,
            },
            "provider_record": provider_record,
            "closure_readiness": {
                "can_submit_provider_record": can_submit_provider_record,
                "can_finalize": can_finalize,
                "blockers": blockers,
            },
            "allowed_methods": ["onsite_cash", "onsite_upi", "onsite_card", "onsite_bank_transfer", "onsite_other"],
            "allowed_actions": allowed_actions,
        }

    # ── Mutations ─────────────────────────────────────────────────────────

    async def declare_payment(self, db: AsyncSession, user_id: uuid.UUID, tenant_id: uuid.UUID, job_id: uuid.UUID, *,
                               amount, method: str, reference_id: str | None, note: str | None,
                               evidence_media_id: str | None, request_id: str | None) -> dict:
        job, staff_id = await self._get_assigned_job(db, user_id, tenant_id, job_id)
        proof = await self._completion_proof(db, job.id)
        if not proof or proof.status != "submitted":
            raise ServiceOSException("COMPLETION_PROOF_NOT_SUBMITTED", "Submit completion proof before recording payment.", status_code=409)
        svc = self._svc(db, tenant_id, request_id)
        result = await svc.declare(
            job_id=job.id, amount=amount, method=method, actor_user_id=str(user_id),
            reference_id=reference_id, note=note, evidence_media_id=evidence_media_id,
        )
        return result["record"]

    async def remind_customer(self, db: AsyncSession, user_id: uuid.UUID, tenant_id: uuid.UUID, job_id: uuid.UUID, request_id: str | None) -> dict:
        from app.engines.invoice_payment.models import ServicePaymentRecord
        job, staff_id = await self._get_assigned_job(db, user_id, tenant_id, job_id)
        record = (await db.execute(
            select(ServicePaymentRecord).where(ServicePaymentRecord.job_id == job.id, ServicePaymentRecord.tenant_id == tenant_id)
        )).scalars().first()
        if not record:
            raise ServiceOSException("DIRECT_PAYMENT_NOT_DECLARED", "Declare the payment before sending a reminder.", status_code=409)
        svc = self._svc(db, tenant_id, request_id)
        return await svc.remind_customer(payment_id=record.id, actor_user_id=str(user_id))

    async def finalize_job(self, db: AsyncSession, user_id: uuid.UUID, tenant_id: uuid.UUID, job_id: uuid.UUID, request_id: str | None) -> dict:
        """Reuses the EXISTING, single canonical `complete_job` action
        verbatim (spec section 17: "Do not implement finalization separately
        in the mobile route") -- this wrapper only adds the pre-check +
        assignment resolution; every gate (parts, checklist, direct-payment
        reconciliation, commission trigger) still runs exactly where it
        always has, once, inside complete_job itself."""
        from app.engines.invoice_payment.models import ServicePaymentRecord
        from app.engines.execution.constants import PAYMENT_MODE_HOME_SERVICES

        job, staff_id = await self._get_assigned_job(db, user_id, tenant_id, job_id)
        detail = await self.get_detail(db, user_id, tenant_id, job_id)
        if not detail["closure_readiness"]["can_finalize"]:
            raise ServiceOSException("JOB_NOT_READY_TO_FINALIZE", "Every closure requirement must pass before completing the job.", status_code=409, context={"blockers": detail["closure_readiness"]["blockers"]})
        proof = await self._completion_proof(db, job.id)
        record = (await db.execute(
            select(ServicePaymentRecord).where(ServicePaymentRecord.job_id == job.id, ServicePaymentRecord.tenant_id == tenant_id)
        )).scalars().first()
        collected_amount = record.collected_amount if record else 0
        from app.engines.execution.home_service_service import HomeServiceJobExecutionService
        result = await HomeServiceJobExecutionService().complete_job(
            db, job.id, tenant_id, staff_id, user_id,
            work_summary=proof.resolution_summary if proof else "Work completed.",
            collected_amount=collected_amount, payment_mode=PAYMENT_MODE_HOME_SERVICES,
            before_photo_ids=proof.before_photo_ids if proof else None,
            after_photo_ids=proof.after_photo_ids if proof else None,
            completion_photo_ids=None, customer_signature_id=None,
            technician_note=proof.final_service_notes if proof else None,
            request_id=request_id,
        )
        await db.commit()
        return result
