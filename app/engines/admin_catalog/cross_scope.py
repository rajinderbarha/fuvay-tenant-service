"""Shared helper for the Type/Brand library pickers.

Types and Brands are global libraries, but a value only makes sense as a
choice for services it's actually used on. Every legacy-dimension picker in
the catalog workspace (and the plain /v1/admin/service-types and
/v1/admin/brands listings it calls) previously showed the ENTIRE global
library with no scoping at all -- so configuring a Microwave Oven offered
"Split AC" / "Window AC" as Type choices just because some other service
(Air Conditioner) happened to use them.

Rule: exclude a value from master_service_id's picker only if it is already
actively attached to a DIFFERENT master service and NOT attached to this
one. A value nobody has used yet stays visible everywhere (nothing to
exclude it on); a value already attached to two services correctly stays
visible for both.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def cross_scoped_ids(db: AsyncSession, mapping_model, mapping_id_col,
                            master_service_id: uuid.UUID | None) -> set[uuid.UUID]:
    if master_service_id is None:
        return set()
    other_ids = set((await db.execute(
        select(mapping_id_col).where(
            mapping_model.master_service_id != master_service_id,
            mapping_model.is_active.is_(True),
        ))).scalars().all())
    if not other_ids:
        return set()
    own_ids = set((await db.execute(
        select(mapping_id_col).where(
            mapping_model.master_service_id == master_service_id,
            mapping_model.is_active.is_(True),
        ))).scalars().all())
    return other_ids - own_ids
