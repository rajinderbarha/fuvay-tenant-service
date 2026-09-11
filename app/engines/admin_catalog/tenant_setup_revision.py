"""Version and invalidate tenant setup contracts after Admin rule changes."""
from __future__ import annotations

import uuid

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.admin_catalog.models import MasterServiceJobType, TenantService


async def bump_tenant_setup_revision(
    db: AsyncSession, master_service_id: uuid.UUID,
    job_type_id: uuid.UUID | None = None,
    *, affected_tenant_service_ids: set[uuid.UUID] | None = None,
) -> tuple[int, int]:
    """Atomically bump the rule revision and require affected tenants to review.

    A stricter Admin rule must never be displayed as active while customer
    booking continues against an older tenant configuration. Published tenant
    offerings therefore return to draft in the same transaction. The tenant's
    prior selections/prices are retained; republishing only asks them to fill
    newly-required data and acknowledge the new revision.

    ``affected_tenant_service_ids`` narrows that invalidation when the caller
    knows exactly which provider configurations used the changed catalog row.
    This matters for retiring a duplicate Type: the master-service revision is
    global, but providers that never selected that Type remain valid and must
    not disappear from customer/Instagram serviceability.
    """
    link_scope = [MasterServiceJobType.master_service_id == master_service_id]
    tenant_scope = [TenantService.master_service_id == master_service_id]
    if job_type_id is not None:
        link_scope.append(MasterServiceJobType.job_type_id == job_type_id)
        tenant_scope.append(TenantService.job_type_id == job_type_id)
    revisions = (await db.execute(
        update(MasterServiceJobType)
        .where(*link_scope)
        .values(setup_rules_revision=MasterServiceJobType.setup_rules_revision + 1)
        .returning(MasterServiceJobType.setup_rules_revision)
    )).scalars().all()
    if not revisions:
        return 0, 0
    if affected_tenant_service_ids is not None:
        if not affected_tenant_service_ids:
            return int(max(revisions)), 0
        tenant_scope.append(TenantService.id.in_(affected_tenant_service_ids))
    affected = (await db.execute(
        update(TenantService)
        .where(
            *tenant_scope,
            TenantService.deleted_at.is_(None),
            TenantService.is_enabled.is_(True),
            TenantService.setup_status == "published",
        )
        .values(setup_status="draft", last_active_step="services-pricing")
    )).rowcount or 0
    return int(max(revisions)), int(affected)
