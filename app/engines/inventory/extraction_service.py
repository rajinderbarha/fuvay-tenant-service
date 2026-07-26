"""Inventory Document Extraction Engine — service layer.

Pipeline: PDF upload -> pypdf text extraction -> DeepSeek LLM structured
extraction -> draft InventoryItem rows -> provider review/edit -> publish.

Gated per-tenant by the `inventory_document_extraction` plugin engine
(app/engine_registry/registry.py). Reuses:
  - DeepSeekClientService (app/engines/ai_conversation/deepseek_client.py) —
    the same LLM client backing the customer-facing DeepSeek chat assistant.
    No new AI provider/API key is introduced.
  - pypdf for PDF text extraction (no existing text-extraction utility was
    found in the rag/document engines — both operate on already-extracted
    text; this is a genuinely new capability, added honestly, not faked).
"""
from __future__ import annotations

import hashlib
import json
import uuid
from decimal import Decimal, InvalidOperation

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine_registry.models import TenantEngine
from app.engines.ai_conversation.deepseek_client import DeepSeekClientService
from app.engines.inventory.constants import (
    DOCUMENT_EXTRACTION_ENGINE_ID, EXTRACTION_SYSTEM_PROMPT, ItemStatus,
    ERR_PDF_UNREADABLE, ERR_LLM_BAD_RESPONSE, ERR_NOT_DRAFT, MAX_UPLOAD_PDF_BYTES,
)
from app.engines.inventory.models import InventoryItem, InventoryExtractionUpload
from app.exceptions import ServiceOSException, NotFoundException, EngineDisabledException

logger = structlog.get_logger("inventory.extraction")


class InventoryExtractionService:
    def __init__(self, db: AsyncSession, request_id: str = "—",
                 actor_id: uuid.UUID | None = None, actor_role: str | None = None,
                 actor_tenant_id: uuid.UUID | None = None):
        self.db = db
        self.request_id = request_id
        self.actor_id = actor_id
        self.actor_role = actor_role
        self.actor_tenant_id = actor_tenant_id

    def _require_trusted_tenant(self, requested_tenant_id: uuid.UUID) -> uuid.UUID:
        if self.actor_role == "super_admin":
            return requested_tenant_id
        if self.actor_tenant_id is None:
            raise ServiceOSException("PERMISSION_DENIED", "No tenant context.",
                blocking_rule="inventory_extraction_requires_trusted_tenant_context")
        if requested_tenant_id != self.actor_tenant_id:
            raise ServiceOSException("PERMISSION_DENIED",
                "You do not have access to this tenant's inventory.",
                blocking_rule="inventory_extraction_cross_tenant_denied")
        return self.actor_tenant_id

    async def _assert_engine_enabled(self, tenant_id: uuid.UUID) -> None:
        if self.actor_role == "super_admin":
            return
        r = await self.db.execute(select(TenantEngine).where(
            TenantEngine.tenant_id == tenant_id,
            TenantEngine.engine_id == DOCUMENT_EXTRACTION_ENGINE_ID,
            TenantEngine.is_enabled == True))
        if not r.scalar_one_or_none():
            raise EngineDisabledException(DOCUMENT_EXTRACTION_ENGINE_ID, str(tenant_id))

    def _extract_pdf_text(self, pdf_bytes: bytes) -> str:
        try:
            import io
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(pdf_bytes))
            if reader.is_encrypted:
                try:
                    reader.decrypt("")
                except Exception:
                    raise ServiceOSException(ERR_PDF_UNREADABLE,
                        "This PDF is password-protected and cannot be read.",
                        resolution="Upload an unencrypted PDF.")
            text_parts = [page.extract_text() or "" for page in reader.pages]
            text = "\n".join(text_parts).strip()
            if not text:
                raise ServiceOSException(ERR_PDF_UNREADABLE,
                    "No extractable text found in this PDF (it may be a scanned image).",
                    resolution="Upload a text-based PDF, or a PDF produced from a spreadsheet/document.")
            return text
        except ServiceOSException:
            raise
        except Exception as e:
            raise ServiceOSException(ERR_PDF_UNREADABLE,
                f"Could not read this file as a PDF: {str(e)[:200]}",
                resolution="Confirm the file is a valid, non-corrupted PDF.")

    def _parse_llm_json(self, raw_content: str) -> list[dict]:
        content = raw_content.strip()
        # Defensive: strip markdown fences if the model added them anyway.
        if content.startswith("```"):
            content = content.strip("`")
            if content.lower().startswith("json"):
                content = content[4:]
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as e:
            raise ServiceOSException(ERR_LLM_BAD_RESPONSE,
                "The AI extraction returned a response that could not be parsed as JSON.",
                context={"parse_error": str(e)})
        items = parsed.get("items") if isinstance(parsed, dict) else None
        if not isinstance(items, list):
            raise ServiceOSException(ERR_LLM_BAD_RESPONSE,
                "The AI extraction response was missing the expected 'items' list.")
        return items

    def _coerce_decimal(self, value) -> Decimal | None:
        if value is None:
            return None
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError):
            return None

    async def extract_from_pdf(self, tenant_id: uuid.UUID, file_name: str,
                                pdf_bytes: bytes) -> dict:
        """Full pipeline. Never auto-publishes — always creates status='draft' rows."""
        tenant_id = self._require_trusted_tenant(tenant_id)
        await self._assert_engine_enabled(tenant_id)

        if len(pdf_bytes) > MAX_UPLOAD_PDF_BYTES:
            raise ServiceOSException("VALIDATION_ERROR",
                f"File exceeds the {MAX_UPLOAD_PDF_BYTES // (1024*1024)}MB upload limit.")

        content_hash = hashlib.sha256(pdf_bytes).hexdigest()

        # Idempotent on (tenant_id, content_hash) — mirrors KBDocument's pattern.
        # BUT idempotency only holds while at least one real item from that
        # upload still exists (draft or published, is_active). If the
        # provider deleted every item that came from this upload, the
        # content-hash record must not permanently block re-processing the
        # same file -- re-run extraction and reuse/reset the same upload row
        # (its content_hash is uniquely constrained, so we can't insert a
        # second row for the same tenant+hash).
        ex = await self.db.execute(select(InventoryExtractionUpload).where(
            InventoryExtractionUpload.tenant_id == tenant_id,
            InventoryExtractionUpload.content_hash == content_hash))
        existing = ex.scalar_one_or_none()
        if existing and existing.status == "completed":
            surviving = await self.db.execute(select(InventoryItem.id).where(
                InventoryItem.source_upload_id == existing.id,
                InventoryItem.is_active == True))  # noqa: E712
            if surviving.first() is not None:
                drafts = await self.db.execute(select(InventoryItem).where(
                    InventoryItem.source_upload_id == existing.id,
                    InventoryItem.status == ItemStatus.DRAFT,
                    InventoryItem.is_active == True))  # noqa: E712
                return {
                    "upload_id": str(existing.id), "idempotent": True,
                    "status": existing.status,
                    "extracted_item_count": existing.extracted_item_count,
                    "draft_items": [self._item_dict(i) for i in drafts.scalars().all()],
                }
            # All prior items from this exact upload were deleted -- reuse
            # the same upload row (reset it) and genuinely re-extract.
            upload = existing
            upload.status = "processing"
            upload.error_message = None
            upload.extracted_item_count = 0
            await self.db.flush()
        else:
            upload = InventoryExtractionUpload(tenant_id=tenant_id, file_name=file_name,
                content_hash=content_hash, status="processing", uploaded_by=self.actor_id)
            self.db.add(upload)
            await self.db.flush()

        try:
            # _extract_pdf_text is synchronous/CPU-bound (pypdf parses
            # every page in-process). Running it directly here would block
            # the single-threaded async event loop for the entire parse
            # duration -- for a large multi-page PDF (5MB+) that can be
            # long enough that the connection goes idle and the browser's
            # fetch gives up with a bare "Failed to fetch" (no clean HTTP
            # response ever gets a chance to be sent). Offload to a thread
            # so the event loop -- and this request's own connection --
            # stays responsive while parsing runs.
            import asyncio
            pdf_text = await asyncio.to_thread(self._extract_pdf_text, pdf_bytes)
            # Keep the prompt bounded — a very large PDF is truncated rather
            # than silently failing the LLM call.
            truncated = pdf_text[:24000]

            llm = DeepSeekClientService(db=self.db, request_id=self.request_id)
            response = await llm.chat(messages=[
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": truncated},
            ])
            raw_content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
            upload.raw_llm_response = raw_content[:20000]

            parsed_items = self._parse_llm_json(raw_content)

            created: list[InventoryItem] = []
            # inventory_items has a real UNIQUE(tenant_id, sku) constraint,
            # and it is NOT scoped to active rows -- a soft-deleted item
            # (is_active=False) still permanently reserves its SKU. A real
            # document can extract a SKU that collides either within this
            # batch, or with an existing (even soft-deleted) row from a
            # prior upload for this tenant. Pre-load every SKU this tenant
            # has ever used and de-duplicate against that set, rather than
            # letting the DB reject the insert (which would fail the whole
            # transaction, see the except block below for why that used to
            # become an unhandled second exception).
            existing_skus_result = await self.db.execute(
                select(InventoryItem.sku).where(InventoryItem.tenant_id == tenant_id)
            )
            seen_skus: set[str] = {row[0] for row in existing_skus_result if row[0]}
            for raw in parsed_items:
                name = (raw.get("name") or "").strip()
                if not name:
                    continue
                sku = raw.get("sku") or f"EXTRACT-{uuid.uuid4().hex[:8].upper()}"
                if sku in seen_skus:
                    sku = f"{sku}-{uuid.uuid4().hex[:4].upper()}"
                seen_skus.add(sku)
                item = InventoryItem(
                    tenant_id=tenant_id, name=name, sku=sku,
                    category=raw.get("category"), unit=raw.get("unit") or "unit",
                    unit_cost=self._coerce_decimal(raw.get("unit_cost")) or Decimal("0"),
                    min_quantity=int(raw["quantity"]) if isinstance(raw.get("quantity"), (int, float)) else 5,
                    status=ItemStatus.DRAFT, source_upload_id=upload.id,
                    meta={"extracted_quantity": raw.get("quantity")},
                    gst=self._coerce_decimal(raw.get("gst")),
                    warranty=(raw.get("warranty") or None),
                )
                self.db.add(item)
                created.append(item)

            upload.status = "completed"
            upload.extracted_item_count = len(created)
            await self.db.flush()

            logger.info("inventory_extraction.completed", upload_id=str(upload.id),
                        tenant_id=str(tenant_id), item_count=len(created))
            return {
                "upload_id": str(upload.id), "idempotent": False,
                "status": "completed", "extracted_item_count": len(created),
                "draft_items": [self._item_dict(i) for i in created],
            }
        except ServiceOSException as e:
            # A ServiceOSException here (e.g. from _parse_llm_json) is
            # raised before any DB write in this block, so the session is
            # still healthy -- safe to record the failure directly.
            upload.status = "failed"
            upload.error_message = e.detail[:1000]
            await self.db.flush()
            raise
        except Exception as e:
            # Real bug found live: a genuine DB error here (e.g. the
            # UNIQUE(tenant_id, sku) constraint, before the in-batch
            # de-dup above existed) leaves the async session in a failed-
            # transaction state. The old code then tried to flush() AGAIN
            # to record upload.status="failed" -- but you cannot issue any
            # further query on a session that already errored without
            # rolling back first, so that second flush() itself raised an
            # unrelated, uncaught exception, surfacing to the client as a
            # raw 500 with no clean error body. Roll back first, then
            # (best-effort, in its own try) record the failure on the
            # now-clean session; if even that fails, still return the
            # honest, clean error to the caller rather than leaking a
            # second exception.
            logger.error("inventory_extraction.failed", upload_id=str(upload.id), error=str(e))
            await self.db.rollback()
            try:
                fresh = await self.db.execute(select(InventoryExtractionUpload).where(
                    InventoryExtractionUpload.id == upload.id))
                fresh_upload = fresh.scalar_one_or_none()
                if fresh_upload:
                    fresh_upload.status = "failed"
                    fresh_upload.error_message = str(e)[:1000]
                    await self.db.flush()
            except Exception:
                pass
            raise ServiceOSException(ERR_LLM_BAD_RESPONSE,
                "Extraction failed unexpectedly.", context={"error": str(e)[:300]})

    def _item_dict(self, item: InventoryItem) -> dict:
        return {"item_id": str(item.id), "name": item.name, "sku": item.sku,
                "category": item.category, "unit": item.unit,
                "unit_cost": float(item.unit_cost), "min_quantity": item.min_quantity,
                "gst": float(item.gst) if item.gst is not None else None,
                "warranty": item.warranty,
                "status": item.status, "source_upload_id": str(item.source_upload_id) if item.source_upload_id else None}

    # ── Draft CRUD ─────────────────────────────────────────────────────
    async def list_drafts(self, tenant_id: uuid.UUID) -> dict:
        tenant_id = self._require_trusted_tenant(tenant_id)
        r = await self.db.execute(select(InventoryItem).where(
            InventoryItem.tenant_id == tenant_id, InventoryItem.status == ItemStatus.DRAFT
        ).order_by(InventoryItem.created_at.desc()))
        items = r.scalars().all()
        return {"items": [self._item_dict(i) for i in items], "total": len(items)}

    async def _get_owned_item(self, item_id: uuid.UUID) -> InventoryItem:
        r = await self.db.execute(select(InventoryItem).where(InventoryItem.id == item_id))
        item = r.scalar_one_or_none()
        if not item:
            raise NotFoundException("InventoryItem", str(item_id))
        self._require_trusted_tenant(item.tenant_id)
        return item

    async def update_draft(self, item_id: uuid.UUID, data: dict) -> dict:
        item = await self._get_owned_item(item_id)
        if item.status != ItemStatus.DRAFT:
            raise ServiceOSException(ERR_NOT_DRAFT,
                f"Item is '{item.status}', not 'draft'. Only draft items can be edited here.",
                resolution="Use the standard inventory update endpoint for published items.")
        for field in ("name", "sku", "category", "unit", "min_quantity", "warranty"):
            if field in data and data[field] is not None:
                setattr(item, field, data[field])
        if "unit_cost" in data and data["unit_cost"] is not None:
            item.unit_cost = self._coerce_decimal(data["unit_cost"]) or item.unit_cost
        if "gst" in data:
            item.gst = self._coerce_decimal(data["gst"]) if data["gst"] not in (None, "") else None
        await self.db.flush()
        return self._item_dict(item)

    async def delete_draft(self, item_id: uuid.UUID) -> dict:
        item = await self._get_owned_item(item_id)
        if item.status != ItemStatus.DRAFT:
            raise ServiceOSException(ERR_NOT_DRAFT,
                f"Item is '{item.status}', not 'draft'. Publish or delete only applies to drafts here.")
        await self.db.delete(item)
        return {"item_id": str(item_id), "deleted": True}

    async def publish_item(self, item_id: uuid.UUID) -> dict:
        item = await self._get_owned_item(item_id)
        await self._assert_engine_enabled(item.tenant_id)
        if item.status != ItemStatus.DRAFT:
            raise ServiceOSException(ERR_NOT_DRAFT,
                f"Item is already '{item.status}'.", resolution="Only draft items can be published.")
        item.status = ItemStatus.PUBLISHED
        await self.db.flush()
        return self._item_dict(item)

    async def publish_many(self, item_ids: list[uuid.UUID]) -> dict:
        results = []
        for item_id in item_ids:
            try:
                results.append({"item_id": str(item_id), **await self.publish_item(item_id)})
            except ServiceOSException as e:
                results.append({"item_id": str(item_id), "error": e.detail})
        published = sum(1 for r in results if "error" not in r)
        return {"results": results, "published": published, "total": len(item_ids)}
