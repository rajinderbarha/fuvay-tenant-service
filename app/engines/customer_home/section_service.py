"""Read/write for Home section layout."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.customer_home.constants import ERR_UNKNOWN_SECTION, HOME_SECTION_KEYS
from app.engines.customer_home.section_models import HomeSectionSetting
from app.exceptions import ServiceOSException


class HomeSectionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _all(self) -> list[HomeSectionSetting]:
        return list((await self.db.execute(
            select(HomeSectionSetting).order_by(HomeSectionSetting.display_order)
        )).scalars().all())

    async def list_admin(self) -> list[dict]:
        """Every known section, including disabled ones -- admin has to see what
        it has turned OFF, or a hidden section looks like a missing feature."""
        rows = await self._all()
        seen = {r.section_key for r in rows}
        # A key the seed has not written yet (a section added by a later release
        # against an older database) is reported at its default rather than
        # silently missing from the admin list.
        missing = [
            {"section_key": key, "is_enabled": True, "display_order": 1000,
             "title_override": None, "updated_at": None}
            for key in HOME_SECTION_KEYS if key not in seen
        ]
        return [r.to_dict() for r in rows] + missing

    async def customer_sections(self) -> list[dict]:
        """The enabled sections, in order, for the app to lay out.

        Rows whose key this build does not recognise are dropped: the app would
        not know what to draw for them, and reporting them would make the
        layout depend on rows the client cannot honour.
        """
        return [
            r.to_customer_dict() for r in await self._all()
            if r.is_enabled and r.section_key in HOME_SECTION_KEYS
        ]

    async def update(
        self, section_key: str, data: dict, actor_id: uuid.UUID | None = None,
    ) -> dict:
        if section_key not in HOME_SECTION_KEYS:
            raise ServiceOSException(
                ERR_UNKNOWN_SECTION,
                f"Unknown Home section '{section_key}'. Known sections: "
                f"{', '.join(HOME_SECTION_KEYS)}",
                status_code=422,
            )
        row = (await self.db.execute(
            select(HomeSectionSetting).where(HomeSectionSetting.section_key == section_key)
        )).scalars().first()
        if row is None:
            # Upsert rather than 404: the key is valid (checked above), it simply
            # has no row yet on a database seeded before this section existed.
            row = HomeSectionSetting(section_key=section_key, is_enabled=True, display_order=1000)
            self.db.add(row)
        for field in ("is_enabled", "display_order", "title_override"):
            if field in data:
                setattr(row, field, data[field])
        row.updated_by = actor_id
        await self.db.flush()
        result = row.to_dict()
        await self.db.commit()
        return result

    async def reorder(self, ordered_keys: list[str], actor_id: uuid.UUID | None = None) -> list[dict]:
        """Assigns order from a full list, so admin can drag-sort in one call.

        Every key is validated BEFORE anything is written -- a typo halfway
        through a list must not leave the layout half-reordered.
        """
        unknown = [k for k in ordered_keys if k not in HOME_SECTION_KEYS]
        if unknown:
            raise ServiceOSException(
                ERR_UNKNOWN_SECTION,
                f"Unknown Home section(s): {', '.join(unknown)}",
                status_code=422,
            )
        rows = {r.section_key: r for r in await self._all()}
        for index, key in enumerate(ordered_keys):
            row = rows.get(key)
            if row is None:
                row = HomeSectionSetting(section_key=key, is_enabled=True, display_order=0)
                self.db.add(row)
                rows[key] = row
            row.display_order = (index + 1) * 10
            row.updated_by = actor_id
        await self.db.flush()
        result = [rows[k].to_dict() for k in ordered_keys]
        await self.db.commit()
        return result
