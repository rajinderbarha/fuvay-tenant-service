"""TENANT-SUPPORT ORM models (migration 207).

Deliberately separate tables from customer_complaints — see
constants.py for the boundary rationale.
"""
from __future__ import annotations

import random
import string
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, Column, DateTime, Index, Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.models.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _ticket_number() -> str:
    return "SUP-" + "".join(random.choices(string.digits, k=8))


class SupportTicket(Base):
    """A tenant business asking ServiceOS for help. NOT a customer complaint."""
    __tablename__ = "support_tickets"
    __table_args__ = (
        UniqueConstraint("ticket_number", name="uq_support_ticket_number"),
        Index("ix_support_tickets_tenant", "tenant_id"),
        Index("ix_support_tickets_status", "status"),
        Index("ix_support_tickets_tenant_status", "tenant_id", "status"),
        Index("ix_support_tickets_created", "created_at"),
    )

    id                 = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_number      = Column(String(40), nullable=False, default=_ticket_number)
    tenant_id          = Column(UUID(as_uuid=True), nullable=False)
    vertical_id        = Column(UUID(as_uuid=True), nullable=True)
    vertical_key       = Column(String(60), nullable=True)

    reporter_user_id   = Column(UUID(as_uuid=True), nullable=False)
    reporter_name      = Column(String(200), nullable=True)
    reporter_role      = Column(String(60), nullable=True)

    category           = Column(String(60), nullable=False)
    subcategory        = Column(String(120), nullable=True)
    product_area       = Column(String(60), nullable=True)
    affected_feature   = Column(String(200), nullable=True)

    subject            = Column(String(300), nullable=False)
    description        = Column(Text, nullable=False)
    started_at         = Column(DateTime(timezone=True), nullable=True)

    # Tenant chooses impact; backend derives priority. Never accept priority.
    impact             = Column(String(40), nullable=False)
    priority           = Column(String(20), nullable=False, default="normal")
    priority_reasons   = Column(JSONB, nullable=True)
    is_critical_incident = Column(Boolean, nullable=False, default=False)
    critical_impact_key  = Column(String(40), nullable=True)

    status             = Column(String(40), nullable=False, default="submitted")

    # Scoped references only — never raw customer data (section 20).
    related_entities   = Column(JSONB, nullable=True)

    assigned_team      = Column(String(80), nullable=True)
    assigned_admin_user_id = Column(UUID(as_uuid=True), nullable=True)
    assigned_admin_name    = Column(String(200), nullable=True)

    # SLA (all canonical UTC)
    sla_policy             = Column(String(80), nullable=True)
    first_response_due_at  = Column(DateTime(timezone=True), nullable=True)
    first_response_met_at  = Column(DateTime(timezone=True), nullable=True)
    next_update_due_at     = Column(DateTime(timezone=True), nullable=True)
    resolution_target_at   = Column(DateTime(timezone=True), nullable=True)
    sla_paused_at          = Column(DateTime(timezone=True), nullable=True)
    sla_paused_seconds     = Column(Integer, nullable=False, default=0)
    sla_breached_at        = Column(DateTime(timezone=True), nullable=True)
    escalated_at           = Column(DateTime(timezone=True), nullable=True)

    resolution_summary  = Column(Text, nullable=True)
    resolved_at         = Column(DateTime(timezone=True), nullable=True)
    closed_at           = Column(DateTime(timezone=True), nullable=True)
    reopen_deadline_at  = Column(DateTime(timezone=True), nullable=True)
    reopen_count        = Column(Integer, nullable=False, default=0)

    incident_id         = Column(UUID(as_uuid=True), nullable=True)
    merged_into_id      = Column(UUID(as_uuid=True), nullable=True)

    tenant_unread_count = Column(Integer, nullable=False, default=0)
    last_tenant_reply_at   = Column(DateTime(timezone=True), nullable=True)
    last_support_reply_at  = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)


class SupportTicketMessage(Base):
    """Threaded conversation entry. internal_note kind is NEVER exposed to tenants."""
    __tablename__ = "support_ticket_messages"
    __table_args__ = (
        Index("ix_support_msgs_ticket", "ticket_id"),
        Index("ix_support_msgs_ticket_created", "ticket_id", "created_at"),
    )

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id    = Column(UUID(as_uuid=True), nullable=False)
    kind         = Column(String(40), nullable=False)
    author_user_id = Column(UUID(as_uuid=True), nullable=True)
    author_name  = Column(String(200), nullable=True)
    author_type  = Column(String(40), nullable=False)   # tenant | serviceos | system
    author_role  = Column(String(60), nullable=True)
    body         = Column(Text, nullable=False)
    visibility   = Column(String(20), nullable=False, default="tenant_visible")  # tenant_visible | internal
    attachments  = Column(JSONB, nullable=True)
    created_at   = Column(DateTime(timezone=True), nullable=False, default=_now)


class SupportTicketEvent(Base):
    """Append-only audit trail of status/assignment/priority/SLA changes."""
    __tablename__ = "support_ticket_events"
    __table_args__ = (
        Index("ix_support_events_ticket", "ticket_id"),
        Index("ix_support_events_ticket_created", "ticket_id", "created_at"),
    )

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id   = Column(UUID(as_uuid=True), nullable=False)
    event_type  = Column(String(60), nullable=False)
    from_value  = Column(String(80), nullable=True)
    to_value    = Column(String(80), nullable=True)
    reason      = Column(Text, nullable=True)
    actor_user_id = Column(UUID(as_uuid=True), nullable=True)
    actor_type  = Column(String(40), nullable=False, default="system")
    actor_name  = Column(String(200), nullable=True)
    visibility  = Column(String(20), nullable=False, default="tenant_visible")
    meta        = Column(JSONB, nullable=True)
    created_at  = Column(DateTime(timezone=True), nullable=False, default=_now)


class SupportTicketAttachment(Base):
    """Ticket-scoped attachment pointer into the canonical media engine."""
    __tablename__ = "support_ticket_attachments"
    __table_args__ = (
        Index("ix_support_attach_ticket", "ticket_id"),
    )

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id       = Column(UUID(as_uuid=True), nullable=False)
    message_id      = Column(UUID(as_uuid=True), nullable=True)
    media_asset_id  = Column(UUID(as_uuid=True), nullable=False)
    file_name       = Column(String(300), nullable=True)
    mime_type       = Column(String(120), nullable=True)
    size_bytes      = Column(Integer, nullable=True)
    uploaded_by     = Column(UUID(as_uuid=True), nullable=True)
    uploaded_by_type = Column(String(40), nullable=False, default="tenant")
    visibility      = Column(String(20), nullable=False, default="tenant_visible")
    legal_hold      = Column(Boolean, nullable=False, default=False)
    created_at      = Column(DateTime(timezone=True), nullable=False, default=_now)


class SupportKnowledgeArticle(Base):
    """Admin-managed knowledge base article — the real production source.
    The frontend never hardcodes articles."""
    __tablename__ = "support_knowledge_articles"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_support_kb_slug"),
        Index("ix_support_kb_area", "product_area"),
        Index("ix_support_kb_published", "is_published"),
    )

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug           = Column(String(200), nullable=False)
    title          = Column(String(300), nullable=False)
    summary        = Column(Text, nullable=True)
    body           = Column(Text, nullable=True)
    product_area   = Column(String(60), nullable=False)
    keywords       = Column(JSONB, nullable=True)
    vertical_keys  = Column(JSONB, nullable=True)   # null/[] = all verticals
    role_keys      = Column(JSONB, nullable=True)   # null/[] = all roles
    is_featured    = Column(Boolean, nullable=False, default=False)
    is_published   = Column(Boolean, nullable=False, default=False)
    policy_version = Column(String(40), nullable=True)
    helpful_count      = Column(Integer, nullable=False, default=0)
    not_helpful_count  = Column(Integer, nullable=False, default=0)
    view_count         = Column(Integer, nullable=False, default=0)
    created_at     = Column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at     = Column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)


class SupportArticleFeedback(Base):
    __tablename__ = "support_article_feedback"
    __table_args__ = (Index("ix_support_kb_fb_article", "article_id"),)

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    article_id = Column(UUID(as_uuid=True), nullable=False)
    tenant_id  = Column(UUID(as_uuid=True), nullable=True)
    user_id    = Column(UUID(as_uuid=True), nullable=True)
    is_helpful = Column(Boolean, nullable=False)
    comment    = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now)


class SupportAnnouncement(Base):
    """Real platform announcement, scoped by vertical/role/region/date."""
    __tablename__ = "support_announcements"
    __table_args__ = (
        Index("ix_support_ann_effective", "effective_from"),
        Index("ix_support_ann_published", "is_published"),
    )

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    announcement_type = Column(String(40), nullable=False)
    title           = Column(String(300), nullable=False)
    body            = Column(Text, nullable=True)
    vertical_keys   = Column(JSONB, nullable=True)
    role_keys       = Column(JSONB, nullable=True)
    region_keys     = Column(JSONB, nullable=True)
    tenant_ids      = Column(JSONB, nullable=True)   # null = all tenants
    requires_acknowledgement = Column(Boolean, nullable=False, default=False)
    is_published    = Column(Boolean, nullable=False, default=False)
    effective_from  = Column(DateTime(timezone=True), nullable=True)
    expires_at      = Column(DateTime(timezone=True), nullable=True)
    incident_id     = Column(UUID(as_uuid=True), nullable=True)
    created_at      = Column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at      = Column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)


class SupportAnnouncementAck(Base):
    __tablename__ = "support_announcement_acks"
    __table_args__ = (
        UniqueConstraint("announcement_id", "user_id", name="uq_support_ann_ack"),
        Index("ix_support_ann_ack_tenant", "tenant_id"),
    )

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    announcement_id = Column(UUID(as_uuid=True), nullable=False)
    tenant_id       = Column(UUID(as_uuid=True), nullable=False)
    user_id         = Column(UUID(as_uuid=True), nullable=False)
    acknowledged_at = Column(DateTime(timezone=True), nullable=False, default=_now)


class SupportPlatformIncident(Base):
    """Platform incident / maintenance window. Only ServiceOS ops create these
    — the tenant service-status banner is derived from real rows here, and
    reports 'unavailable' when there is no evidence at all."""
    __tablename__ = "support_platform_incidents"
    __table_args__ = (
        Index("ix_support_incidents_status", "status"),
        Index("ix_support_incidents_started", "started_at"),
    )

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reference    = Column(String(40), nullable=True)
    title        = Column(String(300), nullable=False)
    description  = Column(Text, nullable=True)
    severity     = Column(String(20), nullable=False, default="minor")  # maintenance|minor|major
    status       = Column(String(30), nullable=False, default="investigating")
    components   = Column(JSONB, nullable=True)
    started_at   = Column(DateTime(timezone=True), nullable=False, default=_now)
    resolved_at  = Column(DateTime(timezone=True), nullable=True)
    last_checked_at = Column(DateTime(timezone=True), nullable=True)
    created_at   = Column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at   = Column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)


class SupportStatusHeartbeat(Base):
    """Evidence that the platform status projection is live. Without a recent
    heartbeat the banner shows 'Status unavailable' rather than green."""
    __tablename__ = "support_status_heartbeats"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    component     = Column(String(60), nullable=False)
    is_healthy    = Column(Boolean, nullable=False, default=True)
    detail        = Column(Text, nullable=True)
    checked_at    = Column(DateTime(timezone=True), nullable=False, default=_now)
