"""Legal Documents — resolution, authoring and publication.

The one piece of real logic here is :func:`get_live`. Everything else is
CRUD with a lifecycle guard.
"""
from __future__ import annotations

import uuid
from datetime import datetime

import structlog
from sqlalchemy import func as sa_func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ServiceOSException
from app.models.base import utcnow

from app.engines.legal_documents import constants as C
from app.engines.legal_documents.models import LegalDocumentVersion

logger = structlog.get_logger(__name__)


# ── Validation helpers ───────────────────────────────────────────────────────
def _require_doc_type(doc_type: str) -> str:
    if doc_type not in C.VALID_DOC_TYPES:
        raise ServiceOSException(
            "LEGAL_DOC_TYPE_UNKNOWN",
            "That is not a legal document type.",
            status_code=404,
            resolution="Use one of: " + ", ".join(sorted(C.VALID_DOC_TYPES)) + ".",
        )
    return doc_type


def _require_audience(audience: str) -> str:
    if audience not in C.VALID_AUDIENCES:
        raise ServiceOSException(
            "LEGAL_AUDIENCE_UNKNOWN",
            "That is not a valid audience.",
            status_code=422,
            resolution="Use one of: " + ", ".join(sorted(C.VALID_AUDIENCES)) + ".",
        )
    return audience


# ── Public resolution ────────────────────────────────────────────────────────
async def get_live(
    db: AsyncSession,
    *,
    doc_type: str,
    audience: str = C.AUDIENCE_ALL,
    locale: str = C.DEFAULT_LOCALE,
    at: datetime | None = None,
) -> LegalDocumentVersion | None:
    """Resolve the version governing ``doc_type`` right now.

    "Live" means published AND already in effect — ``effective_at <= now``.
    A version scheduled for next month is published but not yet governing, so
    it must not be served; serving it would show people terms that do not bind
    them yet, and would stamp a not-yet-effective version onto their consent.

    Falls back twice, narrowest first: the requested audience before ``all``,
    and the requested locale before ``en``. A tenant-specific Terms therefore
    overrides the shared one the moment it is published, with no pointer to
    repoint by hand.
    """
    _require_doc_type(doc_type)
    _require_audience(audience)
    now = at or utcnow()

    audiences = [audience] if audience == C.AUDIENCE_ALL else [audience, C.AUDIENCE_ALL]
    locales = [locale] if locale == C.DEFAULT_LOCALE else [locale, C.DEFAULT_LOCALE]

    candidates: list[tuple[str, str]] = []
    for aud in audiences:
        for loc in locales:
            if (aud, loc) not in candidates:
                candidates.append((aud, loc))

    for aud, loc in candidates:
        row = (await db.execute(
            select(LegalDocumentVersion)
            .where(
                LegalDocumentVersion.doc_type == doc_type,
                LegalDocumentVersion.audience == aud,
                LegalDocumentVersion.locale == loc,
                LegalDocumentVersion.status == C.STATUS_PUBLISHED,
                LegalDocumentVersion.effective_at.isnot(None),
                LegalDocumentVersion.effective_at <= now,
            )
            .order_by(LegalDocumentVersion.effective_at.desc())
            .limit(1)
        )).scalars().first()
        if row is not None:
            return row
    return None


async def require_live(
    db: AsyncSession,
    *,
    doc_type: str,
    audience: str = C.AUDIENCE_ALL,
    locale: str = C.DEFAULT_LOCALE,
) -> LegalDocumentVersion:
    row = await get_live(db, doc_type=doc_type, audience=audience, locale=locale)
    if row is None:
        label = C.VALID_DOC_TYPES.get(doc_type, doc_type)
        raise ServiceOSException(
            "LEGAL_DOC_NOT_PUBLISHED",
            "No " + label + " has been published yet.",
            status_code=404,
            resolution="Publish a version from Admin → Legal Documents.",
        )
    return row


async def list_live(
    db: AsyncSession,
    *,
    audience: str = C.AUDIENCE_ALL,
    locale: str = C.DEFAULT_LOCALE,
) -> list[dict]:
    """Index of every document that currently has a live version.

    Document types with nothing published are omitted rather than returned
    empty, so a client rendering this list never links to a 404.
    """
    out: list[dict] = []
    for doc_type in C.VALID_DOC_TYPES:
        row = await get_live(db, doc_type=doc_type, audience=audience, locale=locale)
        if row is None:
            continue
        out.append({
            "doc_type": row.doc_type,
            "title": row.title,
            "version": row.version,
            "audience": row.audience,
            "locale": row.locale,
            "effective_at": row.effective_at.isoformat() if row.effective_at else None,
            "path": "/v1/public/legal/" + row.doc_type,
        })
    return out


async def consent_references(
    db: AsyncSession,
    *,
    audience: str = C.AUDIENCE_ALL,
    locale: str = C.DEFAULT_LOCALE,
) -> list[dict]:
    """The document versions a signup consent should be stamped against.

    Returns whatever is live; an unpublished document yields no reference
    rather than an error. Signup must not become unable to complete because a
    policy has not been authored yet — the consent row is still written, it
    simply records that no versioned text existed at that moment.
    """
    refs: list[dict] = []
    for doc_type in C.SIGNUP_CONSENT_DOC_TYPES:
        row = await get_live(db, doc_type=doc_type, audience=audience, locale=locale)
        if row is not None:
            refs.append(row.to_reference())
    return refs


# ── Admin authoring ──────────────────────────────────────────────────────────
async def get_version(db: AsyncSession, version_id: uuid.UUID) -> LegalDocumentVersion:
    row = (await db.execute(
        select(LegalDocumentVersion).where(LegalDocumentVersion.id == version_id)
    )).scalars().first()
    if row is None:
        raise ServiceOSException(
            "LEGAL_DOC_VERSION_NOT_FOUND",
            "That legal document version does not exist.",
            status_code=404,
        )
    return row


async def list_versions(
    db: AsyncSession,
    *,
    doc_type: str | None = None,
    status: str | None = None,
    audience: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[LegalDocumentVersion], int]:
    conditions = []
    if doc_type:
        conditions.append(LegalDocumentVersion.doc_type == _require_doc_type(doc_type))
    if status:
        if status not in C.VALID_STATUSES:
            raise ServiceOSException(
                "LEGAL_STATUS_UNKNOWN",
                "That is not a valid status.",
                status_code=422,
            )
        conditions.append(LegalDocumentVersion.status == status)
    if audience:
        conditions.append(LegalDocumentVersion.audience == _require_audience(audience))

    total = (await db.execute(
        select(sa_func.count()).select_from(LegalDocumentVersion).where(*conditions)
    )).scalar_one()

    rows = (await db.execute(
        select(LegalDocumentVersion)
        .where(*conditions)
        # Newest authoring activity first. A draft has no effective_at, so
        # ordering on created_at keeps drafts at the top instead of sorting
        # them last behind every published version.
        .order_by(LegalDocumentVersion.created_at.desc())
        .limit(limit).offset(offset)
    )).scalars().all()
    return list(rows), int(total)


async def create_draft(
    db: AsyncSession,
    *,
    doc_type: str,
    version: str,
    title: str,
    body: str,
    summary: str | None = None,
    audience: str = C.AUDIENCE_ALL,
    locale: str = C.DEFAULT_LOCALE,
    requires_reacceptance: bool = False,
    change_note: str | None = None,
    actor_id: uuid.UUID | None = None,
) -> LegalDocumentVersion:
    _require_doc_type(doc_type)
    _require_audience(audience)

    clash = (await db.execute(
        select(LegalDocumentVersion.id).where(
            LegalDocumentVersion.doc_type == doc_type,
            LegalDocumentVersion.audience == audience,
            LegalDocumentVersion.locale == locale,
            LegalDocumentVersion.version == version,
        )
    )).scalars().first()
    if clash:
        raise ServiceOSException(
            "LEGAL_DOC_VERSION_EXISTS",
            "Version " + version + " of this document already exists.",
            status_code=409,
            resolution="Choose a different version label.",
        )

    row = LegalDocumentVersion(
        doc_type=doc_type, audience=audience, locale=locale, version=version,
        title=title, summary=summary, body=body,
        body_format=C.BODY_FORMAT_MARKDOWN, status=C.STATUS_DRAFT,
        requires_reacceptance=requires_reacceptance, change_note=change_note,
        created_by=actor_id,
    )
    db.add(row)
    await db.flush()
    logger.info("legal_documents.draft_created",
                doc_type=doc_type, version=version, audience=audience)
    return row


async def update_draft(
    db: AsyncSession,
    version_id: uuid.UUID,
    *,
    title: str | None = None,
    summary: str | None = None,
    body: str | None = None,
    version: str | None = None,
    requires_reacceptance: bool | None = None,
    change_note: str | None = None,
) -> LegalDocumentVersion:
    """Edit a draft.

    Published versions are immutable. Someone has already accepted the text at
    that id, and editing it in place would silently rewrite what they agreed
    to — the audit trail would then point at words they never saw. Corrections
    are made by publishing a new version.
    """
    row = await get_version(db, version_id)
    if row.status != C.STATUS_DRAFT:
        raise ServiceOSException(
            "LEGAL_DOC_NOT_EDITABLE",
            "A published or archived version cannot be edited.",
            status_code=409,
            blocking_rule="legal_document.immutable_after_publish",
            resolution="Create a new draft version instead.",
        )

    if version is not None and version != row.version:
        clash = (await db.execute(
            select(LegalDocumentVersion.id).where(
                LegalDocumentVersion.doc_type == row.doc_type,
                LegalDocumentVersion.audience == row.audience,
                LegalDocumentVersion.locale == row.locale,
                LegalDocumentVersion.version == version,
                LegalDocumentVersion.id != row.id,
            )
        )).scalars().first()
        if clash:
            raise ServiceOSException(
                "LEGAL_DOC_VERSION_EXISTS",
                "Version " + version + " of this document already exists.",
                status_code=409,
            )
        row.version = version

    if title is not None:
        row.title = title
    if summary is not None:
        row.summary = summary
    if body is not None:
        row.body = body
    if requires_reacceptance is not None:
        row.requires_reacceptance = requires_reacceptance
    if change_note is not None:
        row.change_note = change_note

    await db.flush()
    return row


async def publish(
    db: AsyncSession,
    version_id: uuid.UUID,
    *,
    effective_at: datetime | None = None,
    actor_id: uuid.UUID | None = None,
) -> LegalDocumentVersion:
    """Publish a draft, archiving the version it supersedes.

    The predecessor is archived rather than deleted: consent records point at
    it by id, and those references must keep resolving to real text forever.
    """
    row = await get_version(db, version_id)
    if row.status == C.STATUS_PUBLISHED:
        raise ServiceOSException(
            "LEGAL_DOC_ALREADY_PUBLISHED",
            "That version is already published.",
            status_code=409,
        )
    if row.status == C.STATUS_ARCHIVED:
        raise ServiceOSException(
            "LEGAL_DOC_ARCHIVED",
            "An archived version cannot be republished.",
            status_code=409,
            resolution="Create a new draft from its text instead.",
        )
    if not (row.body or "").strip():
        raise ServiceOSException(
            "LEGAL_DOC_BODY_EMPTY",
            "A document cannot be published with an empty body.",
            status_code=422,
        )

    now = utcnow()
    effective = effective_at or now

    # Archive the currently-governing version only when the new one takes
    # effect immediately. A future-dated publication must leave the incumbent
    # live, or the document would go dark in the gap between the two.
    if effective <= now:
        current = await get_live(
            db, doc_type=row.doc_type, audience=row.audience,
            locale=row.locale, at=now,
        )
        if current is not None and current.id != row.id:
            current.status = C.STATUS_ARCHIVED
            current.archived_at = now

    row.status = C.STATUS_PUBLISHED
    row.effective_at = effective
    row.published_at = now
    row.published_by = actor_id
    await db.flush()
    logger.info("legal_documents.published",
                doc_type=row.doc_type, version=row.version,
                effective_at=effective.isoformat())
    return row


async def archive(db: AsyncSession, version_id: uuid.UUID) -> LegalDocumentVersion:
    row = await get_version(db, version_id)
    if row.status == C.STATUS_ARCHIVED:
        return row
    if row.status == C.STATUS_DRAFT:
        raise ServiceOSException(
            "LEGAL_DOC_NOT_PUBLISHED",
            "A draft is deleted, not archived.",
            status_code=409,
        )
    row.status = C.STATUS_ARCHIVED
    row.archived_at = utcnow()
    await db.flush()
    return row


async def delete_draft(db: AsyncSession, version_id: uuid.UUID) -> None:
    """Hard-delete a draft. Only a draft — nothing can have accepted it."""
    row = await get_version(db, version_id)
    if row.status != C.STATUS_DRAFT:
        raise ServiceOSException(
            "LEGAL_DOC_NOT_EDITABLE",
            "Only a draft can be deleted. Archive a published version instead.",
            status_code=409,
        )
    await db.delete(row)
    await db.flush()
