"""Technician Mobile App Phase L — Estimate Builder read projection +
technician-authorized wrapper around the EXISTING, already-tested
`ServiceJobQuoteService` (app/engines/quote_checklist/quote_service.py).

This module never recomputes a total, never introduces a second quote
status graph, and never stores estimate data of its own -- it only adds the
authorization layer (session/tenant/technician/assignment) the canonical
quote service does not itself perform (that engine's own staff_router uses
`require_owner_or_office_staff_mutation`, which explicitly excludes
technicians -- see provider_router.py's own docstring), and projects the
canonical quote/job/inspection state into the shape the mobile screen needs
in one call.

Visit-fee: no automated visit-fee application exists anywhere in the
canonical quote engine today (audited) -- `visit_charge` is a defined item
type but is not summed into any total bucket by `_recalculate`. Rather than
fabricate a new pricing engine, `create_estimate` below seeds exactly one
real `discount`-type line item (the only item type `_recalculate` actually
subtracts) using the job's REAL catalog `MasterService.visit_fee`, once, at
quote creation -- never recalculated client-side, never hardcoded.
"""
from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ServiceOSException
from app.engines.quote_checklist.quote_service import ServiceJobQuoteService, ITEM_EDITABLE_QUOTE_STATUSES
from app.engines.quote_checklist.constants import ITEM_TYPE_DISCOUNT, QS_REVISION_REQUESTED

_TERMINAL_STATUSES = {"completed", "cancelled", "failed", "closed_estimate_declined"}
_VISIT_FEE_ITEM_NAME = "Visit fee adjustment"

_quote_svc = ServiceJobQuoteService()


def _fail_not_found() -> ServiceOSException:
    return ServiceOSException("ENTITY_NOT_FOUND", "Job not found.", status_code=404)


def _map_value_error(exc: ValueError) -> ServiceOSException:
    code = str(exc.args[0]) if exc.args else "QUOTE_ERROR"
    status = 404 if code in ("QUOTE_NOT_FOUND", "QUOTE_JOB_NOT_FOUND") else 403 if code == "QUOTE_ACCESS_DENIED" else 422
    return ServiceOSException(code, code.replace("_", " ").capitalize() + ".", status_code=status)


class MobileEstimateService:
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
            raise _fail_not_found()
        if str(job.assigned_staff_id) not in (str(staff_id), str(user_id)):
            raise ServiceOSException("ENTITY_NOT_ASSIGNED", "This job is not assigned to you.", status_code=403)
        return job

    async def _resolve_visit_fee(self, db: AsyncSession, job) -> Decimal | None:
        from app.engines.admin_catalog.models import MasterService
        if not job.offering_id:
            return None
        service = await db.get(MasterService, job.offering_id)
        if not service or not service.visit_fee or service.visit_fee <= 0:
            return None
        return Decimal(str(service.visit_fee))

    async def _inspection_source(self, db: AsyncSession, job) -> dict:
        from app.engines.checklist_catalog import service as checklist_svc
        from app.engines.checklist_catalog import constants as c

        mappings = await checklist_svc.get_applicable_mappings(db, job, phase=c.PURPOSE_INSPECTION)
        if not mappings:
            return {"completed": False, "diagnosis_summary": None, "evidence_count": 0}
        mapping = next((m for m in mappings if m.usage == c.USAGE_REQUIRED), mappings[0])
        instance = await checklist_svc.ensure_instance(db, job, mapping)
        items = await checklist_svc._instance_items(db, instance)
        from app.engines.checklist_catalog.models import JobChecklistResponse
        responses = {
            r.checklist_item_id: r for r in (await db.execute(
                select(JobChecklistResponse).where(JobChecklistResponse.job_checklist_instance_id == instance.id)
            )).scalars().all()
        }
        diagnosis_labels: list[str] = []
        evidence_count = 0
        for item in items:
            resp = responses.get(item.id)
            if not resp:
                continue
            evidence_count += len(resp.evidence or [])
            if item.item_type in ("SINGLE_SELECT", "MULTI_SELECT") and item.select_options:
                by_value = {o["value"]: o["label"] for o in item.select_options}
                values = resp.response_value.get("values") or ([resp.response_value.get("value")] if resp.response_value and resp.response_value.get("value") else [])
                diagnosis_labels.extend(by_value.get(v, v) for v in values if v)
        return {
            "completed": instance.state == c.INSTANCE_COMPLETED,
            "instance_id": str(instance.id),
            "diagnosis_summary": ", ".join(diagnosis_labels) if diagnosis_labels else None,
            "evidence_count": evidence_count,
        }

    async def get_detail(self, db: AsyncSession, user_id: uuid.UUID, tenant_id: uuid.UUID, job_id: uuid.UUID) -> dict:
        job = await self._get_assigned_job(db, user_id, tenant_id, job_id)
        inspection_source = await self._inspection_source(db, job)
        visit_fee = await self._resolve_visit_fee(db, job)

        quotes = await _quote_svc.list_quotes_for_job(db, str(job.id), str(tenant_id))
        current = next((q for q in quotes if q["is_current"]), None)
        quote_detail = None
        if current:
            quote_detail = await _quote_svc.get_quote(db, current["id"], tenant_id=str(tenant_id))

        readiness = self._build_readiness(quote_detail, inspection_source)
        allowed_actions = self._build_allowed_actions(quote_detail, readiness, job)

        return {
            "job": {
                "job_id": str(job.id), "job_reference": job.job_number,
                "workflow_status": job.status, "is_terminal": job.status in _TERMINAL_STATUSES,
            },
            "inspection_source": inspection_source,
            "quote": self._project_quote(quote_detail),
            "calculation": self._project_calculation(quote_detail),
            "visit_fee_policy": {
                "amount": float(visit_fee) if visit_fee is not None else None,
                "currency": "INR", "disposition": "not_tracked" if visit_fee is not None else "unavailable",
            },
            "readiness": readiness,
            "next_approval_target": "customer",
            "allowed_actions": allowed_actions,
            "server_timestamp": None,
        }

    def _project_quote(self, quote: dict | None) -> dict | None:
        if not quote:
            return None
        return {
            "quote_id": quote["id"], "version_number": quote["version_number"], "is_current": quote["is_current"],
            "status": quote["status"], "quote_type": quote["quote_type"],
            "line_items": [
                {
                    "id": i["id"], "item_type": i["item_type"], "item_name": i["item_name"],
                    "item_description": i["item_description"], "quantity": i["quantity"],
                    "unit_price": i["unit_price"], "line_total": i["line_total"],
                    "is_customer_visible": i["is_customer_visible"],
                }
                for i in quote.get("items", [])
            ],
            "valid_until": quote.get("expires_at"), "customer_notes": quote.get("customer_visible_notes"),
        }

    def _project_calculation(self, quote: dict | None) -> dict:
        if not quote:
            return {"currency": "INR", "labour_total": "0", "parts_total": "0", "subtotal": "0",
                    "visit_fee_adjustment": "0", "tax_total": "0", "grand_total": "0"}
        subtotal = str(Decimal(quote["labour_amount"]) + Decimal(quote["parts_amount"]) + Decimal(quote["service_amount"]))
        return {
            "currency": quote["currency"], "labour_total": quote["labour_amount"], "parts_total": quote["parts_amount"],
            "subtotal": subtotal, "visit_fee_adjustment": f"-{quote['discount_amount']}",
            "tax_total": quote["tax_amount"], "grand_total": quote["total_amount"],
        }

    def _build_readiness(self, quote: dict | None, inspection_source: dict) -> dict:
        blockers = []
        if not inspection_source["completed"]:
            blockers.append("INSPECTION_NOT_COMPLETE")
        can_save = not blockers
        can_submit = bool(quote and quote.get("items")) and can_save and (not quote or quote["status"] in ITEM_EDITABLE_QUOTE_STATUSES)
        return {"can_save": can_save, "can_submit": can_submit, "blockers": blockers}

    def _build_allowed_actions(self, quote: dict | None, readiness: dict, job) -> list[str]:
        if job.status in _TERMINAL_STATUSES:
            return []
        if quote is None:
            return ["create_estimate"] if readiness["can_save"] else []
        actions = []
        if quote["status"] in ITEM_EDITABLE_QUOTE_STATUSES and quote["is_current"]:
            actions.append("edit_estimate")
            if readiness["can_submit"]:
                actions.append("send_for_approval")
        if quote["status"] == QS_REVISION_REQUESTED and quote["is_current"]:
            actions.append("create_revision")
        return actions

    # ── Mutations (thin technician-authorized wrappers over the canonical service) ──

    async def create_estimate(self, db: AsyncSession, user_id: uuid.UUID, tenant_id: uuid.UUID, job_id: uuid.UUID, request_id: str | None) -> dict:
        job = await self._get_assigned_job(db, user_id, tenant_id, job_id)
        staff_id = await self._resolve_staff_member_id(db, user_id)
        try:
            quote = await _quote_svc.create_quote(
                db, str(job.id), str(tenant_id), "repair_quote", str(user_id), str(staff_id), None, request_id,
            )
            visit_fee = await self._resolve_visit_fee(db, job)
            if visit_fee is not None:
                await _quote_svc.add_item(
                    db, quote["id"], str(tenant_id), ITEM_TYPE_DISCOUNT, _VISIT_FEE_ITEM_NAME,
                    "Adjusted into the final amount if the customer continues with the work.",
                    1, float(visit_fee), True, True, str(user_id), request_id,
                )
                quote = await _quote_svc.get_quote(db, quote["id"], tenant_id=str(tenant_id))
        except ValueError as exc:
            raise _map_value_error(exc)
        return quote

    async def create_revision(self, db: AsyncSession, user_id: uuid.UUID, tenant_id: uuid.UUID, job_id: uuid.UUID, current_quote_id: str, request_id: str | None) -> dict:
        job = await self._get_assigned_job(db, user_id, tenant_id, job_id)
        staff_id = await self._resolve_staff_member_id(db, user_id)
        try:
            await _quote_svc.mark_revised(db, current_quote_id, str(tenant_id), str(user_id), request_id)
            new_quote = await _quote_svc.create_quote(
                db, str(job.id), str(tenant_id), "repair_quote", str(user_id), str(staff_id), None, request_id,
            )
        except ValueError as exc:
            raise _map_value_error(exc)
        return new_quote

    async def add_item(self, db, user_id, tenant_id, job_id, quote_id, item_type, item_name, item_description, quantity, unit_price, is_customer_visible, request_id):
        await self._get_assigned_job(db, user_id, tenant_id, job_id)
        try:
            return await _quote_svc.add_item(
                db, quote_id, str(tenant_id), item_type, item_name, item_description,
                quantity, unit_price, True, is_customer_visible, str(user_id), request_id,
            )
        except ValueError as exc:
            raise _map_value_error(exc)

    async def update_item(self, db, user_id, tenant_id, job_id, quote_id, item_id, item_name, item_description, quantity, unit_price, is_customer_visible, request_id):
        await self._get_assigned_job(db, user_id, tenant_id, job_id)
        try:
            return await _quote_svc.update_item(
                db, quote_id, item_id, str(tenant_id), item_name, item_description,
                quantity, unit_price, is_customer_visible, str(user_id), request_id,
            )
        except ValueError as exc:
            raise _map_value_error(exc)

    async def remove_item(self, db, user_id, tenant_id, job_id, quote_id, item_id, request_id):
        await self._get_assigned_job(db, user_id, tenant_id, job_id)
        try:
            return await _quote_svc.remove_item(db, quote_id, item_id, str(tenant_id), str(user_id), request_id)
        except ValueError as exc:
            raise _map_value_error(exc)

    async def send_for_approval(self, db, user_id, tenant_id, job_id, quote_id, customer_notes, request_id):
        await self._get_assigned_job(db, user_id, tenant_id, job_id)
        try:
            return await _quote_svc.send_to_customer(db, quote_id, str(tenant_id), customer_notes, str(user_id), request_id)
        except ValueError as exc:
            raise _map_value_error(exc)
