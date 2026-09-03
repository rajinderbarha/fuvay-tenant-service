"""
Fuvay — Async Database Setup
SQLAlchemy 2.0 async engine + session factory.
Per-tenant schema isolation: each tenant gets schema = tenant_{tenant_id}.
The public schema holds platform-level tables (tenants, tenant_engines, users).
"""
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.config import get_settings

# ── Engine & Session Factory ───────────────────────────────────────────────────
_engine: AsyncEngine | None = None
_async_session_factory: async_sessionmaker[AsyncSession] | None = None


def create_engine() -> AsyncEngine:
    settings = get_settings()
    return create_async_engine(
        settings.DATABASE_URL,
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
        pool_timeout=settings.DATABASE_POOL_TIMEOUT,
        pool_pre_ping=True,
        echo=settings.DEBUG,
        future=True,
        connect_args={
            "ssl": False,  # local PostgreSQL has no SSL
            # A cancelled client or worker must never retain an open
            # transaction indefinitely. PostgreSQL enforces this per
            # connection even if application cleanup itself is interrupted.
            "server_settings": {
                "idle_in_transaction_session_timeout": str(
                    settings.DATABASE_IDLE_IN_TRANSACTION_TIMEOUT_SECONDS * 1000
                ),
            },
        },
    )


def create_test_engine() -> AsyncEngine:
    """Isolated engine for tests — NullPool prevents connection reuse."""
    settings = get_settings()
    return create_async_engine(settings.DATABASE_URL, poolclass=NullPool, echo=False)


async def init_db() -> None:
    """Called during app startup lifespan."""
    global _engine, _async_session_factory
    _engine = create_engine()
    _async_session_factory = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False,       # Keep attributes accessible after commit
        autocommit=False,
        autoflush=False,
    )
    import structlog
    structlog.get_logger("database").info("database.connected", url=get_settings().DATABASE_URL.split("@")[-1])


async def close_db() -> None:
    """Called during app shutdown lifespan."""
    global _engine
    if _engine:
        await _engine.dispose()
        import structlog
        structlog.get_logger("database").info("database.disconnected")


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    if _async_session_factory is None:
        raise RuntimeError("Database not initialized. Check app lifespan.")
    return _async_session_factory


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Context manager — use in background tasks and scripts."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ── Tenant Schema Helpers ─────────────────────────────────────────────────────
def tenant_schema_name(tenant_id: str) -> str:
    """Returns the Postgres schema name for a given tenant."""
    # Sanitize — remove dashes for Postgres identifier compatibility
    safe_id = tenant_id.replace("-", "_")
    return f"tenant_{safe_id}"


async def set_tenant_schema(session: AsyncSession, tenant_id: str) -> None:
    """
    Sets search_path to the tenant's schema for row-level isolation.
    Call this at the start of any tenant-scoped DB operation.
    """
    from sqlalchemy import text
    schema = tenant_schema_name(tenant_id)
    await session.execute(text(f"SET search_path TO {schema}, public"))


async def create_tenant_schema(session: AsyncSession, tenant_id: str) -> None:
    """
    Creates the tenant's Postgres schema.
    Called during tenant provisioning (Phase 2).
    """
    from sqlalchemy import text
    schema = tenant_schema_name(tenant_id)
    await session.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
    import structlog
    structlog.get_logger("database").info("tenant_schema.created", schema=schema, tenant_id=tenant_id)
