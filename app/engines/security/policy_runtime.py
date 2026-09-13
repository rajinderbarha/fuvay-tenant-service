"""Small, dependency-safe accessors for runtime security policy values."""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def security_policy_value(db: AsyncSession, key: str, default: Any) -> Any:
    """Return a persisted policy value, falling back safely during upgrades."""
    try:
        from app.engines.security.models import SecurityPolicy

        result = await db.execute(
            select(SecurityPolicy.policy_value_json).where(SecurityPolicy.policy_key == key)
        )
        value = result.scalar_one_or_none()
        return default if value is None else value
    except Exception:
        # Authentication must remain available while the migration is rolling
        # through a deployment or when the policy table is temporarily offline.
        return default


async def password_policy(db: AsyncSession) -> tuple[int, int]:
    minimum = int(await security_policy_value(db, "password_min_length", 8))
    history = int(await security_policy_value(db, "password_history_count", 5))
    return max(8, min(minimum, 64)), max(1, min(history, 24))
