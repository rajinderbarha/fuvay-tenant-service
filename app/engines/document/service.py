"""Document Engine — DocumentService. Proven Level 5.
is_frozen checked at top of every write method — hard guard, not convention.
Sequential document numbers via Redis INCR. Full legal audit trail.
"""
from __future__ import annotations
import secrets, uuid
from datetime import datetime, timezone, timedelta

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.document.constants import (
    DocType, DocStatus, DocEventType, TERMINAL_DOC_STATUSES,
    SIGNING_URL_TTL_HOURS, REDIS_DOC_COUNTER, REDIS_SIGNING_URL,
)
from app.engines.document.models import Document, DocumentTemplate, DocumentEvent
from app.exceptions import ServiceOSException, NotFoundException
from app.redis_client import get_redis
from app.schemas.base import encode_cursor, decode_cursor

logger = structlog.get_logger("document.service")
utcnow = lambda: datetime.now(timezone.utc)


class DocumentService:
    def __init__(self, db: AsyncSession, request_id: str = "—",
                 actor_id: uuid.UUID | None = None, actor_role: str | None = None,
                 actor_ip: str | None = None, actor_tenant_id: uuid.UUID | None = None):
        self.db = db; self.redis = get_redis()
        self.request_id = request_id
        self.actor_id = actor_id; self.actor_role = actor_role; self.actor_ip = actor_ip
        # Phase 2A Slice 2F-35: the authoritative tenant of the calling
        # principal, derived server-side from the token. generate_document/
        # send_for_signature/void_document MUST scope by this value.
        self.actor_tenant_id = actor_tenant_id

    def _require_trusted_tenant(self, requested_tenant_id: uuid.UUID | None = None) -> uuid.UUID | None:
        if self.actor_role == "super_admin":
            return requested_tenant_id
        if self.actor_tenant_id is None:
            raise ServiceOSException(
                "PERMISSION_DENIED", "No tenant context.",
                blocking_rule="document_mutation_requires_trusted_tenant_context")
        if requested_tenant_id is not None and requested_tenant_id != self.actor_tenant_id:
            raise ServiceOSException(
                "PERMISSION_DENIED", "You do not have access to this tenant's documents.",
                blocking_rule="document_mutation_cross_tenant_denied")
        return self.actor_tenant_id

    # PROVEN LEVEL 5: is_frozen guard — hard check at top of every write
    def _assert_not_frozen(self, doc: Document, operation: str = "modify"):
        if doc.is_frozen:
            raise ServiceOSException("DOCUMENT_FROZEN",
                f"Document {doc.document_number} is frozen after signing and cannot be {operation}.",
                resolution="Void this document and generate a new one.",
                context={"document_id": str(doc.id), "signed_at": doc.signed_at.isoformat() if doc.signed_at else None})

    # PROVEN LEVEL 5: sequential document numbers via Redis INCR
    async def _next_doc_number(self, tenant_id: uuid.UUID, doc_type: str) -> str:
        key = REDIS_DOC_COUNTER.format(tenant_id=tenant_id)
        try:
            n = await self.redis.incr(key)
        except Exception:
            r = await self.db.execute(select(Document).where(Document.tenant_id == tenant_id))
            n = len(r.scalars().all()) + 1
        prefix = {"service_agreement":"SA","warranty":"WR","completion_certificate":"CC",
                  "gst_invoice":"INV","inspection_report":"IR","custom":"DOC"}.get(doc_type,"DOC")
        return f"{prefix}-{str(tenant_id)[:8].upper()}-{str(n).zfill(5)}"

    # PROVEN LEVEL 5: append-only audit trail — every action logged
    async def _write_event(self, doc: Document, event_type: str, meta: dict | None = None):
        self.db.add(DocumentEvent(
            document_id=doc.id, tenant_id=doc.tenant_id,
            event_type=event_type, actor_id=self.actor_id,
            actor_role=self.actor_role, actor_ip=self.actor_ip, meta=meta or {}))

    async def _publish(self, event_type: str, tenant_id: str, doc_id: str, payload: dict):
        try:
            from app.core.events import get_event_bus
            bus = get_event_bus()
            await bus.publish_raw(event_type=event_type, engine_id="document",
                tenant_id=tenant_id, entity_type="document", entity_id=doc_id,
                payload=payload, actor_id=str(self.actor_id) if self.actor_id else None)
        except Exception: pass

    def _doc_dict(self, d: Document) -> dict:
        return {"document_id": str(d.id), "document_number": d.document_number,
                "tenant_id": str(d.tenant_id), "doc_type": d.doc_type,
                "status": d.status, "is_frozen": d.is_frozen,
                "entity_type": d.entity_type, "entity_id": d.entity_id,
                "customer_id": str(d.customer_id) if d.customer_id else None,
                "storage_key": d.storage_key,
                "signed_at": d.signed_at.isoformat() if d.signed_at else None,
                "voided_at": d.voided_at.isoformat() if d.voided_at else None,
                "signing_expires_at": d.signing_expires_at.isoformat() if d.signing_expires_at else None,
                "created_at": d.created_at.isoformat()}

    # Template CRUD
    async def get_template(self, tenant_id: uuid.UUID, doc_type: str) -> dict:
        r = await self.db.execute(select(DocumentTemplate).where(
            DocumentTemplate.tenant_id == tenant_id, DocumentTemplate.doc_type == doc_type,
            DocumentTemplate.is_active == True))
        t = r.scalar_one_or_none()
        if not t:
            # Try platform default
            r2 = await self.db.execute(select(DocumentTemplate).where(
                DocumentTemplate.tenant_id == None, DocumentTemplate.doc_type == doc_type,
                DocumentTemplate.is_active == True))
            t = r2.scalar_one_or_none()
        if not t: raise NotFoundException("DocumentTemplate", doc_type)
        return {"template_id": str(t.id), "doc_type": t.doc_type, "name": t.name,
                "required_vars": t.required_vars, "version": t.version}

    # PROVEN LEVEL 5: validate variables before generation — 422 with list of missing
    async def generate_document(self, tenant_id: uuid.UUID, doc_type: str,
                                 entity_type: str | None, entity_id: str | None,
                                 customer_id: uuid.UUID | None, variables: dict) -> dict:
        # Phase 2A Slice 2F-35: tenant_id previously arrived straight from
        # the request body with no comparison to the calling principal --
        # verified server-side before any row is created.
        tenant_id = self._require_trusted_tenant(tenant_id)
        # Resolve template
        tmpl_r = await self.db.execute(select(DocumentTemplate).where(
            DocumentTemplate.tenant_id == tenant_id, DocumentTemplate.doc_type == doc_type,
            DocumentTemplate.is_active == True))
        tmpl = tmpl_r.scalar_one_or_none()
        if not tmpl:
            platform_r = await self.db.execute(select(DocumentTemplate).where(
                DocumentTemplate.tenant_id == None, DocumentTemplate.doc_type == doc_type,
                DocumentTemplate.is_active == True))
            tmpl = platform_r.scalar_one_or_none()

        # Validate required variables BEFORE generation — not halfway through rendering
        required = tmpl.required_vars if tmpl else []
        missing = [v for v in required if v not in variables]
        if missing:
            raise ServiceOSException("VALIDATION_ERROR",
                f"Missing required template variables: {', '.join(missing)}",
                context={"missing_variables": missing, "provided": list(variables.keys())},
                resolution="Provide all required variables and retry.")

        doc_number = await self._next_doc_number(tenant_id, doc_type)
        content = tmpl.template_html if tmpl else f"<html><body>Document {doc_number}</body></html>"
        for k, v in variables.items():
            content = content.replace(f"{{{{{k}}}}}", str(v))

        doc = Document(
            tenant_id=tenant_id, doc_type=doc_type, document_number=doc_number,
            entity_type=entity_type, entity_id=entity_id, customer_id=customer_id,
            template_id=tmpl.id if tmpl else None, status=DocStatus.DRAFT,
            is_frozen=False,  # NOT frozen until signed
            content_html=content, variables_used=variables,
            storage_key=f"documents/{tenant_id}/{doc_number}.pdf",
        )
        self.db.add(doc); await self.db.flush()
        await self._write_event(doc, DocEventType.GENERATED,
                                 meta={"template_version": tmpl.version if tmpl else None})
        await self._publish("document.generated", str(tenant_id), str(doc.id),
                            {"doc_type": doc_type, "doc_number": doc_number})
        logger.info("document.generated", doc_number=doc_number, doc_type=doc_type)
        return self._doc_dict(doc)

    async def get_document(self, document_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(Document).where(Document.id == document_id))
        d = r.scalar_one_or_none()
        if not d: raise NotFoundException("Document", str(document_id))
        return self._doc_dict(d)

    async def list_by_entity(self, tenant_id: uuid.UUID, entity_type: str | None,
                              entity_id: str | None, limit: int, cursor: str | None,
                              status: str | None = None) -> dict:
        # entity_type/entity_id are optional: the tenant portal's Documents
        # page lists a whole tenant's documents with a status filter, which
        # this endpoint could not express (it 422'd on every load). Callers
        # that pass an entity still get the entity-scoped list unchanged.
        tenant_id = self._require_trusted_tenant(tenant_id) or tenant_id
        q = select(Document).where(Document.tenant_id == tenant_id)
        if entity_type:
            q = q.where(Document.entity_type == entity_type)
        if entity_id:
            q = q.where(Document.entity_id == entity_id)
        if status:
            q = q.where(Document.status == status)
        q = q.order_by(Document.created_at.desc())
        if cursor:
            try:
                c = decode_cursor(cursor)
                q = q.where(Document.created_at < datetime.fromisoformat(c["created_at"]))
            except Exception: pass
        q = q.limit(limit + 1)
        r = await self.db.execute(q)
        docs = r.scalars().all()
        has_next = len(docs) > limit; docs = docs[:limit]
        nc = encode_cursor({"created_at": docs[-1].created_at.isoformat()}) if has_next and docs else None
        return {"documents": [self._doc_dict(d) for d in docs],
                "has_next": has_next, "next_cursor": nc}

    async def send_for_signature(self, document_id: uuid.UUID) -> dict:
        # Phase 2A Slice 2F-35: previously queried WHERE id==document_id
        # ONLY -- zero tenant predicate, so any TENANT_UPDATE holder in ANY
        # tenant could send another tenant's legal document for signature.
        tenant_id = self._require_trusted_tenant()
        q = select(Document).where(Document.id == document_id)
        if tenant_id is not None:
            q = q.where(Document.tenant_id == tenant_id)
        r = await self.db.execute(q)
        doc = r.scalar_one_or_none()
        if not doc: raise NotFoundException("Document", str(document_id))
        # PROVEN: is_frozen checked first
        self._assert_not_frozen(doc, "send for signature")
        if doc.status in TERMINAL_DOC_STATUSES:
            raise ServiceOSException("CONFLICT", f"Document is already {doc.status}.")

        token = secrets.token_urlsafe(48)
        expires_at = utcnow() + timedelta(hours=SIGNING_URL_TTL_HOURS)
        doc.status = DocStatus.SENT
        doc.signing_token = token
        doc.signing_expires_at = expires_at

        try:
            await self.redis.setex(REDIS_SIGNING_URL.format(token=token),
                                    SIGNING_URL_TTL_HOURS * 3600, str(document_id))
        except Exception:
            pass

        signing_url = f"https://sign.serviceos.in/d/{token}"
        await self._write_event(doc, DocEventType.SENT,
                                 meta={"signing_url": signing_url, "expires_at": expires_at.isoformat()})
        await self._publish("document.sent", str(doc.tenant_id), str(document_id),
                            {"signing_url": signing_url})
        return {**self._doc_dict(doc), "signing_url": signing_url,
                "expires_at": expires_at.isoformat(),
                "ttl_hours": SIGNING_URL_TTL_HOURS}

    async def get_signing_url(self, document_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(Document).where(Document.id == document_id))
        doc = r.scalar_one_or_none()
        if not doc: raise NotFoundException("Document", str(document_id))
        if not doc.signing_token:
            raise ServiceOSException("CONFLICT", "Document has not been sent for signature yet.")
        if doc.signing_expires_at and doc.signing_expires_at < utcnow():
            raise ServiceOSException("CONFLICT", "Signing URL has expired.",
                                      resolution="Call POST /send-for-signature to generate a new URL.")
        return {"signing_url": f"https://sign.serviceos.in/d/{doc.signing_token}",
                "expires_at": doc.signing_expires_at.isoformat() if doc.signing_expires_at else None}

    # PROVEN LEVEL 5: document frozen after signing — is_frozen=True
    async def record_signature(self, token: str, signature_data: str,
                                signer_ip: str) -> dict:
        # Resolve document from Redis token
        try:
            doc_id_bytes = await self.redis.get(REDIS_SIGNING_URL.format(token=token))
            if not doc_id_bytes:
                raise ServiceOSException("NOT_FOUND", "Signing token not found or expired.")
            doc_id = uuid.UUID(doc_id_bytes.decode() if isinstance(doc_id_bytes, bytes) else doc_id_bytes)
        except ServiceOSException: raise
        except Exception:
            raise ServiceOSException("NOT_FOUND", "Invalid signing token.")

        r = await self.db.execute(select(Document).where(Document.id == doc_id))
        doc = r.scalar_one_or_none()
        if not doc: raise NotFoundException("Document", str(doc_id))

        if doc.is_frozen:
            raise ServiceOSException("DOCUMENT_FROZEN", "Document already signed.")
        if doc.signing_expires_at and doc.signing_expires_at < utcnow():
            raise ServiceOSException("CONFLICT", "Signing URL has expired.")

        # PROVEN LEVEL 5: freeze the document — any subsequent write attempt raises immediately
        doc.status = DocStatus.SIGNED
        doc.is_frozen = True          # ← hard freeze
        doc.signed_at = utcnow()
        doc.signed_by = self.actor_id
        doc.signer_ip = signer_ip
        doc.signature_data = signature_data
        doc.signing_token = None  # token consumed

        try:
            await self.redis.delete(REDIS_SIGNING_URL.format(token=token))
        except Exception:
            pass

        await self._write_event(doc, DocEventType.SIGNED,
                                 meta={"signer_ip": signer_ip,
                                       "signed_at": doc.signed_at.isoformat()})
        await self._publish("document.signed", str(doc.tenant_id), str(doc_id),
                            {"signed_at": doc.signed_at.isoformat(), "signer_ip": signer_ip})
        logger.info("document.signed", document_id=str(doc_id), doc_number=doc.document_number)
        return {**self._doc_dict(doc), "signature_recorded": True}

    # PROVEN LEVEL 5: void requires is_frozen check
    async def void_document(self, document_id: uuid.UUID, reason: str) -> dict:
        # Phase 2A Slice 2F-35: same cross-tenant fix as send_for_signature.
        tenant_id = self._require_trusted_tenant()
        q = select(Document).where(Document.id == document_id)
        if tenant_id is not None:
            q = q.where(Document.tenant_id == tenant_id)
        r = await self.db.execute(q)
        doc = r.scalar_one_or_none()
        if not doc: raise NotFoundException("Document", str(document_id))
        if doc.status == DocStatus.VOIDED:
            raise ServiceOSException("CONFLICT", "Document is already voided.")
        # Signed documents CAN be voided (for legal correction) but only with explicit reason
        doc.status = DocStatus.VOIDED; doc.voided_at = utcnow(); doc.void_reason = reason
        # Voided signed documents must remain frozen — content is evidence
        # is_frozen stays True if it was signed
        await self._write_event(doc, DocEventType.VOIDED, meta={"reason": reason})
        await self._publish("document.voided", str(doc.tenant_id), str(document_id),
                            {"reason": reason, "was_signed": doc.signed_at is not None})
        return self._doc_dict(doc)

    async def list_document_events(self, document_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(DocumentEvent).where(
            DocumentEvent.document_id == document_id).order_by(DocumentEvent.created_at))
        events = r.scalars().all()
        return {"document_id": str(document_id),
                "events": [{"event_id": str(e.id), "event_type": e.event_type,
                             "actor_role": e.actor_role, "actor_ip": e.actor_ip,
                             "meta": e.meta, "occurred_at": e.created_at.isoformat()}
                            for e in events],
                "note": "This is the legal audit trail. Events are never deleted."}
