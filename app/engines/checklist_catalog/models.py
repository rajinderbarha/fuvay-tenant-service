"""Checklist Catalog Engine — SQLAlchemy models.

Canonical hierarchy this engine plugs into (already exists, unchanged here):
  ServiceCategory (Business Vertical) -> ServiceGroup -> MasterService
  -> MasterServiceJobType (Job Type) -> ServiceJobWorkflow (Job-Type Blueprint).

A ChecklistTemplate is a reusable, vertical-agnostic logical container (no
AC/Repair/Home-Services hardcoding anywhere in this file). It only becomes
runtime-usable via JobTypeChecklistMapping, which references the exact
existing master_service_job_types row (and, where present, the exact
service_job_workflow blueprint row id — its own row IS the blueprint
version per that table's docstring) — never a category or "applies to" flag.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import ServiceOSBase


class ChecklistTemplate(ServiceOSBase):
    """Reusable logical checklist template (global library entry)."""
    __tablename__ = "checklist_templates"
    __table_args__ = (
        UniqueConstraint("code", name="uq_ct_code"),
        Index("ix_ct_status", "status"),
        Index("ix_ct_owner_scope", "owner_scope"),
    )

    name:               Mapped[str]              = mapped_column(String(200), nullable=False)
    code:               Mapped[str]              = mapped_column(String(80),  nullable=False)
    description:        Mapped[str | None]       = mapped_column(Text, nullable=True)
    icon_url:           Mapped[str | None]       = mapped_column(String(500), nullable=True)
    purpose:            Mapped[str]              = mapped_column(String(30), nullable=False)
    status:             Mapped[str]              = mapped_column(String(20), default="active", nullable=False)
    owner_scope:        Mapped[str]              = mapped_column(String(20), default="PLATFORM", nullable=False)
    tenant_id:          Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id), "name": self.name, "code": self.code,
            "description": self.description, "icon_url": self.icon_url, "purpose": self.purpose,
            "status": self.status, "owner_scope": self.owner_scope,
            "tenant_id": str(self.tenant_id) if self.tenant_id else None,
            "created_by_user_id": str(self.created_by_user_id) if self.created_by_user_id else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ChecklistTemplateVersion(ServiceOSBase):
    """Immutable-once-published content snapshot of a template.

    Editing PUBLISHED content never mutates this row -- the service layer
    creates a new DRAFT version instead (see service.py::create_draft_version).
    In-progress jobs keep the exact version id they snapshotted at
    instantiation time forever, even after a newer version publishes.
    """
    __tablename__ = "checklist_template_versions"
    __table_args__ = (
        UniqueConstraint("checklist_template_id", "version_number", name="uq_ctv_template_version"),
        Index("ix_ctv_template", "checklist_template_id"),
        Index("ix_ctv_status", "status"),
    )

    checklist_template_id: Mapped[uuid.UUID]         = mapped_column(UUID(as_uuid=True), nullable=False)
    version_number:        Mapped[int]               = mapped_column(Integer, nullable=False)
    status:                Mapped[str]               = mapped_column(String(20), default="DRAFT", nullable=False)
    change_summary:        Mapped[str | None]        = mapped_column(Text, nullable=True)
    published_by:          Mapped[uuid.UUID | None]  = mapped_column(UUID(as_uuid=True), nullable=True)
    published_at:          Mapped[datetime | None]   = mapped_column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id), "checklist_template_id": str(self.checklist_template_id),
            "version_number": self.version_number, "status": self.status,
            "change_summary": self.change_summary,
            "published_by": str(self.published_by) if self.published_by else None,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ChecklistSection(ServiceOSBase):
    """Ordered section within a template version."""
    __tablename__ = "checklist_sections"
    __table_args__ = (
        Index("ix_csec_version", "checklist_template_version_id"),
    )

    checklist_template_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    title:                         Mapped[str]        = mapped_column(String(200), nullable=False)
    display_order:                 Mapped[int]        = mapped_column(Integer, default=0, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "checklist_template_version_id": str(self.checklist_template_version_id),
            "title": self.title, "display_order": self.display_order,
        }


class ChecklistItem(ServiceOSBase):
    """Typed checklist item within a section.

    condition_rules is a validated declarative structure (evaluated only in
    the trusted backend gate/service layer -- never arbitrary frontend
    expressions executed server-side). See gate.py::evaluate_condition.
    Shape: {"all": [{"field": "job_type_id"|"brand"|"type"|"problem_code"|
    "answer:<item_id>", "op": "eq"|"neq"|"in", "value": ...}, ...]}
    """
    __tablename__ = "checklist_items"
    __table_args__ = (
        Index("ix_ci_section", "checklist_section_id"),
    )

    checklist_section_id: Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), nullable=False)
    item_type:            Mapped[str]          = mapped_column(String(20), nullable=False)
    label:                Mapped[str]          = mapped_column(String(300), nullable=False)
    help_text:            Mapped[str | None]   = mapped_column(Text, nullable=True)
    is_required:          Mapped[bool]         = mapped_column(Boolean, default=False, nullable=False)
    evidence_required:    Mapped[bool]         = mapped_column(Boolean, default=False, nullable=False)
    min_evidence_count:   Mapped[int]          = mapped_column(Integer, default=0, nullable=False)
    max_evidence_count:   Mapped[int]          = mapped_column(Integer, default=1, nullable=False)
    allowed_file_types:   Mapped[dict | None]  = mapped_column(JSONB, nullable=True)  # ["image/jpeg", ...]
    measurement_unit:     Mapped[str | None]   = mapped_column(String(30), nullable=True)
    select_options:       Mapped[dict | None]  = mapped_column(JSONB, nullable=True)  # [{"value","label"}]
    validation_rules:     Mapped[dict | None]  = mapped_column(JSONB, nullable=True)  # {"min","max","regex",...}
    display_order:        Mapped[int]          = mapped_column(Integer, default=0, nullable=False)
    condition_rules:      Mapped[dict | None]  = mapped_column(JSONB, nullable=True)
    failure_behavior:     Mapped[str | None]   = mapped_column(String(30), nullable=True)  # e.g. ESCALATE, BLOCK
    customer_visible:     Mapped[bool]         = mapped_column(Boolean, default=False, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id), "checklist_section_id": str(self.checklist_section_id),
            "item_type": self.item_type, "label": self.label, "help_text": self.help_text,
            "is_required": self.is_required, "evidence_required": self.evidence_required,
            "min_evidence_count": self.min_evidence_count, "max_evidence_count": self.max_evidence_count,
            "allowed_file_types": self.allowed_file_types, "measurement_unit": self.measurement_unit,
            "select_options": self.select_options, "validation_rules": self.validation_rules,
            "display_order": self.display_order, "condition_rules": self.condition_rules,
            "failure_behavior": self.failure_behavior, "customer_visible": self.customer_visible,
        }


class JobTypeChecklistMapping(ServiceOSBase):
    """Connects a published template VERSION to an exact Job-Type Blueprint.

    master_service_job_type_id is the canonical (master_service, job_type)
    child record (admin_catalog.MasterServiceJobType). service_job_workflow_id
    optionally pins the exact blueprint row (admin_catalog.ServiceJobWorkflow)
    active when the mapping was created, so Repair and Installation under the
    same Master Service always resolve independently.
    """
    __tablename__ = "job_type_checklist_mappings"
    __table_args__ = (
        Index("ix_jtcm_job_type", "master_service_job_type_id"),
        Index("ix_jtcm_version", "checklist_template_version_id"),
        Index("ix_jtcm_status", "status"),
        UniqueConstraint(
            "master_service_job_type_id", "checklist_template_version_id", "phase",
            name="uq_jtcm_job_type_version_phase",
        ),
    )

    master_service_job_type_id:    Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    service_job_workflow_id:       Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    checklist_template_version_id: Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    phase:                         Mapped[str]              = mapped_column(String(30), nullable=False)
    usage:                         Mapped[str]              = mapped_column(String(20), default="OPTIONAL", nullable=False)
    actor:                         Mapped[str]              = mapped_column(String(20), default="TECHNICIAN", nullable=False)
    completion_gate:               Mapped[str]              = mapped_column(String(50), default="NONE", nullable=False)
    condition_rules:               Mapped[dict | None]      = mapped_column(JSONB, nullable=True)
    display_order:                 Mapped[int]              = mapped_column(Integer, default=0, nullable=False)
    status:                        Mapped[str]              = mapped_column(String(20), default="active", nullable=False)
    effective_from:                Mapped[datetime | None]  = mapped_column(DateTime(timezone=True), nullable=True)
    effective_until:                Mapped[datetime | None]  = mapped_column(DateTime(timezone=True), nullable=True)
    created_by:                    Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    updated_by:                    Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "master_service_job_type_id": str(self.master_service_job_type_id),
            "service_job_workflow_id": str(self.service_job_workflow_id) if self.service_job_workflow_id else None,
            "checklist_template_version_id": str(self.checklist_template_version_id),
            "phase": self.phase, "usage": self.usage, "actor": self.actor,
            "completion_gate": self.completion_gate, "condition_rules": self.condition_rules,
            "display_order": self.display_order, "status": self.status,
            "effective_from": self.effective_from.isoformat() if self.effective_from else None,
            "effective_until": self.effective_until.isoformat() if self.effective_until else None,
            "created_by": str(self.created_by) if self.created_by else None,
            "updated_by": str(self.updated_by) if self.updated_by else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class JobChecklistInstance(ServiceOSBase):
    """A resolved, per-job checklist instance, snapshotted at creation time.

    Snapshotting template_version_id (immutable content) means publishing a
    new template version never alters an in-progress job's checklist.
    """
    __tablename__ = "job_checklist_instances"
    __table_args__ = (
        Index("ix_jci_job", "job_id"),
        Index("ix_jci_mapping", "mapping_id"),
        Index("ix_jci_tenant", "tenant_id"),
        UniqueConstraint("job_id", "mapping_id", name="uq_jci_job_mapping"),
    )

    job_id:                Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id:             Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    mapping_id:            Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    checklist_template_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    phase:                 Mapped[str]              = mapped_column(String(30), nullable=False)
    assigned_actor:        Mapped[str]              = mapped_column(String(20), nullable=False)
    state:                 Mapped[str]              = mapped_column(String(20), default="NOT_STARTED", nullable=False)
    started_at:            Mapped[datetime | None]  = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at:          Mapped[datetime | None]  = mapped_column(DateTime(timezone=True), nullable=True)
    completed_by:          Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    waived_by:             Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    waived_at:             Mapped[datetime | None]  = mapped_column(DateTime(timezone=True), nullable=True)
    waiver_reason:         Mapped[str | None]       = mapped_column(Text, nullable=True)
    snapshot_metadata:      Mapped[dict | None]      = mapped_column(JSONB, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id), "job_id": str(self.job_id), "tenant_id": str(self.tenant_id),
            "mapping_id": str(self.mapping_id),
            "checklist_template_version_id": str(self.checklist_template_version_id),
            "phase": self.phase, "assigned_actor": self.assigned_actor, "state": self.state,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "completed_by": str(self.completed_by) if self.completed_by else None,
            "waived_by": str(self.waived_by) if self.waived_by else None,
            "waived_at": self.waived_at.isoformat() if self.waived_at else None,
            "waiver_reason": self.waiver_reason, "snapshot_metadata": self.snapshot_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class JobChecklistResponse(ServiceOSBase):
    """A single item's response within a job checklist instance.

    checklist_item_id is retained even if the item definition later changes
    on a newer template version -- historical rows are never rewritten.
    """
    __tablename__ = "job_checklist_responses"
    __table_args__ = (
        Index("ix_jcr_instance", "job_checklist_instance_id"),
        Index("ix_jcr_item", "checklist_item_id"),
        UniqueConstraint("job_checklist_instance_id", "checklist_item_id", name="uq_jcr_instance_item"),
    )

    job_checklist_instance_id: Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    checklist_item_id:         Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    response_value:            Mapped[dict | None]      = mapped_column(JSONB, nullable=True)
    actor_user_id:              Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    submitted_at:               Mapped[datetime | None]  = mapped_column(DateTime(timezone=True), nullable=True)
    last_updated_at:            Mapped[datetime | None]  = mapped_column(DateTime(timezone=True), nullable=True)
    evidence:                  Mapped[dict | None]      = mapped_column(JSONB, nullable=True)  # [{"file_id","uploader_id","uploaded_at","content_type","size_bytes"}]
    validation_result:          Mapped[dict | None]      = mapped_column(JSONB, nullable=True)  # {"valid": bool, "errors": [...]}

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "job_checklist_instance_id": str(self.job_checklist_instance_id),
            "checklist_item_id": str(self.checklist_item_id),
            "response_value": self.response_value,
            "actor_user_id": str(self.actor_user_id) if self.actor_user_id else None,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "last_updated_at": self.last_updated_at.isoformat() if self.last_updated_at else None,
            "evidence": self.evidence, "validation_result": self.validation_result,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
