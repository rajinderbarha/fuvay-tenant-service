"""
ServiceOS — Base SQLAlchemy Models
All models inherit from ServiceOSBase which provides:
  - UUID primary key
  - created_at / updated_at timestamps (auto-managed)
  - tenant_id (on tenant-scoped models)
  - soft delete via deleted_at
  - helper methods: to_dict(), update()
"""
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, MappedColumn, mapped_column


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """SQLAlchemy declarative base — shared across all engines."""
    pass


class TimestampMixin:
    """Adds created_at / updated_at to any model."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        server_default=func.now(),
        onupdate=utcnow,
        nullable=False,
    )


class SoftDeleteMixin:
    """Adds soft-delete support. Filter on deleted_at IS NULL in queries."""
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def soft_delete(self) -> None:
        self.deleted_at = utcnow()


class ServiceOSBase(Base, TimestampMixin):
    """
    Base for ALL ServiceOS models.
    - UUID PK (gen_random_uuid() in Postgres, uuid4() in Python)
    - Auto timestamps
    """
    __abstract__ = True

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )

    def to_dict(self, exclude: set[str] | None = None) -> dict[str, Any]:
        exclude = exclude or set()
        result = {}
        for col in self.__table__.columns:
            if col.name not in exclude:
                val = getattr(self, col.name)
                if isinstance(val, uuid.UUID):
                    val = str(val)
                elif isinstance(val, datetime):
                    val = val.isoformat()
                result[col.name] = val
        return result

    def update(self, **kwargs: Any) -> None:
        """Patch model fields from a dict."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)


class TenantScopedBase(ServiceOSBase):
    """
    Base for all tenant-scoped models.
    Adds tenant_id — always filter on this in every query.
    Row-level security is enforced both at app level AND via Postgres RLS policies.
    """
    __abstract__ = True

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="Foreign key to tenants.id — all queries MUST filter on this",
    )
