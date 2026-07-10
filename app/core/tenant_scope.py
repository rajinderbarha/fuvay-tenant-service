"""
TenantScopeService — enforces tenant isolation at the service layer.

Rules:
- tenant_id is ALWAYS taken from the JWT (actor.tenant_id), never from request body/query.
- Records belonging to a different tenant raise PERMISSION_DENIED immediately.
- Super admins may operate across tenants; all other roles are strictly scoped.
"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import Select

from app.exceptions import ServiceOSException


class TenantScopeService:
    """Stateless helper — instantiate per-call or share as a module-level singleton."""

    TENANT_ROLES = {"tenant_owner", "staff", "technician"}

    def get_tenant_id_from_actor(self, actor) -> uuid.UUID:
        """Extract tenant_id from JWT actor; raises if missing."""
        tid = actor.tenant_id
        if not tid:
            raise ServiceOSException(
                error_code="TENANT_CONTEXT_MISSING",
                detail="No tenant context found in token.",
                resolution="Authenticate with a tenant-scoped account.",
            )
        return uuid.UUID(str(tid))

    def require_tenant_user(self, actor) -> None:
        """Actor must be a tenant-scoped role (not super_admin or customer)."""
        if actor.role not in self.TENANT_ROLES and actor.role != "tenant_owner":
            raise ServiceOSException(
                error_code="PERMISSION_DENIED",
                detail=f"Tenant-user access required. Your role: '{actor.role}'.",
                blocking_rule="required_role: tenant_owner | staff | technician",
            )

    def require_active_tenant(self, actor) -> uuid.UUID:
        """Actor must have a tenant_id (ensures tenant context is active)."""
        return self.get_tenant_id_from_actor(actor)

    def apply_tenant_scope(self, query: Select, actor, model_class) -> Select:
        """
        Append a WHERE tenant_id = <actor.tenant_id> filter.
        Super admins are NOT scoped — they may query across tenants.
        """
        if actor.role == "super_admin":
            return query
        tenant_id = self.get_tenant_id_from_actor(actor)
        return query.where(model_class.tenant_id == tenant_id)

    def assert_record_belongs_to_tenant(self, record: Any, tenant_id: uuid.UUID) -> None:
        """Raise PERMISSION_DENIED if record.tenant_id != tenant_id."""
        record_tid = getattr(record, "tenant_id", None)
        if record_tid is None or str(record_tid) != str(tenant_id):
            raise ServiceOSException(
                error_code="PERMISSION_DENIED",
                detail="This record does not belong to your tenant.",
                resolution="Access only resources assigned to your tenant.",
            )

    def reject_tenant_override(self, payload: dict | None, actor) -> None:
        """
        Raise if the request body/query contains a tenant_id that differs
        from the actor's JWT tenant_id. Prevents tenant injection attacks.
        """
        if not payload:
            return
        supplied = payload.get("tenant_id")
        if supplied is None:
            return
        actor_tid = actor.tenant_id
        if actor_tid is None:
            return
        if str(supplied) != str(actor_tid):
            raise ServiceOSException(
                error_code="TENANT_OVERRIDE_REJECTED",
                detail="tenant_id in request body must match your authenticated tenant.",
                resolution="Remove tenant_id from the request body; it is set from your token.",
            )


tenant_scope = TenantScopeService()
