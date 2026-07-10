"""
CustomerScopeService — enforces customer data isolation.

Rules:
- customer_id is ALWAYS taken from the JWT sub (actor.user_id when role == customer).
- A customer can never see another customer's bookings, invoices, or conversations.
- The request body must never supply customer_id; the value is always JWT-sourced.
"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import Select

from app.exceptions import ServiceOSException


class CustomerScopeService:
    """Stateless helper — module-level singleton `customer_scope` provided below."""

    def get_customer_id_from_actor(self, actor) -> uuid.UUID:
        """Return customer_id from JWT. For customers this is actor.user_id."""
        if actor.role != "customer":
            raise ServiceOSException(
                error_code="PERMISSION_DENIED",
                detail="Customer role required.",
                blocking_rule="required_role: customer",
            )
        return uuid.UUID(str(actor.user_id))

    def require_customer(self, actor) -> uuid.UUID:
        """Actor must have role == 'customer'. Returns customer_id."""
        return self.get_customer_id_from_actor(actor)

    def apply_customer_scope(self, query: Select, actor, model_class) -> Select:
        """Append WHERE customer_id = <actor.user_id> for customer actors."""
        customer_id = self.get_customer_id_from_actor(actor)
        return query.where(model_class.customer_id == customer_id)

    def assert_record_belongs_to_customer(self, record: Any, customer_id: uuid.UUID) -> None:
        """Raise PERMISSION_DENIED if record.customer_id != customer_id."""
        record_cid = getattr(record, "customer_id", None)
        if record_cid is None or str(record_cid) != str(customer_id):
            raise ServiceOSException(
                error_code="PERMISSION_DENIED",
                detail="This record does not belong to you.",
                resolution="Access only your own records.",
            )

    def reject_customer_override(self, payload: dict | None, actor) -> None:
        """
        Raise if request body contains customer_id that differs from actor's user_id.
        Prevents customer injection attacks.
        """
        if not payload:
            return
        supplied = payload.get("customer_id")
        if supplied is None:
            return
        if str(supplied) != str(actor.user_id):
            raise ServiceOSException(
                error_code="CUSTOMER_OVERRIDE_REJECTED",
                detail="customer_id in request body must match your authenticated user.",
                resolution="Remove customer_id from the request body; it is set from your token.",
            )


customer_scope = CustomerScopeService()
