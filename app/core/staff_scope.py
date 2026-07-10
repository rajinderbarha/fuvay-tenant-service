"""
StaffScopeService — enforces staff/technician data isolation.

Rules:
- staff_member_id is ALWAYS taken from JWT (actor.user_id).
- Staff may only access jobs assigned to them, not arbitrary jobs.
- tenant_owner may access all jobs within their tenant.
- Staff cannot access admin-only or cross-tenant resources.
"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import Select

from app.exceptions import ServiceOSException


class StaffScopeService:
    """Stateless helper — module-level singleton `staff_scope` provided below."""

    STAFF_ROLES = {"staff", "technician"}
    STAFF_OR_ABOVE = {"staff", "technician", "tenant_owner", "super_admin"}

    def get_staff_member_id_from_actor(self, actor) -> uuid.UUID:
        """Return staff member's user_id from JWT. Raises if not a staff role."""
        if actor.role not in self.STAFF_ROLES:
            raise ServiceOSException(
                error_code="PERMISSION_DENIED",
                detail=f"Staff/technician role required. Your role: '{actor.role}'.",
                blocking_rule="required_role: staff | technician",
            )
        return uuid.UUID(str(actor.user_id))

    def require_staff_actor(self, actor) -> uuid.UUID:
        """Actor must be staff, technician, tenant_owner, or super_admin."""
        if actor.role not in self.STAFF_OR_ABOVE:
            raise ServiceOSException(
                error_code="PERMISSION_DENIED",
                detail=f"Staff access required. Your role: '{actor.role}'.",
                blocking_rule="required_role: staff | technician | tenant_owner | super_admin",
            )
        return uuid.UUID(str(actor.user_id))

    def apply_assigned_job_scope(self, query: Select, actor, model_class) -> Select:
        """
        For staff/technician: filter to jobs assigned to them.
        For tenant_owner/super_admin: no filter (full tenant access handled by TenantScopeService).
        """
        if actor.role in self.STAFF_ROLES:
            staff_id = uuid.UUID(str(actor.user_id))
            return query.where(model_class.assigned_staff_id == staff_id)
        return query

    def assert_job_assigned_to_staff(self, job: Any, staff_id: uuid.UUID) -> None:
        """Raise PERMISSION_DENIED if job.assigned_staff_id != staff_id."""
        assigned = getattr(job, "assigned_staff_id", None)
        if assigned is None or str(assigned) != str(staff_id):
            raise ServiceOSException(
                error_code="PERMISSION_DENIED",
                detail="This job is not assigned to you.",
                resolution="You may only access jobs assigned to your staff account.",
            )

    def assert_chat_thread_allowed_for_staff(self, thread: Any, staff_id: uuid.UUID) -> None:
        """Raise PERMISSION_DENIED if staff is not a participant in the chat thread."""
        thread_staff_id = getattr(thread, "staff_id", None) or getattr(thread, "assigned_staff_id", None)
        if thread_staff_id is None or str(thread_staff_id) != str(staff_id):
            raise ServiceOSException(
                error_code="PERMISSION_DENIED",
                detail="You are not a participant in this chat thread.",
                resolution="Access only chat threads where you are the assigned staff member.",
            )


staff_scope = StaffScopeService()
