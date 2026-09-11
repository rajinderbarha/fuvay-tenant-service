"""Technician Mobile App Phase N — Completion Proof & Customer Handover.

Genuinely new (audited, confirmed missing): the only existing completion-
shaped fields live inside ServiceJob.completion_data, written atomically
WITH the final `completed` transition + commission trigger inside
`complete_job` -- there is no separate pre-completion capture point. This
module adds exactly that missing stage via the new `CompletionProof` table,
and never calls `complete_job`/`_set_status`/`deduct_for_completed_job`
itself -- submitting proof only ever leaves `ServiceJob.status` at
`work_done`. Final completion remains a distinct, later, canonical action.

Final checklist reuses the checklist_catalog engine (PURPOSE_COMPLETION),
same pattern as inspection/work checklists in prior phases -- never a
second checklist model.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ServiceOSException
from app.engines.execution.constants import JS_WORK_DONE
from app.engines.execution.models import CompletionProof

_TERMINAL_STATUSES = {"completed", "cancelled", "failed", "closed_estimate_declined"}
_PARTS_UNRESOLVED_STATUSES = {"requested", "customer_approval_pending"}
_HANDOVER_REMINDER_COOLDOWN_SECONDS = 3600


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _proof_view(proof: CompletionProof) -> dict:
    """Serialize a proof with its photo lists always present as lists.

    `before_photo_ids` / `after_photo_ids` are nullable JSONB with no server
    default, so a proof that has never had a photo attached carries SQL NULL
    and the generic `to_dict()` hands that straight to the client as `null`.
    The mobile Evidence grid types them as arrays and maps over them on
    render, so the whole completion screen died on
    "Cannot read property 'map' of null" -- for every job reaching completion
    without photos, which is the common case now that evidence is optional.

    An absent list is an empty list. Normalizing here rather than at the one
    call site that crashed covers the mutation responses too, which return the
    same shape and would have reintroduced the null on the next save.
    """
    return {
        **proof.to_dict(),
        "before_photo_ids": list(proof.before_photo_ids or []),
        "after_photo_ids": list(proof.after_photo_ids or []),
    }


class MobileCompletionProofService:
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

    async def _get_or_create_proof(self, db: AsyncSession, job, staff_id: uuid.UUID) -> CompletionProof:
        res = await db.execute(select(CompletionProof).where(CompletionProof.job_id == job.id))
        proof = res.scalars().first()
        if proof is None:
            proof = CompletionProof(job_id=job.id, tenant_id=job.tenant_id, staff_member_id=staff_id, status="draft")
            db.add(proof)
            await db.flush()
        return proof

    async def _work_summary(self, db: AsyncSession, job) -> dict:
        from app.engines.execution.work_session_service import WorkSessionService
        from app.engines.quote_checklist.quote_service import ServiceJobQuoteService
        session = await WorkSessionService().get(db, job.id)
        quotes = await ServiceJobQuoteService().list_quotes_for_job(db, str(job.id), str(job.tenant_id))
        current = next((q for q in quotes if q["is_current"]), None)
        return {
            "work_finished_at": session.finished_at.isoformat() if session and session.finished_at else None,
            "work_session_id": str(session.id) if session else None,
            "approved_quote_id": current["id"] if current else None,
            "approved_quote_version": current["version_number"] if current else None,
        }

    async def _final_checks(self, db: AsyncSession, job) -> dict:
        from app.engines.checklist_catalog import service as checklist_svc
        from app.engines.checklist_catalog import constants as c

        mappings = await checklist_svc.get_applicable_mappings(db, job, phase=c.PURPOSE_COMPLETION)
        if not mappings:
            return {"items": [], "required_total": 0, "required_completed": 0}
        mapping = next((m for m in mappings if m.usage == c.USAGE_REQUIRED), mappings[0])
        instance = await checklist_svc.ensure_instance(db, job, mapping)
        items = await checklist_svc._instance_items(db, instance)
        from app.engines.checklist_catalog.models import JobChecklistResponse
        responses = {
            r.checklist_item_id: r for r in (await db.execute(
                select(JobChecklistResponse).where(JobChecklistResponse.job_checklist_instance_id == instance.id)
            )).scalars().all()
        }
        required_total = required_completed = 0
        item_dicts = []
        for item in sorted(items, key=lambda i: i.display_order):
            resp = responses.get(item.id)
            answered = resp is not None and resp.response_value not in (None, {}, "")
            if item.is_required:
                required_total += 1
                if answered:
                    required_completed += 1
            idict = item.to_dict()
            idict["response"] = resp.to_dict() if resp else None
            idict["instance_id"] = str(instance.id)
            item_dicts.append(idict)
        return {"items": item_dicts, "required_total": required_total, "required_completed": required_completed, "instance_id": str(instance.id)}

    async def _parts_used(self, db: AsyncSession, job) -> list[dict]:
        from app.engines.execution.models import PartsRequest
        rows = (await db.execute(
            select(PartsRequest).where(PartsRequest.job_id == job.id).order_by(PartsRequest.created_at.desc())
        )).scalars().all()
        return [p.to_dict() for p in rows]

    async def get_detail(self, db: AsyncSession, user_id: uuid.UUID, tenant_id: uuid.UUID, job_id: uuid.UUID) -> dict:
        job, staff_id = await self._get_assigned_job(db, user_id, tenant_id, job_id)
        is_terminal = job.status in _TERMINAL_STATUSES
        work_finished = job.status == JS_WORK_DONE

        proof = await self._get_or_create_proof(db, job, staff_id)
        work_summary = await self._work_summary(db, job)
        final_checks = await self._final_checks(db, job)
        parts = await self._parts_used(db, job)
        unresolved_parts = [p["parts_request_id"] for p in parts if p["status"] in _PARTS_UNRESOLVED_STATUSES]

        missing_check_ids = [i["id"] for i in final_checks["items"] if i["is_required"] and (i["response"] is None or i["response"]["response_value"] in (None, {}, ""))]

        # Before/after photos are optional evidence, never a blocker: a
        # technician whose photo upload fails on site must still be able to
        # submit proof and close the job.
        blockers = []
        if not work_finished:
            blockers.append("WORK_NOT_FINISHED")
        if proof.status == "submitted":
            blockers.append("PROOF_ALREADY_SUBMITTED")
        if missing_check_ids:
            blockers.append("FINAL_CHECKS_INCOMPLETE")
        if unresolved_parts:
            blockers.append("PARTS_UNRESOLVED")
        if not (proof.resolution_summary or "").strip():
            blockers.append("RESOLUTION_SUMMARY_REQUIRED")

        can_submit = work_finished and proof.status == "draft" and not blockers

        allowed_actions: list[str] = []
        if not is_terminal and work_finished and proof.status == "draft":
            allowed_actions.append("save_draft")
            if can_submit:
                allowed_actions.append("submit_proof")
        if proof.status == "submitted" and proof.handover_status in ("not_requested",):
            allowed_actions.append("request_handover")
        if proof.status == "submitted" and proof.handover_status == "requested":
            allowed_actions.append("send_reminder")
            allowed_actions.append("mark_customer_unavailable")

        return {
            "job": {"job_id": str(job.id), "job_reference": job.job_number, "workflow_status": job.status, "is_terminal": is_terminal},
            "work_summary": work_summary,
            "proof": _proof_view(proof),
            "definition": {"final_checks": final_checks["items"], "customer_handover_required": True},
            "parts_used": parts,
            "readiness": {
                "can_submit": can_submit,
                "missing_check_ids": missing_check_ids,
                # Always empty now that evidence is optional; kept because the
                # installed mobile app reads it on every render.
                "missing_evidence_categories": [],
                "unresolved_parts": unresolved_parts,
                "blockers": blockers,
            },
            "final_checks_progress": {"required_total": final_checks["required_total"], "required_completed": final_checks["required_completed"]},
            "allowed_actions": allowed_actions,
        }

    # ── Mutations ─────────────────────────────────────────────────────────

    async def save_draft(self, db: AsyncSession, user_id: uuid.UUID, tenant_id: uuid.UUID, job_id: uuid.UUID, resolution_summary: str | None, final_service_notes: str | None) -> dict:
        job, staff_id = await self._get_assigned_job(db, user_id, tenant_id, job_id)
        proof = await self._get_or_create_proof(db, job, staff_id)
        if proof.status != "draft":
            raise ServiceOSException("COMPLETION_PROOF_IMMUTABLE", "Submitted completion proof cannot be edited.", status_code=409)
        if resolution_summary is not None:
            proof.resolution_summary = resolution_summary
        if final_service_notes is not None:
            proof.final_service_notes = final_service_notes
        db.add(proof)
        await db.commit()
        return _proof_view(proof)

    async def add_evidence(self, db: AsyncSession, user_id: uuid.UUID, tenant_id: uuid.UUID, job_id: uuid.UUID, category: str, file_id: str) -> dict:
        if category not in ("before", "after"):
            raise ServiceOSException("VALIDATION_ERROR", "category must be 'before' or 'after'.", status_code=422)
        job, staff_id = await self._get_assigned_job(db, user_id, tenant_id, job_id)
        proof = await self._get_or_create_proof(db, job, staff_id)
        if proof.status != "draft":
            raise ServiceOSException("COMPLETION_PROOF_IMMUTABLE", "Submitted completion proof cannot be edited.", status_code=409)
        field = "before_photo_ids" if category == "before" else "after_photo_ids"
        current = list(getattr(proof, field) or [])
        if file_id not in current:
            current.append(file_id)
        setattr(proof, field, current)
        db.add(proof)
        await db.commit()
        return _proof_view(proof)

    async def remove_evidence(self, db: AsyncSession, user_id: uuid.UUID, tenant_id: uuid.UUID, job_id: uuid.UUID, category: str, file_id: str) -> dict:
        job, staff_id = await self._get_assigned_job(db, user_id, tenant_id, job_id)
        proof = await self._get_or_create_proof(db, job, staff_id)
        if proof.status != "draft":
            raise ServiceOSException("COMPLETION_PROOF_IMMUTABLE", "Submitted completion proof cannot be edited.", status_code=409)
        field = "before_photo_ids" if category == "before" else "after_photo_ids"
        current = [f for f in (getattr(proof, field) or []) if f != file_id]
        setattr(proof, field, current)
        db.add(proof)
        await db.commit()
        return _proof_view(proof)

    async def submit(self, db: AsyncSession, user_id: uuid.UUID, tenant_id: uuid.UUID, job_id: uuid.UUID) -> dict:
        job, staff_id = await self._get_assigned_job(db, user_id, tenant_id, job_id)
        detail = await self.get_detail(db, user_id, tenant_id, job_id)
        if not detail["readiness"]["can_submit"]:
            raise ServiceOSException("COMPLETION_PROOF_NOT_READY", "Complete every required item before submitting.", status_code=409, context={"blockers": detail["readiness"]["blockers"]})
        proof = await self._get_or_create_proof(db, job, staff_id)
        proof.status = "submitted"
        proof.submitted_by = user_id
        proof.submitted_at = _now()
        db.add(proof)
        # Invoice generation is a required part of native closure, not an
        # optional staff-portal action. Keep it atomic with proof submission so
        # the payment screen and every admin/customer invoice projection read
        # the same immutable financial snapshot.
        from app.engines.invoice_payment.invoice_service import ServiceInvoiceService
        await ServiceInvoiceService().ensure_issued_for_job(
            db, str(job.id), str(tenant_id), str(user_id),
            request_id=None, notify_customer=True,
        )
        await db.commit()
        return _proof_view(proof)

    async def request_handover(self, db: AsyncSession, user_id: uuid.UUID, tenant_id: uuid.UUID, job_id: uuid.UUID) -> dict:
        job, staff_id = await self._get_assigned_job(db, user_id, tenant_id, job_id)
        proof = await self._get_or_create_proof(db, job, staff_id)
        if proof.status != "submitted":
            raise ServiceOSException("COMPLETION_PROOF_NOT_SUBMITTED", "Submit completion proof before requesting customer handover.", status_code=409)
        if proof.handover_status == "not_requested":
            proof.handover_status = "requested"
            proof.handover_requested_at = _now()
            db.add(proof)
            await db.commit()
        return _proof_view(proof)

    async def send_reminder(self, db: AsyncSession, user_id: uuid.UUID, tenant_id: uuid.UUID, job_id: uuid.UUID) -> dict:
        job, staff_id = await self._get_assigned_job(db, user_id, tenant_id, job_id)
        proof = await self._get_or_create_proof(db, job, staff_id)
        if proof.handover_status != "requested":
            raise ServiceOSException("HANDOVER_NOT_REQUESTED", "Request customer handover before sending a reminder.", status_code=409)
        if proof.handover_last_reminder_at is not None:
            elapsed = (_now() - proof.handover_last_reminder_at).total_seconds()
            if elapsed < _HANDOVER_REMINDER_COOLDOWN_SECONDS:
                raise ServiceOSException("HANDOVER_REMINDER_RATE_LIMITED", "A reminder was already sent recently.", status_code=429)
        proof.handover_last_reminder_at = _now()
        db.add(proof)
        await db.commit()
        return _proof_view(proof)

    async def acknowledge_handover(self, db: AsyncSession, customer_id: uuid.UUID, job_id: uuid.UUID) -> dict:
        """Customer-side counterpart to request_handover -- found genuinely
        missing entirely during the Final Phase end-to-end pass: no
        endpoint anywhere let a customer acknowledge handover, which
        permanently blocked closure (CUSTOMER_HANDOVER_NOT_ACKNOWLEDGED)
        for every real Home Services job in the system."""
        from app.engines.final_records.models import ServiceJob
        job = await db.get(ServiceJob, job_id)
        if not job or str(job.customer_id) != str(customer_id):
            raise ServiceOSException("ENTITY_NOT_FOUND", "Job not found.", status_code=404)
        res = await db.execute(select(CompletionProof).where(CompletionProof.job_id == job.id))
        proof = res.scalars().first()
        if proof is None or proof.handover_status not in ("requested", "customer_unavailable"):
            raise ServiceOSException("HANDOVER_NOT_REQUESTED", "No handover has been requested for this job yet.", status_code=409)
        proof.handover_status = "acknowledged"
        db.add(proof)
        await db.commit()
        return _proof_view(proof)

    async def get_customer_handover(self, db: AsyncSession, customer_id: uuid.UUID, job_id: uuid.UUID) -> dict:
        """Return the customer-safe handover state without creating a proof.

        The technician projection can create a draft while preparing completion,
        but a customer merely opening Booking Details must remain read-only.
        """
        from app.engines.final_records.models import ServiceJob
        job = await db.get(ServiceJob, job_id)
        if not job or str(job.customer_id) != str(customer_id):
            raise ServiceOSException("ENTITY_NOT_FOUND", "Job not found.", status_code=404)
        res = await db.execute(select(CompletionProof).where(CompletionProof.job_id == job.id))
        proof = res.scalars().first()
        return {
            "job_id": str(job.id),
            "status": proof.handover_status if proof else "not_requested",
            "requested_at": proof.handover_requested_at.isoformat() if proof and proof.handover_requested_at else None,
            "can_acknowledge": bool(proof and proof.handover_status in ("requested", "customer_unavailable")),
        }

    async def mark_customer_unavailable(self, db: AsyncSession, user_id: uuid.UUID, tenant_id: uuid.UUID, job_id: uuid.UUID) -> dict:
        job, staff_id = await self._get_assigned_job(db, user_id, tenant_id, job_id)
        proof = await self._get_or_create_proof(db, job, staff_id)
        if proof.status != "submitted":
            raise ServiceOSException("COMPLETION_PROOF_NOT_SUBMITTED", "Submit completion proof first.", status_code=409)
        proof.handover_status = "customer_unavailable"
        db.add(proof)
        await db.commit()
        return _proof_view(proof)
