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


class TestDuplicateSkuInBatch:
    @pytest.mark.asyncio
    async def test_duplicate_skus_in_one_document_are_deduplicated_not_left_to_crash_db(self):
        """Real bug found live: a real multi-item equipment-list PDF
        produced two extracted rows with the same SKU (LLM omitted SKU for
        both, or the document genuinely repeats one) -- inventory_items has
        a real UNIQUE(tenant_id, sku) constraint, so inserting the second
        one crashed the whole request. Must de-duplicate within the batch
        before insert rather than let the DB reject it."""
        tenant_id = uuid.uuid4()
        enabled_engine_row = MagicMock(is_enabled=True)

        call_count = [0]

        async def mock_execute(q):
            call_count[0] += 1
            if call_count[0] == 1:
                return _scalar_result(enabled_engine_row)
            if call_count[0] == 2:
                return _scalar_result(None)
            return _scalar_result(None)

        db = AsyncMock()
        db.execute = mock_execute
        db.add = MagicMock()
        db.flush = AsyncMock()

        svc = InventoryExtractionService(db=db, actor_role="tenant_owner", actor_tenant_id=tenant_id)

        # Two items sharing the identical real SKU, exactly the real-world
        # shape that crashed live.
        fake_llm_json = json.dumps({"items": [
            {"name": "Craftsman tool set A", "sku": "SAME-SKU-1", "quantity": 1, "unit": "set", "unit_cost": 10},
            {"name": "Craftsman tool set B", "sku": "SAME-SKU-1", "quantity": 1, "unit": "set", "unit_cost": 12},
        ]})
        fake_response = {"choices": [{"message": {"content": fake_llm_json}}]}

        with patch.object(svc, "_extract_pdf_text", return_value="two tool sets, same sku..."), \
             patch("app.engines.inventory.extraction_service.DeepSeekClientService") as MockClient:
            MockClient.return_value.chat = AsyncMock(return_value=fake_response)
            result = await svc.extract_from_pdf(tenant_id, "equipment-list.pdf", b"%PDF-1.4 fake-but-nonempty")

        assert result["extracted_item_count"] == 2
        skus = [i["sku"] for i in result["draft_items"]]
        assert len(skus) == len(set(skus)), f"duplicate SKUs would violate the real DB constraint: {skus}"
        assert skus[0] == "SAME-SKU-1"
        assert skus[1] != "SAME-SKU-1"  # de-duplicated, not identical


class TestSessionRecoveryOnDbError:
    @pytest.mark.asyncio
    async def test_db_error_during_insert_rolls_back_before_recording_failure(self):
        """Real bug found live: when self.db.flush() raised a real DB error
        (e.g. a constraint violation) after items were added, the except
        block tried to flush() AGAIN on the now-failed session to record
        upload.status="failed" -- that second flush() itself raised an
        unrelated exception (real DB sessions refuse further queries after
        an error until rolled back), which was never caught, surfacing to
        the client as a raw, unexplained 500. Must roll back before any
        further DB use, and must always surface a clean ServiceOSException
        to the caller even if recording the failure also fails."""
        tenant_id = uuid.uuid4()
        enabled_engine_row = MagicMock(is_enabled=True)
        existing_upload = MagicMock(id=uuid.uuid4())

        call_count = [0]

        async def mock_execute(q):
            call_count[0] += 1
            if call_count[0] == 1:
                return _scalar_result(enabled_engine_row)
            if call_count[0] == 2:
                return _scalar_result(None)          # no existing upload
            # the post-rollback re-fetch of the upload row
            return _scalar_result(existing_upload)

        flush_calls = [0]
        async def mock_flush():
            flush_calls[0] += 1
            if flush_calls[0] == 1:
                # First flush (creating the upload row) succeeds.
                return
            if flush_calls[0] == 2:
                # Second flush (inserting extracted items) hits the real
                # UNIQUE(tenant_id, sku) constraint.
                raise Exception("duplicate key value violates unique constraint \"uq_ii_tenant_sku\"")
            # Third flush (recording failure, post-rollback) succeeds.
            return

        db = AsyncMock()
        db.execute = mock_execute
        db.add = MagicMock()
        db.flush = mock_flush
        db.rollback = AsyncMock()

        svc = InventoryExtractionService(db=db, actor_role="tenant_owner", actor_tenant_id=tenant_id)

        fake_llm_json = json.dumps({"items": [
            {"name": "Item A", "sku": "SKU-A", "quantity": 1, "unit": "pcs", "unit_cost": 5},
        ]})
        fake_response = {"choices": [{"message": {"content": fake_llm_json}}]}

        with patch.object(svc, "_extract_pdf_text", return_value="Item A..."), \
             patch("app.engines.inventory.extraction_service.DeepSeekClientService") as MockClient:
            MockClient.return_value.chat = AsyncMock(return_value=fake_response)
            with pytest.raises(ServiceOSException) as exc_info:
                await svc.extract_from_pdf(tenant_id, "equipment-list.pdf", b"%PDF-1.4 fake-but-nonempty")

        # The real fix: rollback happened, and the caller got a clean,
        # honest ServiceOSException -- not the raw secondary exception.
        assert db.rollback.await_count == 1
        assert "unexpectedly" in exc_info.value.detail.lower()


class TestCrossUploadSkuCollision:
    @pytest.mark.asyncio
    async def test_sku_matching_a_soft_deleted_item_from_a_prior_upload_is_deduplicated(self):
        """Real live bug (reproduced against the running backend with the
        user's actual home-inventory PDF): uq_ii_tenant_sku is a PLAIN
        unique constraint, NOT scoped to is_active. A soft-deleted item
        from an earlier upload permanently reserves its SKU. Re-uploading
        any document that extracts that same SKU (e.g. "CMT12367") must
        not crash -- the new item should get a de-duplicated SKU instead,
        the same as an in-batch collision."""
        tenant_id = uuid.uuid4()
        enabled_engine_row = MagicMock(is_enabled=True)

        existing_sku_rows = MagicMock()
        existing_sku_rows.__iter__ = MagicMock(return_value=iter([("CMT12367",)]))

        call_count = [0]

        async def mock_execute(q):
            call_count[0] += 1
            if call_count[0] == 1:
                return _scalar_result(enabled_engine_row)
            if call_count[0] == 2:
                return _scalar_result(None)          # no existing upload
            if call_count[0] == 3:
                return existing_sku_rows              # pre-existing tenant SKUs
            return _scalar_result(None)

        db = AsyncMock()
        db.execute = mock_execute
        db.add = MagicMock()
        db.flush = AsyncMock()

        svc = InventoryExtractionService(db=db, actor_role="tenant_owner", actor_tenant_id=tenant_id)

        fake_llm_json = json.dumps({"items": [
            {"name": "Craftsman tool set", "sku": "CMT12367", "quantity": 1, "unit": "set", "unit_cost": 400},
        ]})
        fake_response = {"choices": [{"message": {"content": fake_llm_json}}]}

        with patch.object(svc, "_extract_pdf_text", return_value="Craftsman tool set..."), \
             patch("app.engines.inventory.extraction_service.DeepSeekClientService") as MockClient:
            MockClient.return_value.chat = AsyncMock(return_value=fake_response)
            result = await svc.extract_from_pdf(tenant_id, "home-inventory.pdf", b"%PDF-1.4 fake-but-nonempty")

        assert result["extracted_item_count"] == 1
        assert result["draft_items"][0]["sku"] != "CMT12367"


class TestReUploadAfterDeletion:
    @pytest.mark.asyncio
    async def test_reupload_reprocesses_when_all_prior_items_deleted(self):
        """Real bug found live: uploading the same PDF after deleting every
        item it previously produced returned the stale idempotent response
        forever (the content_hash record survives deletion of its items).
        Re-processing must proceed for real once no surviving item remains."""
        tenant_id = uuid.uuid4()
        enabled_engine_row = MagicMock(is_enabled=True)
        existing_upload = MagicMock(id=uuid.uuid4(), status="completed", extracted_item_count=5)

        call_count = [0]

        async def mock_execute(q):
            call_count[0] += 1
            if call_count[0] == 1:
                return _scalar_result(enabled_engine_row)   # engine-enabled check
            if call_count[0] == 2:
                return _scalar_result(existing_upload)      # existing upload found (same hash)
            if call_count[0] == 3:
                r = MagicMock(); r.first = MagicMock(return_value=None)  # no surviving active items
                return r
            return _scalar_result(None)

        db = AsyncMock()
        db.execute = mock_execute
        db.add = MagicMock()
        db.flush = AsyncMock()

        svc = InventoryExtractionService(db=db, actor_role="tenant_owner", actor_tenant_id=tenant_id)

        fake_llm_json = json.dumps({"items": [
            {"name": "Test Widget A", "sku": "TWA-100", "quantity": 20,
             "unit": "pcs", "unit_cost": 50, "category": "electrical"},
        ]})
        fake_response = {"choices": [{"message": {"content": fake_llm_json}}]}

        with patch.object(svc, "_extract_pdf_text", return_value="Test Widget A..."), \
             patch("app.engines.inventory.extraction_service.DeepSeekClientService") as MockClient:
            MockClient.return_value.chat = AsyncMock(return_value=fake_response)
            result = await svc.extract_from_pdf(tenant_id, "pricelist.pdf", b"%PDF-1.4 same-file-bytes")

        # Must NOT be the stale idempotent short-circuit -- real re-extraction ran.
        assert result["idempotent"] is False
        assert result["extracted_item_count"] == 1
        assert result["upload_id"] == str(existing_upload.id)  # reused, not a new row
        assert existing_upload.status == "processing" or existing_upload.status == "completed"
