"""Audit logging for sensitive customer-contact/address access (spec section
5/12: "record who viewed it and when", "audit on sensitive-data access").

Reuses the existing append-only ComplianceAuditLog table
(app.engines.compliance.models.ComplianceAuditLog) rather than inventing a
parallel audit table — same pattern already used for legal/DPDP data-access
logging elsewhere in this codebase.
"""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.compliance.models import ComplianceAuditLog

ACTION_ADDRESS_ACCESS = "customer_exact_address_access"


async def record_address_access(
    db: AsyncSession, *, tenant_id: uuid.UUID, staff_id: uuid.UUID | None,
    job_id: uuid.UUID, customer_id: uuid.UUID | None, granted: bool, reason_code: str,
) -> None:
    row = ComplianceAuditLog(
        user_id=customer_id,
        tenant_id=tenant_id,
        action=ACTION_ADDRESS_ACCESS,
        table_accessed="service_bookings.address_snapshot",
        purpose="job_operational_access",
        legal_basis="customer_operational_access_policy",
        actor_id=staff_id,
        actor_role=None,
        reference_id=str(job_id),
        meta={"granted": granted, "reason_code": reason_code, "customer_id": str(customer_id) if customer_id else None},
    )
    db.add(row)
