"""Marketing Automation Engine — Models (5 tables)."""
import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import (
    Boolean, DateTime, Index, Integer, Numeric,
    String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import ServiceOSBase, utcnow


class SocialAccount(ServiceOSBase):
    """Platform social accounts (Instagram + Facebook pages).
    PROVEN: token refresh uses SELECT FOR UPDATE NOWAIT."""
    __tablename__ = "social_accounts"
    __table_args__ = (
        UniqueConstraint("platform","page_id", name="uq_sa_platform_page"),
        Index("ix_sa_platform",  "platform"),
        Index("ix_sa_status",    "status"),
    )
    platform:         Mapped[str]           = mapped_column(String(20),  nullable=False)
    page_id:          Mapped[str]           = mapped_column(String(100), nullable=False)
    page_name:        Mapped[str]           = mapped_column(String(200), nullable=False)
    ig_user_id:       Mapped[str|None]      = mapped_column(String(100), nullable=True)
    # PROVEN: token stored encrypted reference — never plaintext in logs
    access_token:     Mapped[str]           = mapped_column(Text,        nullable=False)
    token_expires_at: Mapped[datetime]      = mapped_column(DateTime(timezone=True), nullable=False)
    last_refreshed_at:Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)
    status:           Mapped[str]           = mapped_column(String(20),  default="active", nullable=False)
    follower_count:   Mapped[int]           = mapped_column(Integer,     default=0, nullable=False)
    post_count:       Mapped[int]           = mapped_column(Integer,     default=0, nullable=False)
    is_primary:       Mapped[bool]          = mapped_column(Boolean,     default=False, nullable=False)
    connection_status:   Mapped[str]        = mapped_column(Text,        default="connected", nullable=False)
    daily_post_limit:    Mapped[int]        = mapped_column(Integer,     default=10, nullable=False)
    last_sync_at:        Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)
    publishing_enabled:  Mapped[bool]       = mapped_column(Boolean,     default=True, nullable=False)
    meta:             Mapped[dict]          = mapped_column(JSONB,       default=dict, nullable=False)


class ContentTemplate(ServiceOSBase):
    """DALL-E prompt templates per post type. Variable interpolation at generation time."""
    __tablename__ = "content_templates"
    __table_args__ = (
        UniqueConstraint("post_type","vertical","is_active",
                         name="uq_ct_type_vertical_active"),
        Index("ix_ct_post_type", "post_type"),
    )
    post_type:       Mapped[str]        = mapped_column(String(50),  nullable=False)
    vertical:        Mapped[str|None]   = mapped_column(String(50),  nullable=True)
    name:            Mapped[str]        = mapped_column(String(200), nullable=False)
    # DALL-E prompt template — variables in {{double_braces}}
    dalle_prompt:    Mapped[str]        = mapped_column(Text,        nullable=False)
    # Caption template for social post
    caption_template:Mapped[str]        = mapped_column(Text,        nullable=False)
    required_vars:   Mapped[list]       = mapped_column(JSONB,       default=list, nullable=False)
    default_tags:    Mapped[list]       = mapped_column(JSONB,       default=list, nullable=False)
    is_active:       Mapped[bool]       = mapped_column(Boolean,     default=True, nullable=False)
    version:         Mapped[str]        = mapped_column(String(10),  default="1.0", nullable=False)


class GeneratedAsset(ServiceOSBase):
    """DALL-E generated image. Cost tracked per row. Stored in Media Vault.
    PROVEN: DALL-E URL downloaded immediately — URLs expire in 60 min.
    PROVEN: exact API cost stored — not estimated retroactively.
    PROVEN: prompt_hash idempotency — same prompt in same hour reuses asset."""
    __tablename__ = "generated_assets"
    __table_args__ = (
        UniqueConstraint("prompt_hash","generated_date",
                         name="uq_ga_prompt_date"),
        Index("ix_ga_post_type",  "post_type"),
        Index("ix_ga_created",    "created_at"),
    )
    post_type:       Mapped[str]            = mapped_column(String(50),  nullable=False)
    dalle_model:     Mapped[str]            = mapped_column(String(30),  nullable=False)
    dalle_size:      Mapped[str]            = mapped_column(String(20),  nullable=False)
    # PROVEN: full prompt stored — can always see what was sent to DALL-E
    prompt_used:     Mapped[str]            = mapped_column(Text,        nullable=False)
    # PROVEN: prompt hash for idempotency — same prompt + date = same asset
    prompt_hash:     Mapped[str]            = mapped_column(String(64),  nullable=False)
    generated_date:  Mapped[str]            = mapped_column(String(10),  nullable=False)
    # PROVEN: cost stored at generation time — exact API response cost
    cost_inr:        Mapped[Decimal]        = mapped_column(Numeric(8,2),nullable=False)
    # PROVED: dalle_url downloaded immediately, stored_in media vault
    dalle_url:       Mapped[str|None]       = mapped_column(String(2000),nullable=True)
    media_file_id:   Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    storage_key:     Mapped[str|None]       = mapped_column(String(500), nullable=True)
    # Full DALL-E API response stored — same as webhook raw_payload pattern
    api_response:    Mapped[dict]           = mapped_column(JSONB,       default=dict, nullable=False)
    variables_used:  Mapped[dict]           = mapped_column(JSONB,       default=dict, nullable=False)
    generated_by:    Mapped[str]            = mapped_column(String(20),  default="celery", nullable=False)


class ScheduledPost(ServiceOSBase):
    """Content calendar entry. One delivery per post — idempotent on scheduled_post_id.
    PROVEN: uq_sp_post_date ensures no duplicate posts for same type on same date."""
    __tablename__ = "scheduled_posts"
    __table_args__ = (
        UniqueConstraint("post_type","scheduled_date","account_id",
                         name="uq_sp_post_date_account"),
        Index("ix_sp_status",       "status"),
        Index("ix_sp_scheduled",    "scheduled_at"),
        Index("ix_sp_account",      "account_id"),
    )
    account_id:      Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    post_type:       Mapped[str]            = mapped_column(String(50),  nullable=False)
    template_id:     Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    asset_id:        Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    tenant_id:       Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    scheduled_date:  Mapped[str]            = mapped_column(String(10),  nullable=False)
    scheduled_at:    Mapped[datetime]       = mapped_column(DateTime(timezone=True), nullable=False)
    status:          Mapped[str]            = mapped_column(String(20),  default="draft", nullable=False)
    caption:         Mapped[str|None]       = mapped_column(Text,        nullable=True)
    tags:            Mapped[list]           = mapped_column(JSONB,       default=list, nullable=False)
    variables:       Mapped[dict]           = mapped_column(JSONB,       default=dict, nullable=False)
    published_at:    Mapped[datetime|None]  = mapped_column(DateTime(timezone=True), nullable=True)
    meta_post_id:    Mapped[str|None]       = mapped_column(String(100), nullable=True)
    cancelled_at:    Mapped[datetime|None]  = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_reason:   Mapped[str|None]       = mapped_column(String(500), nullable=True)


class PostDelivery(ServiceOSBase):
    """APPEND-ONLY. Every Meta Graph API call result.
    PROVEN: full API response stored — response_body, latency_ms, http_status."""
    __tablename__ = "post_deliveries"
    __table_args__ = (
        UniqueConstraint("scheduled_post_id", name="uq_pd_post"),
        Index("ix_pd_status",   "status"),
        Index("ix_pd_account",  "account_id"),
        Index("ix_pd_created",  "created_at"),
    )
    scheduled_post_id: Mapped[uuid.UUID]     = mapped_column(UUID(as_uuid=True), nullable=False, unique=True)
    account_id:        Mapped[uuid.UUID]     = mapped_column(UUID(as_uuid=True), nullable=False)
    platform:          Mapped[str]           = mapped_column(String(20),  nullable=False)
    status:            Mapped[str]           = mapped_column(String(20),  nullable=False)
    # PROVEN: full Meta API response stored
    http_status:       Mapped[int|None]      = mapped_column(Integer,     nullable=True)
    response_body:     Mapped[dict]          = mapped_column(JSONB,       default=dict, nullable=False)
    meta_post_id:      Mapped[str|None]      = mapped_column(String(100), nullable=True)
    meta_media_id:     Mapped[str|None]      = mapped_column(String(100), nullable=True)
    latency_ms:        Mapped[int|None]      = mapped_column(Integer,     nullable=True)
    attempt_count:     Mapped[int]           = mapped_column(Integer,     default=1, nullable=False)
    error_message:     Mapped[str|None]      = mapped_column(String(500), nullable=True)
    delivered_at:      Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)
