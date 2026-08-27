"""Legal Documents — one table, one row per published version.

A single table rather than a document/version pair. The "document" is nothing
more than its type, which is a constant in ``constants.VALID_DOC_TYPES``, so a
parent table would hold a primary key and a label already known at import
time. More importantly, a parent row carrying a ``current_version_id`` pointer
is a second source of truth that can disagree with the version rows themselves;
here "current" is derived — the published row with the latest ``effective_at``
that has already come into effect — so it cannot drift.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import ServiceOSBase

from app.engines.legal_documents import constants as C


class LegalDocumentVersion(ServiceOSBase):
    """One version of one legal document, for one audience and locale."""

    __tablename__ = "legal_document_versions"
    __table_args__ = (
        # Version strings are author-supplied ("1.0", "2026-08"), so this is
        # what stops two published rows claiming to be the same version of the
        # same document — which would make a consent record ambiguous about
        # what was actually accepted.
        UniqueConstraint("doc_type", "audience", "locale", "version",
                         name="uq_legal_doc_version"),
        # Serves the hot path: resolve the live document for a type+audience.
        Index("ix_legal_doc_live", "doc_type", "audience", "locale", "effective_at"),
        Index("ix_legal_doc_status", "status"),
    )

    doc_type: Mapped[str] = mapped_column(String(40), nullable=False)
    audience: Mapped[str] = mapped_column(
        String(20), nullable=False, default=C.AUDIENCE_ALL,
    )
    locale: Mapped[str] = mapped_column(
        String(10), nullable=False, default=C.DEFAULT_LOCALE,
    )
    #: Author-chosen, displayed to the person accepting and written into the
    #: consent record. Not auto-incremented: legal teams version by their own
    #: scheme and a surprise renumbering would break the audit trail.
    version: Mapped[str] = mapped_column(String(20), nullable=False)

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    #: One-paragraph lead shown above the body.
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    body_format: Mapped[str] = mapped_column(
        String(20), nullable=False, default=C.BODY_FORMAT_MARKDOWN,
    )

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=C.STATUS_DRAFT,
    )
    #: When this version starts governing. Set at publish time; may be in the
    #: future so a change can be scheduled and announced before it binds.
    effective_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    #: True when the change is significant enough that existing users must
    #: re-accept. Read by the re-consent check; publishing does not act on it
    #: by itself.
    requires_reacceptance: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
    )
    #: Author-facing note ("added clause 7 on data retention"). Never shown to
    #: the person accepting.
    change_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    published_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    meta: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # ── Serialisation ────────────────────────────────────────────────────────
    def to_public_dict(self) -> dict:
        """What an unauthenticated caller may see.

        Excludes the authoring trail (``change_note``, ``created_by``,
        ``published_by``, ``status``) — those describe how the document was
        made, which is internal, not part of the published text.
        """
        return {
            "id": str(self.id),
            "doc_type": self.doc_type,
            "audience": self.audience,
            "locale": self.locale,
            "version": self.version,
            "title": self.title,
            "summary": self.summary,
            "body": self.body,
            "body_format": self.body_format,
            "effective_at": self.effective_at.isoformat() if self.effective_at else None,
            "published_at": self.published_at.isoformat() if self.published_at else None,
        }

    def to_admin_dict(self, *, include_body: bool = True) -> dict:
        data = {
            "id": str(self.id),
            "doc_type": self.doc_type,
            "doc_type_label": C.VALID_DOC_TYPES.get(self.doc_type, self.doc_type),
            "audience": self.audience,
            "locale": self.locale,
            "version": self.version,
            "title": self.title,
            "summary": self.summary,
            "body_format": self.body_format,
            "status": self.status,
            "effective_at": self.effective_at.isoformat() if self.effective_at else None,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "archived_at": self.archived_at.isoformat() if self.archived_at else None,
            "requires_reacceptance": self.requires_reacceptance,
            "change_note": self.change_note,
            "created_by": str(self.created_by) if self.created_by else None,
            "published_by": str(self.published_by) if self.published_by else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_body:
            data["body"] = self.body
        return data

    def to_reference(self) -> dict:
        """The compact form stamped into ``consent_records.meta``.

        Deliberately small and self-contained: the id resolves back to the
        exact text, and version/effective_at stay readable even if the row is
        later archived.
        """
        return {
            "id": str(self.id),
            "doc_type": self.doc_type,
            "version": self.version,
            "audience": self.audience,
            "locale": self.locale,
            "effective_at": self.effective_at.isoformat() if self.effective_at else None,
        }
