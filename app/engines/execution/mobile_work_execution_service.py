"""Technician Mobile App Phase M — Work Execution projection + technician-
authorized wrappers over EXISTING canonical services. Never a second
job-status graph: `ServiceJob.status` (via `HomeServiceJobExecutionService`)
remains the sole workflow authority. `WorkSession` (work_session_service.py)
is supplementary elapsed-time evidence only.

Start Work / Finish Work reuse the EXISTING, already-gated
`start_service`/`mark_work_done` methods verbatim -- this module adds only
the technician-scoped work-session bookkeeping around them, never
duplicates the approval/checklist/monetization gates already enforced
inside `_set_status`.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ServiceOSException
from app.engines.execution.constants import JS_SERVICE_STARTED, JS_WORK_DONE
from app.engines.execution.home_service_service import HomeServiceJobExecutionService
from app.engines.execution.work_session_service import WorkSessionService, STATE_ACTIVE, STATE_PAUSED

_TERMINAL_STATUSES = {"completed", "cancelled", "failed", "closed_estimate_declined"}
_PARTS_PENDING_STATUSES = {"requested", "customer_approval_pending"}

_exec_svc = HomeServiceJobExecutionService()
_session_svc = WorkSessionService()


class MobileWorkExecutionService:
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

    async def _approved_scope(self, db: AsyncSession, job) -> dict | None:
        from app.engines.quote_checklist.quote_service import ServiceJobQuoteService
        from app.engines.quote_checklist.constants import QS_CUSTOMER_APPROVED
        quotes = await ServiceJobQuoteService().list_quotes_for_job(db, str(job.id), str(job.tenant_id))
        current = next((q for q in quotes if q["is_current"]), None)
        if not current or current["status"] != QS_CUSTOMER_APPROVED:
            return None
        return {
            "quote_id": current["id"], "version_number": current["version_number"],
            "approved_total": current["total_amount"], "currency": current["currency"],
            "approved_at": current["approved_at"], "scope_locked": True,
        }

    async def _checklist(self, db: AsyncSession, job) -> dict:
        from app.engines.checklist_catalog import service as checklist_svc
        from app.engines.checklist_catalog import constants as c

        mappings = await checklist_svc.get_applicable_mappings(db, job, phase=c.PURPOSE_EXECUTION)
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

    async def get_detail(self, db: AsyncSession, user_id: uuid.UUID, tenant_id: uuid.UUID, job_id: uuid.UUID) -> dict:
        job, _ = await self._get_assigned_job(db, user_id, tenant_id, job_id)
        approved_scope = await self._approved_scope(db, job)
        checklist = await self._checklist(db, job)

        session = await _session_svc.get(db, job.id)
        session_dict = session.to_dict() if session else None
        if session_dict is not None:
            session_dict["accumulated_seconds"] = _session_svc.elapsed_seconds(session)

        from app.engines.execution.models import PartsRequest
        parts = [p.to_dict() for p in (await db.execute(
            select(PartsRequest).where(PartsRequest.job_id == job.id).order_by(PartsRequest.created_at.desc())
        )).scalars().all()]
        pending_part_ids = [p["parts_request_id"] for p in parts if p["status"] in _PARTS_PENDING_STATUSES]

        missing_checklist_ids = [i["id"] for i in checklist["items"] if i["is_required"] and (i["response"] is None or i["response"]["response_value"] in (None, {}, ""))]

        blockers = []
        is_terminal = job.status in _TERMINAL_STATUSES
        if job.status == JS_WORK_DONE:
            blockers.append("WORK_ALREADY_FINISHED")
        if missing_checklist_ids:
            blockers.append("CHECKLIST_INCOMPLETE")
        if pending_part_ids:
            blockers.append("PART_APPROVAL_PENDING")

        can_finish_work = (
            job.status == JS_SERVICE_STARTED and session is not None
            and not missing_checklist_ids and not pending_part_ids
        )

        allowed_actions: list[str] = []
        if not is_terminal:
            if job.status != JS_SERVICE_STARTED and job.status != JS_WORK_DONE:
                allowed_actions.append("start_work")
            elif job.status == JS_SERVICE_STARTED:
                if session is None or session.state == STATE_PAUSED:
                    allowed_actions.append("resume_work" if session is not None else "start_work")
                elif session.state == STATE_ACTIVE:
                    allowed_actions.append("pause_work")
                    if can_finish_work:
                        allowed_actions.append("finish_work")

        return {
            "job": {
                "job_id": str(job.id), "job_reference": job.job_number,
                "workflow_status": job.status, "is_terminal": is_terminal,
            },
            "approved_scope": approved_scope,
            "work_session": session_dict,
            "checklist": checklist,
            "parts": parts,
            "readiness": {
                "can_finish_work": can_finish_work,
                "missing_checklist_item_ids": missing_checklist_ids,
                "pending_part_request_ids": pending_part_ids,
                "missing_evidence_categories": [],
                "blockers": blockers,
            },
            "allowed_actions": allowed_actions,
        }

    # ── Mutations ─────────────────────────────────────────────────────────

    async def start_work(self, db: AsyncSession, user_id: uuid.UUID, tenant_id: uuid.UUID, job_id: uuid.UUID, request_id: str | None) -> dict:
        job, staff_id = await self._get_assigned_job(db, user_id, tenant_id, job_id)
        if job.status != JS_SERVICE_STARTED:
            # Reuses the EXISTING, already-gated transition verbatim -- approval,
            # pre-work checklist and platform-fee gates all enforced inside.
            await _exec_svc.start_service(db, job.id, tenant_id, staff_id, user_id, request_id=request_id)
            await db.commit()
        session = await _session_svc.start_or_resume(db, job.id, tenant_id, staff_id)
        await db.commit()
        return session.to_dict()

    async def pause_work(self, db: AsyncSession, user_id: uuid.UUID, tenant_id: uuid.UUID, job_id: uuid.UUID, reason: str | None) -> dict:
        await self._get_assigned_job(db, user_id, tenant_id, job_id)
        session = await _session_svc.pause(db, job_id, reason)
        await db.commit()
        return session.to_dict()

    async def resume_work(self, db: AsyncSession, user_id: uuid.UUID, tenant_id: uuid.UUID, job_id: uuid.UUID) -> dict:
        job, staff_id = await self._get_assigned_job(db, user_id, tenant_id, job_id)
        session = await _session_svc.start_or_resume(db, job.id, tenant_id, staff_id)
        await db.commit()
        return session.to_dict()

    async def finish_work(self, db: AsyncSession, user_id: uuid.UUID, tenant_id: uuid.UUID, job_id: uuid.UUID, request_id: str | None) -> dict:
        job, staff_id = await self._get_assigned_job(db, user_id, tenant_id, job_id)
        detail = await self.get_detail(db, user_id, tenant_id, job_id)
        if not detail["readiness"]["can_finish_work"]:
            raise ServiceOSException("WORK_NOT_READY_TO_FINISH", "Complete every required item before finishing work.", status_code=409, context={"blockers": detail["readiness"]["blockers"]})

        # The mobile work screen saves item responses inline and exposes one
        # final "Finish work" action; it has no separate complete-checklist
        # action. Previously this moved the job to work_done while leaving the
        # canonical checklist instance IN_PROGRESS. The later completion gate
        # then blocked payment finalization forever even though every required
        # answer was present. Make the user-visible action atomic: validate and
        # complete its resolved EXECUTION instance before advancing the job.
        checklist_instance_id = (detail.get("checklist") or {}).get("instance_id")
        if checklist_instance_id:
            from app.engines.checklist_catalog.models import JobChecklistInstance
            from app.engines.checklist_catalog.service import complete_instance

            instance = await db.get(JobChecklistInstance, uuid.UUID(str(checklist_instance_id)))
            if instance is None or instance.job_id != job.id or instance.tenant_id != tenant_id:
                raise ServiceOSException(
                    "CHECKLIST_INSTANCE_NOT_FOUND",
                    "The work checklist could not be resolved for this job.",
                    status_code=409,
                )
            await complete_instance(db, instance, completed_by=user_id)

        await _session_svc.finish(db, job.id)
        # Reuses the EXISTING mark_work_done transition verbatim -- moves the
        # job to work_done only, never triggers completion/commission (those
        # fire exclusively from the separate, later complete_job action).
        result = await _exec_svc.mark_work_done(db, job.id, tenant_id, staff_id, user_id, request_id=request_id)
        await db.commit()
        return result
