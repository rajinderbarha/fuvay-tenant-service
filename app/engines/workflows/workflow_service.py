"""Workflow Templates Enterprise Service — migration 106."""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Any

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger("workflows.service")

# ── seed data ─────────────────────────────────────────────────────────────────
_STANDARD_REPAIR_STEPS = [
    {"id": "s1", "step_key": "booking_created", "step_name": "Booking Created", "step_type": "customer_action", "owner_app": "customer_app", "owner_role": "customer", "customer_visible": True, "tenant_visible": False, "staff_visible": False, "admin_visible": True, "requires_notes": False, "requires_photo": False, "requires_payment_record": False, "requires_approval": False, "sla_enabled": False, "audit_required": False, "display_order": 1},
    {"id": "s2", "step_key": "pending_provider_acceptance", "step_name": "Pending Provider Acceptance", "step_type": "tenant_action", "owner_app": "tenant_app", "owner_role": "tenant_owner", "customer_visible": False, "tenant_visible": True, "staff_visible": False, "admin_visible": True, "requires_notes": False, "requires_photo": False, "requires_payment_record": False, "requires_approval": False, "sla_enabled": True, "audit_required": False, "display_order": 2},
    {"id": "s3", "step_key": "provider_accepted", "step_name": "Provider Accepted", "step_type": "tenant_action", "owner_app": "tenant_app", "owner_role": "tenant_owner", "customer_visible": True, "tenant_visible": True, "staff_visible": False, "admin_visible": True, "requires_notes": False, "requires_photo": False, "requires_payment_record": False, "requires_approval": False, "sla_enabled": False, "audit_required": False, "display_order": 3},
    {"id": "s4", "step_key": "technician_assigned", "step_name": "Technician Assigned", "step_type": "tenant_action", "owner_app": "tenant_app", "owner_role": "tenant_manager", "customer_visible": True, "tenant_visible": True, "staff_visible": True, "admin_visible": True, "requires_notes": False, "requires_photo": False, "requires_payment_record": False, "requires_approval": False, "sla_enabled": False, "audit_required": False, "display_order": 4},
    {"id": "s5", "step_key": "on_the_way", "step_name": "On The Way", "step_type": "staff_action", "owner_app": "staff_app", "owner_role": "technician", "customer_visible": True, "tenant_visible": True, "staff_visible": True, "admin_visible": True, "requires_notes": False, "requires_photo": False, "requires_payment_record": False, "requires_approval": False, "sla_enabled": False, "audit_required": False, "display_order": 5},
    {"id": "s6", "step_key": "arrived", "step_name": "Arrived", "step_type": "staff_action", "owner_app": "staff_app", "owner_role": "technician", "customer_visible": True, "tenant_visible": True, "staff_visible": True, "admin_visible": True, "requires_notes": False, "requires_photo": False, "requires_payment_record": False, "requires_approval": False, "sla_enabled": False, "audit_required": False, "display_order": 6},
    {"id": "s7", "step_key": "work_started", "step_name": "Work Started", "step_type": "staff_action", "owner_app": "staff_app", "owner_role": "technician", "customer_visible": False, "tenant_visible": True, "staff_visible": True, "admin_visible": True, "requires_notes": False, "requires_photo": False, "requires_payment_record": False, "requires_approval": False, "sla_enabled": True, "audit_required": False, "display_order": 7},
    {"id": "s8", "step_key": "work_completed", "step_name": "Work Completed", "step_type": "staff_action", "owner_app": "staff_app", "owner_role": "technician", "customer_visible": True, "tenant_visible": True, "staff_visible": True, "admin_visible": True, "requires_notes": True, "requires_photo": True, "requires_payment_record": False, "requires_approval": False, "sla_enabled": False, "audit_required": True, "display_order": 8},
    {"id": "s9", "step_key": "payment_recorded", "step_name": "Payment Recorded", "step_type": "staff_action", "owner_app": "staff_app", "owner_role": "technician", "customer_visible": True, "tenant_visible": True, "staff_visible": True, "admin_visible": True, "requires_notes": False, "requires_photo": False, "requires_payment_record": True, "requires_approval": False, "sla_enabled": False, "audit_required": True, "display_order": 9},
    {"id": "s10", "step_key": "job_completed", "step_name": "Job Completed", "step_type": "system_action", "owner_app": "system", "owner_role": "system", "customer_visible": True, "tenant_visible": True, "staff_visible": True, "admin_visible": True, "requires_notes": False, "requires_photo": False, "requires_payment_record": False, "requires_approval": False, "sla_enabled": False, "audit_required": True, "display_order": 10},
    {"id": "s11", "step_key": "review_requested", "step_name": "Review Requested", "step_type": "customer_action", "owner_app": "customer_app", "owner_role": "customer", "customer_visible": True, "tenant_visible": False, "staff_visible": False, "admin_visible": True, "requires_notes": False, "requires_photo": False, "requires_payment_record": False, "requires_approval": False, "sla_enabled": False, "audit_required": False, "display_order": 11},
]

_STANDARD_REPAIR_TRANSITIONS = [
    {"id": "t1", "from_step_key": "booking_created", "to_step_key": "pending_provider_acceptance", "action_label": "Confirm Booking", "allowed_role": "system", "requires_reason": False, "triggers_notification": True},
    {"id": "t2", "from_step_key": "pending_provider_acceptance", "to_step_key": "provider_accepted", "action_label": "Accept Booking", "allowed_role": "tenant_owner", "requires_reason": False, "triggers_notification": True},
    {"id": "t3", "from_step_key": "provider_accepted", "to_step_key": "technician_assigned", "action_label": "Assign Technician", "allowed_role": "tenant_manager", "requires_reason": False, "triggers_notification": True},
    {"id": "t4", "from_step_key": "technician_assigned", "to_step_key": "on_the_way", "action_label": "Start Travel", "allowed_role": "technician", "requires_reason": False, "triggers_notification": True},
    {"id": "t5", "from_step_key": "on_the_way", "to_step_key": "arrived", "action_label": "Mark Arrived", "allowed_role": "technician", "requires_reason": False, "triggers_notification": False},
    {"id": "t6", "from_step_key": "arrived", "to_step_key": "work_started", "action_label": "Start Work", "allowed_role": "technician", "requires_reason": False, "triggers_notification": False},
    {"id": "t7", "from_step_key": "work_started", "to_step_key": "work_completed", "action_label": "Complete Work", "allowed_role": "technician", "requires_reason": False, "triggers_notification": True},
    {"id": "t8", "from_step_key": "work_completed", "to_step_key": "payment_recorded", "action_label": "Record Payment", "allowed_role": "technician", "requires_reason": False, "triggers_notification": False},
    {"id": "t9", "from_step_key": "payment_recorded", "to_step_key": "job_completed", "action_label": "Complete Job", "allowed_role": "technician", "requires_reason": False, "triggers_notification": True},
    {"id": "t10", "from_step_key": "job_completed", "to_step_key": "review_requested", "action_label": "Request Review", "allowed_role": "system", "requires_reason": False, "triggers_notification": True},
]

_SEED_WORKFLOWS: list[dict] = [
    # Home Services
    {"workflow_key": "standard_repair_workflow", "name": "Standard Repair Workflow", "vertical_key": "home_services", "workflow_type": "repair", "description": "Standard multi-step repair workflow for home service jobs.", "steps_json": _STANDARD_REPAIR_STEPS, "transitions_json": _STANDARD_REPAIR_TRANSITIONS},
    {"workflow_key": "standard_installation_workflow", "name": "Standard Installation Workflow", "vertical_key": "home_services", "workflow_type": "installation", "description": "Standard installation workflow.", "steps_json": [], "transitions_json": []},
    {"workflow_key": "standard_uninstallation_workflow", "name": "Standard Uninstallation Workflow", "vertical_key": "home_services", "workflow_type": "uninstallation", "description": "Standard uninstallation workflow.", "steps_json": [], "transitions_json": []},
    {"workflow_key": "inspection_visit_workflow", "name": "Inspection / Visit Workflow", "vertical_key": "home_services", "workflow_type": "inspection", "description": "Inspection and diagnostic visit workflow.", "steps_json": [], "transitions_json": []},
    {"workflow_key": "cleaning_workflow", "name": "Cleaning Workflow", "vertical_key": "home_services", "workflow_type": "cleaning", "description": "Professional cleaning service workflow.", "steps_json": [], "transitions_json": []},
    {"workflow_key": "emergency_repair_workflow", "name": "Emergency Repair Workflow", "vertical_key": "home_services", "workflow_type": "emergency", "description": "Expedited emergency repair workflow.", "steps_json": [], "transitions_json": []},
    # Coaching
    {"workflow_key": "lead_inquiry_workflow", "name": "Lead Inquiry Workflow", "vertical_key": "coaching", "workflow_type": "inquiry", "description": "Lead inquiry capture and routing.", "steps_json": [], "transitions_json": []},
    {"workflow_key": "demo_class_workflow", "name": "Demo Class Workflow", "vertical_key": "coaching", "workflow_type": "demo", "description": "Free demo class scheduling workflow.", "steps_json": [], "transitions_json": []},
    {"workflow_key": "admission_workflow", "name": "Admission Workflow", "vertical_key": "coaching", "workflow_type": "admission", "description": "Student admission and enrollment workflow.", "steps_json": [], "transitions_json": []},
    {"workflow_key": "counselor_followup_workflow", "name": "Counselor Follow-up Workflow", "vertical_key": "coaching", "workflow_type": "followup", "description": "Counselor follow-up cadence workflow.", "steps_json": [], "transitions_json": []},
    # Real Estate
    {"workflow_key": "property_inquiry_workflow", "name": "Property Inquiry Workflow", "vertical_key": "real_estate", "workflow_type": "inquiry", "description": "Property inquiry and lead capture.", "steps_json": [], "transitions_json": []},
    {"workflow_key": "site_visit_workflow", "name": "Site Visit Workflow", "vertical_key": "real_estate", "workflow_type": "visit", "description": "Property site visit coordination.", "steps_json": [], "transitions_json": []},
    {"workflow_key": "lead_followup_workflow", "name": "Lead Follow-up Workflow", "vertical_key": "real_estate", "workflow_type": "followup", "description": "Real estate lead nurture workflow.", "steps_json": [], "transitions_json": []},
    {"workflow_key": "listing_approval_workflow", "name": "Listing Approval Workflow", "vertical_key": "real_estate", "workflow_type": "approval", "description": "Property listing review and approval.", "steps_json": [], "transitions_json": []},
    # Restaurant
    {"workflow_key": "order_workflow", "name": "Order Workflow", "vertical_key": "restaurant", "workflow_type": "order", "description": "Customer order placement and tracking.", "steps_json": [], "transitions_json": []},
    {"workflow_key": "kitchen_preparation_workflow", "name": "Kitchen Preparation Workflow", "vertical_key": "restaurant", "workflow_type": "preparation", "description": "Kitchen order preparation workflow.", "steps_json": [], "transitions_json": []},
    {"workflow_key": "cancellation_workflow", "name": "Cancellation Workflow", "vertical_key": "restaurant", "workflow_type": "cancellation", "description": "Order cancellation and refund workflow.", "steps_json": [], "transitions_json": []},
    {"workflow_key": "issue_resolution_workflow", "name": "Issue Resolution Workflow", "vertical_key": "restaurant", "workflow_type": "complaint", "description": "Customer issue and complaint resolution.", "steps_json": [], "transitions_json": []},
    # Product
    {"workflow_key": "order_fulfillment_workflow", "name": "Order Fulfillment Workflow", "vertical_key": "product_marketplace", "workflow_type": "fulfillment", "description": "End-to-end order fulfillment workflow.", "steps_json": [], "transitions_json": []},
    {"workflow_key": "inventory_reservation_workflow", "name": "Inventory Reservation Workflow", "vertical_key": "product_marketplace", "workflow_type": "reservation", "description": "Inventory hold and reservation workflow.", "steps_json": [], "transitions_json": []},
    {"workflow_key": "shipping_workflow", "name": "Shipping Workflow", "vertical_key": "product_marketplace", "workflow_type": "shipping", "description": "Package shipping and tracking workflow.", "steps_json": [], "transitions_json": []},
    {"workflow_key": "return_workflow", "name": "Return Workflow", "vertical_key": "product_marketplace", "workflow_type": "return", "description": "Product return and refund workflow.", "steps_json": [], "transitions_json": []},
    # Professional Services
    {"workflow_key": "consultation_booking_workflow", "name": "Consultation Booking Workflow", "vertical_key": "professional_services", "workflow_type": "consultation", "description": "Professional consultation booking flow.", "steps_json": [], "transitions_json": []},
    {"workflow_key": "document_review_workflow", "name": "Document Review Workflow", "vertical_key": "professional_services", "workflow_type": "review", "description": "Document submission and review flow.", "steps_json": [], "transitions_json": []},
    {"workflow_key": "appointment_completion_workflow", "name": "Appointment Completion Workflow", "vertical_key": "professional_services", "workflow_type": "appointment", "description": "Post-appointment completion and closure.", "steps_json": [], "transitions_json": []},
]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uid() -> str:
    return str(uuid.uuid4())


def _row_to_dict(row: Any) -> dict:
    """Convert SA Row to dict."""
    if row is None:
        return {}
    return dict(row._mapping)


class WorkflowTemplateService:

    # ── Summary ────────────────────────────────────────────────────────────────
    async def get_summary(self, db: AsyncSession) -> dict:
        r = await db.execute(text("""
            SELECT
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE status = 'published') AS published,
                COUNT(*) FILTER (WHERE status = 'draft') AS draft,
                COUNT(*) FILTER (WHERE readiness_status = 'missing_mapping') AS missing_mapping,
                COUNT(*) FILTER (WHERE readiness_status = 'ready') AS runtime_ready,
                COUNT(*) FILTER (WHERE jsonb_array_length(sla_rules_json) > 0) AS sla_enabled,
                COUNT(*) FILTER (WHERE jsonb_array_length(approval_gates_json) > 0) AS approval_workflows,
                COUNT(*) FILTER (WHERE jsonb_array_length(automation_rules_json) > 0) AS automation_enabled,
                COUNT(*) FILTER (WHERE jsonb_array_length(service_mappings_json) > 0) AS used_by_services,
                COUNT(*) FILTER (WHERE runtime_health = 'failed') AS runtime_errors
            FROM workflow_templates
            WHERE archived_at IS NULL
        """))
        row = r.fetchone()
        d = _row_to_dict(row)
        return {k: (v or 0) for k, v in d.items()}

    # ── List ───────────────────────────────────────────────────────────────────
    async def list_templates(
        self, db: AsyncSession,
        q: str | None = None,
        vertical: str | None = None,
        workflow_type: str | None = None,
        status: str | None = None,
        readiness: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> dict:
        wheres = ["archived_at IS NULL"]
        params: dict = {}
        if q:
            wheres.append("(name ILIKE :q OR workflow_key ILIKE :q)")
            params["q"] = f"%{q}%"
        if vertical:
            wheres.append("vertical_key = :vertical")
            params["vertical"] = vertical
        if workflow_type:
            wheres.append("workflow_type = :workflow_type")
            params["workflow_type"] = workflow_type
        if status:
            wheres.append("status = :status")
            params["status"] = status
        if readiness:
            wheres.append("readiness_status = :readiness")
            params["readiness"] = readiness

        where_clause = " AND ".join(wheres)
        offset = (page - 1) * page_size

        count_r = await db.execute(text(f"SELECT COUNT(*) FROM workflow_templates WHERE {where_clause}"), params)
        total = count_r.scalar() or 0

        rows_r = await db.execute(text(f"""
            SELECT * FROM workflow_templates WHERE {where_clause}
            ORDER BY updated_at DESC
            LIMIT :limit OFFSET :offset
        """), {**params, "limit": page_size, "offset": offset})
        items = [_row_to_dict(r) for r in rows_r.fetchall()]
        return {
            "items": items,
            "pagination": {"total": total, "page": page, "page_size": page_size, "total_pages": max(1, -(-total // page_size))},
        }

    # ── CRUD ───────────────────────────────────────────────────────────────────
    async def create_template(self, db: AsyncSession, payload: dict, user_id: str | None = None) -> dict:
        import json
        wid = _uid()
        now = _now()
        steps = payload.get("steps_json", [])
        transitions = payload.get("transitions_json", [])
        await db.execute(text("""
            INSERT INTO workflow_templates
              (id, workflow_key, name, description, vertical_key, workflow_type, status,
               steps_json, transitions_json, created_by_user_id, created_at, updated_at)
            VALUES
              (:id, :workflow_key, :name, :desc, :vertical_key, :workflow_type, :status,
               :steps_json::jsonb, :transitions_json::jsonb, :user_id, :now, :now)
        """), {
            "id": wid,
            "workflow_key": payload["workflow_key"],
            "name": payload["name"],
            "desc": payload.get("description"),
            "vertical_key": payload.get("vertical_key", "universal"),
            "workflow_type": payload.get("workflow_type", "repair"),
            "status": payload.get("status", "draft"),
            "steps_json": json.dumps(steps),
            "transitions_json": json.dumps(transitions),
            "user_id": user_id,
            "now": now,
        })
        await db.commit()
        return await self.get_template(db, wid)

    async def get_template(self, db: AsyncSession, wid: str) -> dict:
        r = await db.execute(text("SELECT * FROM workflow_templates WHERE id = :id"), {"id": wid})
        row = r.fetchone()
        if not row:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Workflow template not found")
        return _row_to_dict(row)

    async def update_template(self, db: AsyncSession, wid: str, payload: dict, user_id: str | None = None) -> dict:
        import json
        fields = []
        params: dict = {"id": wid, "now": _now(), "user_id": user_id}
        for f in ["name", "description", "vertical_key", "workflow_type", "status"]:
            if f in payload:
                fields.append(f"{f} = :{f}")
                params[f] = payload[f]
        for jf in ["steps_json", "transitions_json", "sla_rules_json", "approval_gates_json", "automation_rules_json", "service_mappings_json"]:
            if jf in payload:
                fields.append(f"{jf} = :{jf}::jsonb")
                params[jf] = json.dumps(payload[jf])
        if not fields:
            return await self.get_template(db, wid)
        set_clause = ", ".join(fields)
        await db.execute(text(f"UPDATE workflow_templates SET {set_clause}, updated_at = :now, updated_by_user_id = :user_id WHERE id = :id"), params)
        await db.commit()
        return await self.get_template(db, wid)

    async def clone_template(self, db: AsyncSession, wid: str, user_id: str | None = None) -> dict:
        import json
        src = await self.get_template(db, wid)
        new_key = f"{src['workflow_key']}_copy_{_uid()[:8]}"
        return await self.create_template(db, {
            "workflow_key": new_key,
            "name": f"{src['name']} (Copy)",
            "description": src.get("description"),
            "vertical_key": src.get("vertical_key", "universal"),
            "workflow_type": src.get("workflow_type", "repair"),
            "status": "draft",
            "steps_json": src.get("steps_json", []),
            "transitions_json": src.get("transitions_json", []),
        }, user_id)

    async def archive_template(self, db: AsyncSession, wid: str, user_id: str | None = None) -> dict:
        await db.execute(text("""
            UPDATE workflow_templates SET archived_at = :now, status = 'archived', updated_at = :now, updated_by_user_id = :uid WHERE id = :id
        """), {"id": wid, "now": _now(), "uid": user_id})
        await self._write_audit(db, wid, "archived", user_id, None, None, None)
        await db.commit()
        return await self.get_template(db, wid)

    # ── Steps ──────────────────────────────────────────────────────────────────
    async def add_step(self, db: AsyncSession, wid: str, step_payload: dict, user_id: str | None = None) -> dict:
        import json
        tmpl = await self.get_template(db, wid)
        steps: list = list(tmpl.get("steps_json") or [])
        step = {
            "id": _uid()[:8],
            "step_key": step_payload["step_key"],
            "step_name": step_payload.get("step_name", step_payload["step_key"]),
            "step_type": step_payload.get("step_type", "staff_action"),
            "owner_app": step_payload.get("owner_app", "staff_app"),
            "owner_role": step_payload.get("owner_role", "technician"),
            "customer_visible": step_payload.get("customer_visible", False),
            "tenant_visible": step_payload.get("tenant_visible", False),
            "staff_visible": step_payload.get("staff_visible", True),
            "admin_visible": step_payload.get("admin_visible", True),
            "requires_notes": step_payload.get("requires_notes", False),
            "requires_photo": step_payload.get("requires_photo", False),
            "requires_payment_record": step_payload.get("requires_payment_record", False),
            "requires_approval": step_payload.get("requires_approval", False),
            "sla_enabled": step_payload.get("sla_enabled", False),
            "audit_required": step_payload.get("audit_required", False),
            "display_order": step_payload.get("display_order", len(steps) + 1),
        }
        steps.append(step)
        await db.execute(text("UPDATE workflow_templates SET steps_json = :s::jsonb, updated_at = :now WHERE id = :id"),
                         {"s": json.dumps(steps), "now": _now(), "id": wid})
        await self._write_audit(db, wid, "step_added", user_id, None, step, None)
        await db.commit()
        return step

    async def update_step(self, db: AsyncSession, wid: str, step_id: str, step_payload: dict, user_id: str | None = None) -> dict:
        import json
        tmpl = await self.get_template(db, wid)
        steps: list = list(tmpl.get("steps_json") or [])
        updated = None
        for i, s in enumerate(steps):
            if str(s.get("id")) == step_id:
                steps[i] = {**s, **step_payload, "id": step_id}
                updated = steps[i]
                break
        if updated is None:
            from fastapi import HTTPException
            raise HTTPException(404, "Step not found")
        await db.execute(text("UPDATE workflow_templates SET steps_json = :s::jsonb, updated_at = :now WHERE id = :id"),
                         {"s": json.dumps(steps), "now": _now(), "id": wid})
        await db.commit()
        return updated

    async def delete_step(self, db: AsyncSession, wid: str, step_id: str, user_id: str | None = None) -> None:
        import json
        tmpl = await self.get_template(db, wid)
        steps = [s for s in (tmpl.get("steps_json") or []) if str(s.get("id")) != step_id]
        await db.execute(text("UPDATE workflow_templates SET steps_json = :s::jsonb, updated_at = :now WHERE id = :id"),
                         {"s": json.dumps(steps), "now": _now(), "id": wid})
        await db.commit()

    # ── Transitions ────────────────────────────────────────────────────────────
    async def add_transition(self, db: AsyncSession, wid: str, trans_payload: dict, user_id: str | None = None) -> dict:
        import json
        tmpl = await self.get_template(db, wid)
        transitions: list = list(tmpl.get("transitions_json") or [])
        t = {
            "id": _uid()[:8],
            "from_step_key": trans_payload["from_step_key"],
            "to_step_key": trans_payload["to_step_key"],
            "action_label": trans_payload.get("action_label", ""),
            "allowed_role": trans_payload.get("allowed_role", "system"),
            "requires_reason": trans_payload.get("requires_reason", False),
            "triggers_notification": trans_payload.get("triggers_notification", False),
        }
        transitions.append(t)
        await db.execute(text("UPDATE workflow_templates SET transitions_json = :t::jsonb, updated_at = :now WHERE id = :id"),
                         {"t": json.dumps(transitions), "now": _now(), "id": wid})
        await db.commit()
        return t

    async def update_transition(self, db: AsyncSession, wid: str, trans_id: str, trans_payload: dict, user_id: str | None = None) -> dict:
        import json
        tmpl = await self.get_template(db, wid)
        transitions: list = list(tmpl.get("transitions_json") or [])
        updated = None
        for i, t in enumerate(transitions):
            if str(t.get("id")) == trans_id:
                transitions[i] = {**t, **trans_payload, "id": trans_id}
                updated = transitions[i]
                break
        if updated is None:
            from fastapi import HTTPException
            raise HTTPException(404, "Transition not found")
        await db.execute(text("UPDATE workflow_templates SET transitions_json = :t::jsonb, updated_at = :now WHERE id = :id"),
                         {"t": json.dumps(transitions), "now": _now(), "id": wid})
        await db.commit()
        return updated

    async def delete_transition(self, db: AsyncSession, wid: str, trans_id: str, user_id: str | None = None) -> None:
        import json
        tmpl = await self.get_template(db, wid)
        transitions = [t for t in (tmpl.get("transitions_json") or []) if str(t.get("id")) != trans_id]
        await db.execute(text("UPDATE workflow_templates SET transitions_json = :t::jsonb, updated_at = :now WHERE id = :id"),
                         {"t": json.dumps(transitions), "now": _now(), "id": wid})
        await db.commit()

    # ── SLA ────────────────────────────────────────────────────────────────────
    async def get_sla(self, db: AsyncSession, wid: str) -> list:
        tmpl = await self.get_template(db, wid)
        return list(tmpl.get("sla_rules_json") or [])

    async def update_sla(self, db: AsyncSession, wid: str, sla_list: list, user_id: str | None = None) -> list:
        import json
        await db.execute(text("UPDATE workflow_templates SET sla_rules_json = :s::jsonb, updated_at = :now WHERE id = :id"),
                         {"s": json.dumps(sla_list), "now": _now(), "id": wid})
        await db.commit()
        return sla_list

    # ── Approvals ──────────────────────────────────────────────────────────────
    async def get_approvals(self, db: AsyncSession, wid: str) -> list:
        tmpl = await self.get_template(db, wid)
        return list(tmpl.get("approval_gates_json") or [])

    async def update_approvals(self, db: AsyncSession, wid: str, approval_list: list, user_id: str | None = None) -> list:
        import json
        await db.execute(text("UPDATE workflow_templates SET approval_gates_json = :a::jsonb, updated_at = :now WHERE id = :id"),
                         {"a": json.dumps(approval_list), "now": _now(), "id": wid})
        await db.commit()
        return approval_list

    # ── Automation ─────────────────────────────────────────────────────────────
    async def get_automation(self, db: AsyncSession, wid: str) -> list:
        tmpl = await self.get_template(db, wid)
        return list(tmpl.get("automation_rules_json") or [])

    async def update_automation(self, db: AsyncSession, wid: str, auto_list: list, user_id: str | None = None) -> list:
        import json
        await db.execute(text("UPDATE workflow_templates SET automation_rules_json = :a::jsonb, updated_at = :now WHERE id = :id"),
                         {"a": json.dumps(auto_list), "now": _now(), "id": wid})
        await db.commit()
        return auto_list

    # ── Service Mapping ────────────────────────────────────────────────────────
    async def get_service_mapping(self, db: AsyncSession, wid: str) -> list:
        tmpl = await self.get_template(db, wid)
        return list(tmpl.get("service_mappings_json") or [])

    async def add_service_mapping(self, db: AsyncSession, wid: str, mapping_payload: dict, user_id: str | None = None) -> dict:
        import json
        tmpl = await self.get_template(db, wid)
        mappings: list = list(tmpl.get("service_mappings_json") or [])
        m = {
            "id": _uid()[:8],
            "vertical_key": mapping_payload.get("vertical_key"),
            "category_id": mapping_payload.get("category_id"),
            "service_group_id": mapping_payload.get("service_group_id"),
            "master_service_id": mapping_payload.get("master_service_id"),
            "service_type_id": mapping_payload.get("service_type_id"),
            "issue_type_id": mapping_payload.get("issue_type_id"),
            "category_name": mapping_payload.get("category_name"),
            "master_service_name": mapping_payload.get("master_service_name"),
            "status": "active",
            "created_at": _now().isoformat(),
        }
        mappings.append(m)
        # update readiness
        readiness = "ready" if len(mappings) > 0 else "missing_mapping"
        await db.execute(text("""
            UPDATE workflow_templates SET service_mappings_json = :m::jsonb,
            readiness_status = :readiness, updated_at = :now WHERE id = :id
        """), {"m": json.dumps(mappings), "readiness": readiness, "now": _now(), "id": wid})
        await db.commit()
        return m

    async def delete_service_mapping(self, db: AsyncSession, wid: str, mapping_id: str, user_id: str | None = None) -> None:
        import json
        tmpl = await self.get_template(db, wid)
        mappings = [m for m in (tmpl.get("service_mappings_json") or []) if str(m.get("id")) != mapping_id]
        readiness = "ready" if len(mappings) > 0 else "missing_mapping"
        await db.execute(text("""
            UPDATE workflow_templates SET service_mappings_json = :m::jsonb,
            readiness_status = :readiness, updated_at = :now WHERE id = :id
        """), {"m": json.dumps(mappings), "readiness": readiness, "now": _now(), "id": wid})
        await db.commit()

    # ── Validate ───────────────────────────────────────────────────────────────
    async def validate_template(self, db: AsyncSession, wid: str, user_id: str | None = None) -> dict:
        import json
        tmpl = await self.get_template(db, wid)
        steps = list(tmpl.get("steps_json") or [])
        transitions = list(tmpl.get("transitions_json") or [])
        mappings = list(tmpl.get("service_mappings_json") or [])
        errors = []
        warnings = []

        step_keys = {s.get("step_key") for s in steps}

        if not steps:
            errors.append({"field": "steps", "message": "Workflow has no steps defined", "severity": "error"})

        # all_transitions_valid
        for t in transitions:
            if t.get("from_step_key") not in step_keys:
                errors.append({"field": "transitions", "message": f"Transition from_step_key '{t.get('from_step_key')}' not found in steps", "severity": "error"})
            if t.get("to_step_key") not in step_keys:
                errors.append({"field": "transitions", "message": f"Transition to_step_key '{t.get('to_step_key')}' not found in steps", "severity": "error"})

        # no_duplicate_step_keys
        seen_keys: set = set()
        for s in steps:
            k = s.get("step_key")
            if k in seen_keys:
                errors.append({"field": "steps", "message": f"Duplicate step_key: {k}", "severity": "error"})
            seen_keys.add(k)

        # has_end (a step not used as from_step_key)
        from_keys = {t.get("from_step_key") for t in transitions}
        leaf_steps = [s for s in steps if s.get("step_key") not in from_keys]
        if steps and not leaf_steps:
            warnings.append({"field": "transitions", "message": "No terminal step found (all steps have outgoing transitions)"})

        # mapping_exists
        if not mappings:
            warnings.append({"field": "service_mapping", "message": "No service mappings defined. Workflow will not be triggered automatically."})

        passed = len(errors) == 0
        readiness_status = "ready" if passed and mappings else ("missing_mapping" if passed and not mappings else "validation_failed")

        result = {
            "passed": passed,
            "errors": errors,
            "warnings": warnings,
            "readiness_status": readiness_status,
        }

        # persist
        await db.execute(text("""
            UPDATE workflow_templates SET validation_result_json = :v::jsonb,
            readiness_status = :rs, updated_at = :now WHERE id = :id
        """), {"v": json.dumps(result), "rs": readiness_status, "now": _now(), "id": wid})
        await self._write_audit(db, wid, "validated", user_id, None, result, None)
        await db.commit()
        return result

    # ── Simulate ───────────────────────────────────────────────────────────────
    async def simulate_template(self, db: AsyncSession, wid: str, scenario: str, role: str, start_step: str | None, user_id: str | None = None) -> dict:
        tmpl = await self.get_template(db, wid)
        steps = {s["step_key"]: s for s in (tmpl.get("steps_json") or [])}
        transitions = list(tmpl.get("transitions_json") or [])

        # build adjacency
        adj: dict[str, list[dict]] = {}
        for t in transitions:
            adj.setdefault(t["from_step_key"], []).append(t)

        # start from first step if not specified
        if not start_step:
            step_list = sorted((tmpl.get("steps_json") or []), key=lambda s: s.get("display_order", 99))
            start_step = step_list[0]["step_key"] if step_list else None

        if not start_step:
            return {"steps": [], "notifications": [], "sla_timers": [], "finance_triggers": [], "final_state": "empty"}

        walked: list[dict] = []
        current = start_step
        visited: set = set()
        while current and current not in visited:
            visited.add(current)
            step_def = steps.get(current, {})
            walked.append({
                "step_key": current,
                "step_name": step_def.get("step_name", current),
                "action": adj[current][0]["action_label"] if current in adj else "End",
                "role": step_def.get("owner_role", "system"),
                "duration_estimate": "15-30 min",
            })
            if current not in adj:
                break
            next_trans = adj[current][0]
            current = next_trans["to_step_key"]

        notifications = [s["step_key"] for s in walked if steps.get(s["step_key"], {}).get("customer_visible")]
        finance_triggers = [s["step_key"] for s in walked if steps.get(s["step_key"], {}).get("requires_payment_record")]

        return {
            "steps": walked,
            "notifications": notifications,
            "sla_timers": [s["step_key"] for s in walked if steps.get(s["step_key"], {}).get("sla_enabled")],
            "finance_triggers": finance_triggers,
            "final_state": walked[-1]["step_key"] if walked else "empty",
        }

    # ── Publish ────────────────────────────────────────────────────────────────
    async def publish_template(self, db: AsyncSession, wid: str, reason: str | None, user_id: str | None = None) -> dict:
        import json
        validation = await self.validate_template(db, wid, user_id)
        if not validation["passed"]:
            from fastapi import HTTPException
            raise HTTPException(400, f"Cannot publish workflow with validation errors: {[e['message'] for e in validation['errors']]}")

        tmpl = await self.get_template(db, wid)
        new_version = (tmpl.get("current_version") or 1) + 1
        now = _now()

        await db.execute(text("""
            UPDATE workflow_templates SET status = 'published', published_at = :now,
            current_version = :v, readiness_status = 'ready', updated_at = :now,
            updated_by_user_id = :uid WHERE id = :id
        """), {"now": now, "v": new_version, "uid": user_id, "id": wid})

        # insert version record
        await db.execute(text("""
            INSERT INTO workflow_template_versions
              (id, workflow_template_id, version_number, snapshot_json, change_summary,
               published_by_user_id, published_at, is_rollback, status, created_at)
            VALUES
              (:vid, :wid, :vn, :snap::jsonb, :summary, :uid, :now, false, 'published', :now)
        """), {
            "vid": _uid(),
            "wid": wid,
            "vn": new_version,
            "snap": json.dumps(tmpl),
            "summary": reason or f"Published v{new_version}",
            "uid": user_id,
            "now": now,
        })
        await self._write_audit(db, wid, "published", user_id, None, {"version": new_version}, reason)
        await db.commit()
        return await self.get_template(db, wid)

    # ── Rollback ───────────────────────────────────────────────────────────────
    async def rollback_template(self, db: AsyncSession, wid: str, version_number: int, reason: str | None, user_id: str | None = None) -> dict:
        import json
        r = await db.execute(text("""
            SELECT * FROM workflow_template_versions
            WHERE workflow_template_id = :wid AND version_number = :vn
            ORDER BY created_at DESC LIMIT 1
        """), {"wid": wid, "vn": version_number})
        ver = r.fetchone()
        if not ver:
            from fastapi import HTTPException
            raise HTTPException(404, f"Version {version_number} not found")

        ver_dict = _row_to_dict(ver)
        snapshot = ver_dict.get("snapshot_json") or {}
        now = _now()

        await db.execute(text("""
            UPDATE workflow_templates SET
              steps_json = :steps::jsonb,
              transitions_json = :trans::jsonb,
              status = 'draft', updated_at = :now, updated_by_user_id = :uid
            WHERE id = :id
        """), {
            "steps": json.dumps(snapshot.get("steps_json", [])),
            "trans": json.dumps(snapshot.get("transitions_json", [])),
            "now": now,
            "uid": user_id,
            "id": wid,
        })
        await self._write_audit(db, wid, "rollback", user_id, None, {"to_version": version_number}, reason)
        await db.commit()
        return await self.get_template(db, wid)

    # ── Versions ───────────────────────────────────────────────────────────────
    async def get_versions(self, db: AsyncSession, wid: str) -> list:
        r = await db.execute(text("""
            SELECT * FROM workflow_template_versions WHERE workflow_template_id = :wid ORDER BY version_number DESC
        """), {"wid": wid})
        return [_row_to_dict(row) for row in r.fetchall()]

    # ── Runtime Analytics ──────────────────────────────────────────────────────
    async def get_runtime_analytics(self, db: AsyncSession, wid: str) -> dict:
        r = await db.execute(text("""
            SELECT
                COUNT(*) AS jobs_processed,
                COUNT(*) FILTER (WHERE transition_status = 'success') AS successful_transitions,
                COUNT(*) FILTER (WHERE transition_status = 'failed') AS failed_transitions
            FROM workflow_runtime_events WHERE workflow_template_id = :wid
        """), {"wid": wid})
        row = r.fetchone()
        d = _row_to_dict(row)
        total = d.get("jobs_processed") or 0
        successful = d.get("successful_transitions") or 0
        failed = d.get("failed_transitions") or 0
        return {
            "jobs_processed": total,
            "completion_rate": round(successful / total * 100, 1) if total else 0,
            "avg_duration": "N/A",
            "sla_breach_rate": 0,
            "failed_transitions": failed,
        }

    async def get_runtime_jobs(self, db: AsyncSession, wid: str, page: int = 1, page_size: int = 20) -> dict:
        offset = (page - 1) * page_size
        r = await db.execute(text("""
            SELECT * FROM workflow_runtime_events WHERE workflow_template_id = :wid
            ORDER BY created_at DESC LIMIT :limit OFFSET :offset
        """), {"wid": wid, "limit": page_size, "offset": offset})
        return {"items": [_row_to_dict(row) for row in r.fetchall()]}

    # ── Audit ──────────────────────────────────────────────────────────────────
    async def get_audit_logs(self, db: AsyncSession, wid: str) -> list:
        r = await db.execute(text("""
            SELECT * FROM workflow_audit_logs WHERE workflow_template_id = :wid ORDER BY created_at DESC
        """), {"wid": wid})
        return [_row_to_dict(row) for row in r.fetchall()]

    async def _write_audit(self, db: AsyncSession, wid: str, action_type: str, actor_user_id: str | None,
                           old_val: Any, new_val: Any, reason: str | None) -> None:
        import json
        await db.execute(text("""
            INSERT INTO workflow_audit_logs (id, workflow_template_id, action_type, actor_user_id,
              old_value_json, new_value_json, reason, created_at)
            VALUES (:id, :wid, :action, :actor, :old::jsonb, :new::jsonb, :reason, :now)
        """), {
            "id": _uid(),
            "wid": wid,
            "action": action_type,
            "actor": actor_user_id,
            "old": json.dumps(old_val) if old_val is not None else "null",
            "new": json.dumps(new_val) if new_val is not None else "null",
            "reason": reason,
            "now": _now(),
        })

    # ── Seed Defaults ──────────────────────────────────────────────────────────
    async def seed_defaults_preview(self, db: AsyncSession) -> list:
        r = await db.execute(text("SELECT workflow_key FROM workflow_templates"))
        existing = {row[0] for row in r.fetchall()}
        preview = []
        for w in _SEED_WORKFLOWS:
            preview.append({
                "workflow_key": w["workflow_key"],
                "name": w["name"],
                "vertical_key": w["vertical_key"],
                "workflow_type": w["workflow_type"],
                "will_create": w["workflow_key"] not in existing,
                "steps_count": len(w.get("steps_json", [])),
            })
        return preview

    async def seed_defaults(self, db: AsyncSession, user_id: str | None = None) -> dict:
        r = await db.execute(text("SELECT workflow_key FROM workflow_templates"))
        existing = {row[0] for row in r.fetchall()}
        created = []
        skipped = []
        for w in _SEED_WORKFLOWS:
            if w["workflow_key"] in existing:
                skipped.append(w["workflow_key"])
                continue
            await self.create_template(db, w, user_id)
            created.append(w["workflow_key"])
        return {"created": len(created), "skipped": len(skipped), "created_keys": created}
