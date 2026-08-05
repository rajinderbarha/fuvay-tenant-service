"""Compliance Engine — Models (8 tables). All append-only except DataRetentionPolicy and compliance_requests."""
import uuid
from datetime import datetime
from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import ServiceOSBase, utcnow


class DPDPPolicyVersion(ServiceOSBase):
    """A published version of the DPDP (data-protection) compliance policy.

    Real bug fixed here: the `dpdp_policy_versions` table exists and
    public_registration/service.py imports this model to stamp the active
    policy version onto every consent record captured at signup, but the
    model was never written -- so importing that service raised
    ImportError, and the whole 5-step no-payment signup flow it implements
    could never be mounted. Columns mirror the live table exactly.
    """
    __tablename__ = "dpdp_policy_versions"

    policy_name: Mapped[str] = mapped_column(String(255), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(50), nullable=False)
    publication_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    effective_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    enforcement_phase: Mapped[str] = mapped_column(String(50), nullable=False)
    applicable_request_types: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    sla_policy: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    retention_policy_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    evidence_requirements: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    last_policy_review: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    superseded_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    source_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)


class ConsentRecord(ServiceOSBase):
    """PROVEN: immutable — one row per consent event.
    Consent history is a full ledger of every grant/withdraw/update.
    Never UPDATE existing row — always INSERT new one."""
    __tablename__ = "consent_records"
    __table_args__ = (
        Index("ix_cr_user",        "user_id"),
        Index("ix_cr_tenant",      "tenant_id"),
        Index("ix_cr_type_action", "consent_type", "action"),
    )
    user_id:        Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id:      Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    consent_type:   Mapped[str]            = mapped_column(String(50), nullable=False)
    action:         Mapped[str]            = mapped_column(String(20), nullable=False)
    policy_version: Mapped[str]            = mapped_column(String(20), nullable=False)
    granted_at:     Mapped[datetime|None]  = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at:     Mapped[datetime|None]  = mapped_column(DateTime(timezone=True), nullable=True)
    withdrawn_at:   Mapped[datetime|None]  = mapped_column(DateTime(timezone=True), nullable=True)
    ip_address:     Mapped[str|None]       = mapped_column(String(50), nullable=True)
    user_agent:     Mapped[str|None]       = mapped_column(String(500), nullable=True)
    source:         Mapped[str|None]       = mapped_column(String(50), nullable=True)
    meta:           Mapped[dict]           = mapped_column(JSONB, default=dict, nullable=False)


class DataDeletionRequest(ServiceOSBase):
    """Right to erasure — DPDP Act 2023. SLA: 72h from creation.
    PROVEN: exemption_reason stored per row — financial records never erased."""
    __tablename__ = "data_deletion_requests"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_ddr_idem"),
        Index("ix_ddr_user",   "user_id"),
        Index("ix_ddr_status", "status"),
        Index("ix_ddr_sla",    "sla_deadline"),
    )
    user_id:           Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id:         Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    request_reason:    Mapped[str|None]       = mapped_column(String(500), nullable=True)
    status:            Mapped[str]            = mapped_column(String(20), default="pending", nullable=False)
    # PROVEN: 72h SLA deadline stored at creation — Celery uses this
    sla_deadline:      Mapped[datetime]       = mapped_column(DateTime(timezone=True), nullable=False)
    processed_at:      Mapped[datetime|None]  = mapped_column(DateTime(timezone=True), nullable=True)
    tables_erased:     Mapped[list]           = mapped_column(JSONB, default=list, nullable=False)
    tables_exempted:   Mapped[list]           = mapped_column(JSONB, default=list, nullable=False)
    # PROVEN: per-row exemption reason stored for every exempt table
    exemption_reasons: Mapped[dict]           = mapped_column(JSONB, default=dict, nullable=False)
    rejection_reason:  Mapped[str|None]       = mapped_column(String(500), nullable=True)
    processed_by:      Mapped[str|None]       = mapped_column(String(20), default="system", nullable=False)
    idempotency_key:   Mapped[str|None]       = mapped_column(String(64), nullable=True, unique=True)
    verification_token:Mapped[str|None]       = mapped_column(String(64), nullable=True)


class DataPortabilityRequest(ServiceOSBase):
    """Data export — DPDP Act 2023. PROVEN: idempotent on request_id."""
    __tablename__ = "data_portability_requests"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_dpr_idem"),
        Index("ix_dpr_user",   "user_id"),
        Index("ix_dpr_status", "status"),
    )
    user_id:         Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id:       Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    status:          Mapped[str]            = mapped_column(String(20), default="queued", nullable=False)
    sla_deadline:    Mapped[datetime]       = mapped_column(DateTime(timezone=True), nullable=False)
    data_categories: Mapped[list]           = mapped_column(JSONB, default=list, nullable=False)
    export_format:   Mapped[str]            = mapped_column(String(10), default="json", nullable=False)
    storage_key:     Mapped[str|None]       = mapped_column(String(500), nullable=True)
    download_url:    Mapped[str|None]       = mapped_column(String(2000), nullable=True)
    download_expires_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True), nullable=True)
    downloaded_at:   Mapped[datetime|None]  = mapped_column(DateTime(timezone=True), nullable=True)
    record_count:    Mapped[int]            = mapped_column(Integer, default=0, nullable=False)
    size_bytes:      Mapped[int]            = mapped_column(Integer, default=0, nullable=False)
    completed_at:    Mapped[datetime|None]  = mapped_column(DateTime(timezone=True), nullable=True)
    idempotency_key: Mapped[str|None]       = mapped_column(String(64), nullable=True, unique=True)


class DataRetentionPolicy(ServiceOSBase):
    """Per-table retention policy. Checked by Celery purge jobs."""
    __tablename__ = "data_retention_policies"
    __table_args__ = (
        UniqueConstraint("table_name", "tenant_id", name="uq_drp_table_tenant"),
        Index("ix_drp_table", "table_name"),
    )
    table_name:      Mapped[str]            = mapped_column(String(100), nullable=False)
    tenant_id:       Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    retention_days:  Mapped[int]            = mapped_column(Integer, nullable=False)
    is_exempt:       Mapped[bool]           = mapped_column(Boolean, default=False, nullable=False)
    exemption_reason:Mapped[str|None]       = mapped_column(String(500), nullable=True)
    legal_basis:     Mapped[str|None]       = mapped_column(String(200), nullable=True)
    last_purge_at:   Mapped[datetime|None]  = mapped_column(DateTime(timezone=True), nullable=True)
    next_purge_at:   Mapped[datetime|None]  = mapped_column(DateTime(timezone=True), nullable=True)
    set_by:          Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)


class ComplianceAuditLog(ServiceOSBase):
    """APPEND-ONLY. Every data access and compliance action.
    Separate from SecurityEngine audit — this is the legal data-access record."""
    __tablename__ = "compliance_audit_logs"
    __table_args__ = (
        Index("ix_cal_user",      "user_id"),
        Index("ix_cal_action",    "action"),
        Index("ix_cal_created",   "created_at"),
        Index("ix_cal_tenant",    "tenant_id"),
    )
    user_id:       Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    tenant_id:     Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    action:        Mapped[str]            = mapped_column(String(100), nullable=False)
    table_accessed:Mapped[str|None]       = mapped_column(String(100), nullable=True)
    purpose:       Mapped[str|None]       = mapped_column(String(200), nullable=True)
    legal_basis:   Mapped[str|None]       = mapped_column(String(100), nullable=True)
    actor_id:      Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    actor_role:    Mapped[str|None]       = mapped_column(String(30), nullable=True)
    actor_ip:      Mapped[str|None]       = mapped_column(String(50), nullable=True)
    reference_id:  Mapped[str|None]       = mapped_column(String(100), nullable=True)
    meta:          Mapped[dict]           = mapped_column(JSONB, default=dict, nullable=False)


# ── Enterprise DPDP request tables (migration 079) ─────────────────────────


class ComplianceRequest(ServiceOSBase):
    """Enterprise unified compliance request. Covers erasure, export, consent withdrawal, etc."""
    __tablename__ = "compliance_requests"
    __table_args__ = (
        Index("ix_compliance_requests_subject", "subject_id"),
        Index("ix_compliance_requests_status",  "status"),
        Index("ix_compliance_requests_type",    "request_type"),
        Index("ix_compliance_requests_sla",     "sla_status"),
        Index("ix_compliance_requests_due",     "due_at"),
    )
    request_number:       Mapped[str]            = mapped_column(String(30), nullable=False, unique=True)
    subject_type:         Mapped[str]            = mapped_column(String(30), nullable=False)
    subject_id:           Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    subject_email:        Mapped[str|None]       = mapped_column(String(255), nullable=True)
    subject_name:         Mapped[str|None]       = mapped_column(String(200), nullable=True)
    request_type:         Mapped[str]            = mapped_column(String(40), nullable=False)
    status:               Mapped[str]            = mapped_column(String(40), default="submitted", nullable=False)
    sla_status:           Mapped[str]            = mapped_column(String(20), default="on_track", nullable=False)
    verification_status:  Mapped[str]            = mapped_column(String(20), default="not_required", nullable=False)
    submitted_at:         Mapped[datetime|None]  = mapped_column(DateTime(timezone=True), nullable=True)
    due_at:               Mapped[datetime|None]  = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at:         Mapped[datetime|None]  = mapped_column(DateTime(timezone=True), nullable=True)
    assigned_to_admin_id: Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    request_source:       Mapped[str]            = mapped_column(String(30), default="admin_created", nullable=False)
    reason:               Mapped[str|None]       = mapped_column(Text, nullable=True)
    admin_notes:          Mapped[str|None]       = mapped_column(Text, nullable=True)
    rejection_reason:     Mapped[str|None]       = mapped_column(Text, nullable=True)
    metadata_json:        Mapped[dict]           = mapped_column(JSONB, default=dict, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id), "request_number": self.request_number,
            "subject_type": self.subject_type, "subject_id": str(self.subject_id),
            "subject_email": self.subject_email, "subject_name": self.subject_name,
            "request_type": self.request_type, "status": self.status,
            "sla_status": self.sla_status, "verification_status": self.verification_status,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "due_at": self.due_at.isoformat() if self.due_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "assigned_to_admin_id": str(self.assigned_to_admin_id) if self.assigned_to_admin_id else None,
            "request_source": self.request_source, "reason": self.reason,
            "admin_notes": self.admin_notes, "rejection_reason": self.rejection_reason,
            "metadata_json": self.metadata_json,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ComplianceRequestItem(ServiceOSBase):
    """Data inventory scan item per compliance request module."""
    __tablename__ = "compliance_request_items"
    __table_args__ = (
        Index("ix_compliance_request_items_request", "request_id"),
        Index("ix_compliance_request_items_status",  "status"),
    )
    request_id:      Mapped[uuid.UUID]      = mapped_column(
        UUID(as_uuid=True), ForeignKey("compliance_requests.id", ondelete="CASCADE"), nullable=False)
    module_name:     Mapped[str]            = mapped_column(String(100), nullable=False)
    record_type:     Mapped[str]            = mapped_column(String(100), nullable=False)
    record_id:       Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    record_count:    Mapped[int]            = mapped_column(Integer, default=0, nullable=False)
    planned_action:  Mapped[str]            = mapped_column(String(20), default="manual_review", nullable=False)
    actual_action:   Mapped[str|None]       = mapped_column(String(20), nullable=True)
    exemption_reason:Mapped[str|None]       = mapped_column(Text, nullable=True)
    retention_until: Mapped[datetime|None]  = mapped_column(DateTime(timezone=True), nullable=True)
    status:          Mapped[str]            = mapped_column(String(20), default="pending", nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id), "request_id": str(self.request_id),
            "module_name": self.module_name, "record_type": self.record_type,
            "record_id": str(self.record_id) if self.record_id else None,
            "record_count": self.record_count, "planned_action": self.planned_action,
            "actual_action": self.actual_action, "exemption_reason": self.exemption_reason,
            "retention_until": self.retention_until.isoformat() if self.retention_until else None,
            "status": self.status, "created_at": self.created_at.isoformat(),
        }


class ComplianceExport(ServiceOSBase):
    """Enterprise export tracking for data portability requests."""
    __tablename__ = "compliance_exports"
    __table_args__ = (
        Index("ix_compliance_exports_subject", "subject_id"),
        Index("ix_compliance_exports_request", "request_id"),
        Index("ix_compliance_exports_status",  "status"),
    )
    request_id:     Mapped[uuid.UUID|None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("compliance_requests.id", ondelete="SET NULL"), nullable=True)
    subject_type:   Mapped[str]            = mapped_column(String(30), nullable=False)
    subject_id:     Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    export_format:  Mapped[str]            = mapped_column(String(10), default="json", nullable=False)
    status:         Mapped[str]            = mapped_column(String(20), default="pending", nullable=False)
    download_url:   Mapped[str|None]       = mapped_column(String(2000), nullable=True)
    file_size_bytes:Mapped[int|None]       = mapped_column(Integer, nullable=True)
    record_count:   Mapped[int|None]       = mapped_column(Integer, nullable=True)
    expires_at:     Mapped[datetime|None]  = mapped_column(DateTime(timezone=True), nullable=True)
    generated_at:   Mapped[datetime|None]  = mapped_column(DateTime(timezone=True), nullable=True)
    downloaded_at:  Mapped[datetime|None]  = mapped_column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id), "request_id": str(self.request_id) if self.request_id else None,
            "subject_type": self.subject_type, "subject_id": str(self.subject_id),
            "export_format": self.export_format, "status": self.status,
            "download_url": self.download_url, "file_size_bytes": self.file_size_bytes,
            "record_count": self.record_count,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
            "downloaded_at": self.downloaded_at.isoformat() if self.downloaded_at else None,
            "created_at": self.created_at.isoformat(),
        }
