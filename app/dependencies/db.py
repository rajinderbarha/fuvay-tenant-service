"""Dependency: get_db — yields an async DB session per request."""
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency — yields a DB session, commits on success, rolls back on error.
    Usage: db: AsyncSession = Depends(get_db)
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
