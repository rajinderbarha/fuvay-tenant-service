"""Inventory Document Extraction Engine — unit tests.

Covers: engine-disabled gate, malformed PDF handling, and the success path
(mocked DeepSeek response, per the established mocked-AsyncSession pattern
used across this test suite -- see test_final_l5_05j_usage_credit_service.py).
Does not require a live DB or a live DeepSeek API key.
"""
from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.engine_registry.registry import registry
from app.engines.inventory.constants import ItemStatus, ERR_PDF_UNREADABLE
from app.engines.inventory.extraction_service import InventoryExtractionService
from app.exceptions import EngineDisabledException, ServiceOSException


def _scalar_result(value):
    r = MagicMock()
    r.scalar_one_or_none = MagicMock(return_value=value)
    return r


class TestEngineRegistration:
    def test_engine_is_registered_as_plugin_disabled_by_default(self):
        engine = registry.get("inventory_document_extraction")
        assert engine is not None
        assert engine.engine_type == "plugin"
        assert engine.is_enabled_by_default is False
        assert "inventory" in engine.dependencies


class TestEngineDisabledGate:
    @pytest.mark.asyncio
    async def test_extract_from_pdf_raises_when_engine_disabled_for_tenant(self):
        tenant_id = uuid.uuid4()
        db = AsyncMock()
        # TenantEngine lookup returns None -> not enabled
        db.execute = AsyncMock(return_value=_scalar_result(None))
        svc = InventoryExtractionService(db=db, actor_role="tenant_owner", actor_tenant_id=tenant_id)

        with pytest.raises(EngineDisabledException):
            await svc.extract_from_pdf(tenant_id, "pricelist.pdf", b"%PDF-1.4 fake")


class TestMalformedPdf:
    @pytest.mark.asyncio
    async def test_extract_from_pdf_raises_clear_error_on_unreadable_file(self):
        tenant_id = uuid.uuid4()
        enabled_engine_row = MagicMock(is_enabled=True)
        db = AsyncMock()
        db.execute = AsyncMock(return_value=_scalar_result(enabled_engine_row))
        db.add = MagicMock()
        db.flush = AsyncMock()
        svc = InventoryExtractionService(db=db, actor_role="tenant_owner", actor_tenant_id=tenant_id)

        with pytest.raises(ServiceOSException) as exc_info:
            await svc.extract_from_pdf(tenant_id, "not-a-pdf.pdf", b"this is not a real pdf at all")
        assert exc_info.value.error_code == ERR_PDF_UNREADABLE


class TestSuccessfulExtraction:
    @pytest.mark.asyncio
    async def test_extract_from_pdf_creates_draft_items_from_llm_response(self):
        tenant_id = uuid.uuid4()
        enabled_engine_row = MagicMock(is_enabled=True)

        call_count = [0]

        async def mock_execute(q):
            call_count[0] += 1
            if call_count[0] == 1:
                return _scalar_result(enabled_engine_row)   # engine-enabled check
            if call_count[0] == 2:
                return _scalar_result(None)                 # no existing upload (idempotency)
            return _scalar_result(None)

        db = AsyncMock()
        db.execute = mock_execute
        db.add = MagicMock()
        db.flush = AsyncMock()

        svc = InventoryExtractionService(db=db, actor_role="tenant_owner", actor_tenant_id=tenant_id)

        fake_llm_json = json.dumps({"items": [
            {"name": "Copper Pipe 1/2 inch", "sku": "CP-12", "quantity": 50,
             "unit": "pcs", "unit_cost": 45.5, "category": "plumbing"},
            {"name": "PVC Elbow Joint", "sku": None, "quantity": 100,
             "unit": "pcs", "unit_cost": 8, "category": "plumbing"},
        ]})
        fake_response = {"choices": [{"message": {"content": fake_llm_json}}]}

        with patch.object(svc, "_extract_pdf_text", return_value="Copper Pipe... PVC Elbow..."), \
             patch("app.engines.inventory.extraction_service.DeepSeekClientService") as MockClient:
            MockClient.return_value.chat = AsyncMock(return_value=fake_response)
            result = await svc.extract_from_pdf(tenant_id, "pricelist.pdf", b"%PDF-1.4 fake-but-nonempty")

        assert result["extracted_item_count"] == 2
        assert len(result["draft_items"]) == 2
        assert all(i["status"] == ItemStatus.DRAFT for i in result["draft_items"])
        names = {i["name"] for i in result["draft_items"]}
        assert names == {"Copper Pipe 1/2 inch", "PVC Elbow Joint"}


class TestPublishGuard:
    @pytest.mark.asyncio
    async def test_publish_item_rejects_already_published_item(self):
        tenant_id = uuid.uuid4()
        item = MagicMock(tenant_id=tenant_id, status=ItemStatus.PUBLISHED)
        enabled_engine_row = MagicMock(is_enabled=True)

        call_count = [0]

        async def mock_execute(q):
            call_count[0] += 1
            if call_count[0] == 1:
                return _scalar_result(item)
            return _scalar_result(enabled_engine_row)

        db = AsyncMock()
        db.execute = mock_execute
        svc = InventoryExtractionService(db=db, actor_role="tenant_owner", actor_tenant_id=tenant_id)

        with pytest.raises(ServiceOSException):
            await svc.publish_item(uuid.uuid4())
