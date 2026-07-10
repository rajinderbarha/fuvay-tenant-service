"""
Cross-engine platform audit trail.

Every engine keeps its own domain-specific audit table (TenantAuditLog,
AuthAuditLog, SettingAuditLog, ...) for engine-scoped history. This module
additionally mirrors high-value write operations into PlatformAuditLog so
Super Admins can search ALL sensitive actions across ALL engines from one
place (Security → Audit Log), instead of having to check each engine.

Call this directly — it does NOT instantiate SecurityService, so engines
don't take on a dependency on the security engine's full surface area.
"""
from __future__ import annotations
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.security.constants import HIGH_RISK_OPERATIONS
from app.engines.security.models import PlatformAuditLog


async def record_platform_audit(
    db: AsyncSession,
    *,
    operation: str,
    engine_id: str,
    entity_id: str | None = None,
    tenant_id: uuid.UUID | None = None,
    entity_type: str | None = None,
    actor_id: uuid.UUID | None = None,
    actor_role: str | None = None,
    actor_ip: str | None = None,
    request_id: str | None = None,
    before: dict | None = None,
    after: dict | None = None,
) -> None:
    """Append-only insert into platform_audit_logs. Never UPDATE or DELETE."""
    db.add(PlatformAuditLog(
        tenant_id=tenant_id, actor_id=actor_id, actor_role=actor_role, actor_ip=actor_ip,
        operation=operation, engine_id=engine_id, entity_type=entity_type, entity_id=entity_id,
        before_state=before, after_state=after, request_id=request_id,
        is_high_risk=operation in HIGH_RISK_OPERATIONS,
    ))
