"""Document Engine — Models (3 tables). Frozen after signing. Full audit trail."""
import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import ServiceOSBase, utcnow


class DocumentTemplate(ServiceOSBase):
    """Per-tenant per-type templates. Variables listed — validated before generation."""
    __tablename__ = "document_templates"
    __table_args__ = (
        UniqueConstraint("tenant_id","doc_type", name="uq_dt_tenant_type"),
        Index("ix_dt_tenant", "tenant_id"),
    )
    tenant_id:    Mapped[uuid.UUID|None]=mapped_column(UUID(as_uuid=True), nullable=True)
    doc_type:     Mapped[str]           = mapped_column(String(50), nullable=False)
    name:         Mapped[str]           = mapped_column(String(200), nullable=False)
    template_html:Mapped[str]           = mapped_column(Text, nullable=False)
    required_vars:Mapped[list]          = mapped_column(JSONB, default=list, nullable=False)
    is_active:    Mapped[bool]          = mapped_column(Boolean, default=True, nullable=False)
    version:      Mapped[str]           = mapped_column(String(20), default="1.0", nullable=False)


class Document(ServiceOSBase):
    """Generated document. is_frozen=True after signing — no content changes allowed."""
    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint("document_number", name="uq_doc_number"),
        Index("ix_doc_tenant_type", "tenant_id", "doc_type"),
        Index("ix_doc_entity", "entity_type", "entity_id"),
    )
    tenant_id:       Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), nullable=False)
    doc_type:        Mapped[str]          = mapped_column(String(50), nullable=False)
    document_number: Mapped[str]          = mapped_column(String(50), nullable=False, unique=True)
    entity_type:     Mapped[str|None]     = mapped_column(String(50), nullable=True)
    entity_id:       Mapped[str|None]     = mapped_column(String(100), nullable=True)
    customer_id:     Mapped[uuid.UUID|None]=mapped_column(UUID(as_uuid=True), nullable=True)
    template_id:     Mapped[uuid.UUID|None]=mapped_column(UUID(as_uuid=True), nullable=True)
    status:          Mapped[str]          = mapped_column(String(20), default="draft", nullable=False)
    # PROVEN LEVEL 5: is_frozen checked at top of every write method
    is_frozen:       Mapped[bool]         = mapped_column(Boolean, default=False, nullable=False)
    content_html:    Mapped[str|None]     = mapped_column(Text, nullable=True)
    variables_used:  Mapped[dict]         = mapped_column(JSONB, default=dict, nullable=False)
    storage_key:     Mapped[str|None]     = mapped_column(String(500), nullable=True)
    media_file_id:   Mapped[uuid.UUID|None]=mapped_column(UUID(as_uuid=True), nullable=True)
    signing_token:   Mapped[str|None]     = mapped_column(String(128), nullable=True)
    signing_expires_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True), nullable=True)
    signed_at:       Mapped[datetime|None]=mapped_column(DateTime(timezone=True), nullable=True)
    signed_by:       Mapped[uuid.UUID|None]=mapped_column(UUID(as_uuid=True), nullable=True)
    signer_ip:       Mapped[str|None]     = mapped_column(String(50), nullable=True)
    signature_data:  Mapped[str|None]     = mapped_column(Text, nullable=True)
    voided_at:       Mapped[datetime|None]=mapped_column(DateTime(timezone=True), nullable=True)
    void_reason:     Mapped[str|None]     = mapped_column(String(500), nullable=True)


class DocumentEvent(ServiceOSBase):
    """APPEND-ONLY legal audit trail. Never deleted."""
    __tablename__ = "document_events"
    __table_args__ = (Index("ix_de_document", "document_id"),)

    document_id:  Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id:    Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), nullable=False)
    event_type:   Mapped[str]          = mapped_column(String(30), nullable=False)
    actor_id:     Mapped[uuid.UUID|None]=mapped_column(UUID(as_uuid=True), nullable=True)
    actor_role:   Mapped[str|None]     = mapped_column(String(30), nullable=True)
    actor_ip:     Mapped[str|None]     = mapped_column(String(50), nullable=True)
    meta:         Mapped[dict]         = mapped_column(JSONB, default=dict, nullable=False)
