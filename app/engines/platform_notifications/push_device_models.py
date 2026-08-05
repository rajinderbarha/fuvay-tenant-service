"""Phase U -- real Expo push-device registration (migration 217). Confirmed
genuinely absent by audit: PushNotificationProviderStub always returns
PROVIDER_NOT_CONFIGURED and no device-token table existed anywhere.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import ServiceOSBase


class StaffPushDevice(ServiceOSBase):
    __tablename__ = "staff_push_devices"
    __table_args__ = (
        UniqueConstraint("user_id", "device_id", name="uq_push_device_user_device"),
        Index("ix_push_device_user", "user_id"),
        Index("ix_push_device_token", "expo_push_token"),
    )

    user_id:         Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), nullable=False)
    device_id:       Mapped[str]             = mapped_column(String(200), nullable=False)
    expo_push_token: Mapped[str]             = mapped_column(String(300), nullable=False)
    platform:        Mapped[str | None]      = mapped_column(String(20), nullable=True)
    app_version:     Mapped[str | None]      = mapped_column(String(30), nullable=True)
    last_seen_at:    Mapped[datetime]        = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at:      Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
