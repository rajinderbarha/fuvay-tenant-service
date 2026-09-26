"""Public Registration Engine — Models.

PendingTenantRegistration is the working record for the 5-step no-payment
signup flow (Owner Account -> Verify Contact -> Business Identity ->
Select Vertical -> Review & Consent -> Create Workspace). It is NOT the
final Tenant/User — those are created atomically at step 5. Keeping this
as its own table (rather than half-baked User/Tenant rows) means an
abandoned signup never leaves an orphan login-capable account behind.
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import ServiceOSBase, utcnow


class PendingTenantRegistration(ServiceOSBase):
    __tablename__ = "pending_tenant_registrations"
    __table_args__ = (
        Index("ix_ptr_email", "email"),
        Index("ix_ptr_mobile", "mobile"),
        Index("ix_ptr_status", "status"),
    )

    # Step 1 — Owner Account
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    mobile: Mapped[str] = mapped_column(String(20), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    authorized_declaration: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    tos_privacy_accepted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    marketing_consent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Step 2 — Verify Contact
    mobile_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Step 3 — Business Identity (partial/autosave)
    legal_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    business_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    gstin: Mapped[str | None] = mapped_column(String(20), nullable=True)
    pan: Mapped[str | None] = mapped_column(String(10), nullable=True)
    cin: Mapped[str | None] = mapped_column(String(25), nullable=True)
    business_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    year_established: Mapped[int | None] = mapped_column(Integer, nullable=True)
    employee_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    website_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Legal/registered address only — this is NOT service coverage. Service
    # coverage (zipcodes/city-tier) is collected post-signup in the vertical
    # setup wizard, never here.
    registered_address: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # Step 4 — Select Vertical (selection only; enrollment row created at step 5)
    selected_vertical_key: Mapped[str | None] = mapped_column(String(80), nullable=True)

    # Step 5 — Review & Consent -> Create Workspace
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="in_progress")
    # in_progress -> identity_review | completed | abandoned
    idempotency_key: Mapped[str | None] = mapped_column(String(100), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_tenant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)


class ProviderIdentityReviewCase(ServiceOSBase):
    """Durable provider re-registration/evasion review.

    A provider's operational history belongs to the legal business, not to an
    email address.  This record prevents a suspended/penalised provider from
    receiving a clean tenant merely by changing contact details.  Evidence is
    intentionally signal-only; raw tax identifiers are not copied here.
    """

    __tablename__ = "provider_identity_review_cases"
    __table_args__ = (
        UniqueConstraint(
            "registration_id", "matched_tenant_id",
            name="uq_provider_identity_review_registration_tenant",
        ),
        Index("ix_pirc_status_created", "status", "created_at"),
        Index("ix_pirc_matched_tenant", "matched_tenant_id"),
    )

    registration_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    matched_tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="open")
    match_strength: Mapped[str] = mapped_column(String(20), nullable=False)
    match_signals: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    risk_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    decision: Mapped[str | None] = mapped_column(String(40), nullable=True)
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
