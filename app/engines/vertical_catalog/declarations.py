"""Review & Submit declarations -- the 3 mandatory consents a tenant owner
must accept before a vertical enrollment can be submitted for admin review.

Versions are bumped here (not left implicit) whenever the referenced Terms
of Service / Privacy Notice changes materially -- bumping a version means
every tenant must re-accept, even if they accepted a prior version already.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.vertical_catalog.models import TenantOnboardingDeclaration

TERMS_OF_SERVICE_VERSION = "2026-01-01"
PRIVACY_NOTICE_VERSION = "2026-01-01"

# key -> the document_version it must currently be accepted against.
REQUIRED_DECLARATIONS: dict[str, str] = {
    "information_accurate": "1",
    "authorized_submitter": "1",
    "terms_and_privacy": f"tos:{TERMS_OF_SERVICE_VERSION}|privacy:{PRIVACY_NOTICE_VERSION}",
}


async def get_declaration_status(db: AsyncSession, tenant_id: uuid.UUID, vertical_id: uuid.UUID) -> dict:
    rows = (await db.execute(
        select(TenantOnboardingDeclaration).where(
            TenantOnboardingDeclaration.tenant_id == tenant_id,
            TenantOnboardingDeclaration.vertical_id == vertical_id,
        )
    )).scalars().all()
    accepted_current = {r.declaration_key: r for r in rows if r.document_version == REQUIRED_DECLARATIONS.get(r.declaration_key)}
    items = []
    for key, version in REQUIRED_DECLARATIONS.items():
        row = accepted_current.get(key)
        items.append({
            "key": key,
            "document_version": version,
            "accepted": row is not None,
            "accepted_at": row.accepted_at.isoformat() if row else None,
        })
    return {
        "items": items,
        "all_accepted": all(i["accepted"] for i in items),
        "terms_of_service_version": TERMS_OF_SERVICE_VERSION,
        "privacy_notice_version": PRIVACY_NOTICE_VERSION,
    }


async def accept_declarations(
    db: AsyncSession, tenant_id: uuid.UUID, vertical_id: uuid.UUID, keys: list[str],
    *, actor_id: uuid.UUID | None, ip_address: str | None = None, user_agent: str | None = None,
) -> dict:
    unknown = [k for k in keys if k not in REQUIRED_DECLARATIONS]
    if unknown:
        raise ValueError(f"Unknown declaration key(s): {unknown}")

    existing = (await db.execute(
        select(TenantOnboardingDeclaration).where(
            TenantOnboardingDeclaration.tenant_id == tenant_id,
            TenantOnboardingDeclaration.vertical_id == vertical_id,
            TenantOnboardingDeclaration.declaration_key.in_(keys),
        )
    )).scalars().all()
    already = {(r.declaration_key, r.document_version) for r in existing}

    now = datetime.now(timezone.utc)
    for key in keys:
        version = REQUIRED_DECLARATIONS[key]
        if (key, version) in already:
            continue  # idempotent -- don't duplicate an existing acceptance of the current version
        db.add(TenantOnboardingDeclaration(
            tenant_id=tenant_id, vertical_id=vertical_id, declaration_key=key,
            document_version=version, accepted_at=now, actor_id=actor_id,
            ip_address=ip_address, user_agent=user_agent,
        ))
    await db.commit()
    return await get_declaration_status(db, tenant_id, vertical_id)
