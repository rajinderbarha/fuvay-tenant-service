"""Warranty PDF storage and delivery; no real database or messages."""
import uuid
from contextlib import asynccontextmanager
from io import BytesIO
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock

import pytest
from pypdf import PdfReader

from app.engines.messaging_gateway import warranty_delivery as delivery


class DB:
    def __init__(self):
        self.flush = AsyncMock()
        self.rolled_back = False

    @asynccontextmanager
    async def begin_nested(self):
        try:
            yield
        except Exception:
            self.rolled_back = True
            raise


@pytest.fixture
def case(monkeypatch):
    customer_id = uuid.uuid4()
    snapshot = {
        "certificate_number": "WRN-JOB-7", "warranty_days": 5,
        "warranty_expires_at": "2026-09-16T10:30:00+00:00",
        "issued_at": "2026-09-11T10:30:00+00:00",
        "job_number": "JOB-7", "booking_number": "BK-7",
        "service_name": "AC Repair", "customer_name": "Customer",
        "provider": {"name": "Service Provider"}, "terms": [],
    }
    job = NS(id=uuid.uuid4(), customer_id=customer_id, status="completed",
             warranty_certificate_snapshot=snapshot,
             warranty_certificate_number="WRN-JOB-7",
             completion_data={"work_summary": "Fixed AC"})
    thread = NS(id=uuid.uuid4(), customer_id=customer_id, channel="instagram",
                channel_user_id="igsid-7", last_options=["rt|booking|5"],
                last_outbound_at=None)
    stored = NS(public_url="https://files.example.test/warranty/random.pdf",
                storage_driver="cloudinary", storage_key="warranty/random.pdf",
                storage_bucket="documents")
    storage = NS(store_file=AsyncMock(return_value=stored))
    monkeypatch.setattr(delivery, "MediaStorageService", lambda **kw: storage)
    send = AsyncMock(return_value={"sent": True})
    monkeypatch.setattr(delivery.meta_client, "send_document", send)
    return NS(db=DB(), job=job, thread=thread, stored=stored, storage=storage,
              send=send, config={"access_token": "test-token"})


async def deliver(case):
    return await delivery.send_warranty_certificate(
        case.db, case.job, case.thread, config=case.config,
    )


async def test_stores_real_five_day_pdf_and_sends_to_the_rating_recipient_once(case):
    assert await deliver(case) is True
    upload = case.storage.store_file.await_args.kwargs
    assert upload["mime_type"] == "application/pdf"
    assert upload["original_filename"].endswith(".pdf")
    assert upload["owner_id"] == str(case.job.customer_id)
    pdf = PdfReader(BytesIO(upload["file_bytes"]))
    text = " ".join(page.extract_text() for page in pdf.pages)
    assert "warranty of 5 days" in text
    assert "BK-7" in text and "Service Provider" in text
    case.send.assert_awaited_once_with(
        "igsid-7", case.stored.public_url, channel="instagram", config=case.config,
    )
    assert case.job.completion_data["work_summary"] == "Fixed AC"
    assert case.job.completion_data[delivery.DELIVERY_KEY]["sent_at"]
    assert case.thread.last_options == ["rt|booking|5"]
    assert await deliver(case) is True
    case.storage.store_file.assert_awaited_once()
    case.send.assert_awaited_once()


async def test_failed_send_is_not_marked_sent_and_retry_reuses_pdf(case):
    case.send.return_value = {"sent": False, "reason": "transport_error"}
    assert await deliver(case) is False
    assert "sent_at" not in case.job.completion_data[delivery.DELIVERY_KEY]
    assert case.thread.last_outbound_at is None
    case.send.return_value = {"sent": True}
    assert await deliver(case) is True
    case.storage.store_file.assert_awaited_once()
    assert case.send.await_count == 2


async def test_storage_failure_is_isolated_in_a_savepoint(case):
    case.storage.store_file.side_effect = RuntimeError("storage unavailable")
    assert await deliver(case) is False
    assert case.db.rolled_back is True
    case.send.assert_not_awaited()
    assert case.thread.last_options == ["rt|booking|5"]


@pytest.mark.parametrize("url", [None, "/uploads/warranty.pdf", "http://localhost/file.pdf",
                                  "https:///file.pdf", "https://name:secret@files.test/file.pdf"])
async def test_never_messages_an_unusable_document_url(case, url):
    case.stored.public_url = url
    assert await deliver(case) is False
    case.send.assert_not_awaited()
    assert delivery.DELIVERY_KEY not in case.job.completion_data


@pytest.mark.parametrize("change", ["wrong_customer", "not_completed", "wrong_channel", "no_snapshot"])
async def test_only_sends_the_completed_customers_instagram_certificate(case, change):
    if change == "wrong_customer":
        case.thread.customer_id = uuid.uuid4()
    elif change == "not_completed":
        case.job.status = "work_done"
    elif change == "wrong_channel":
        case.thread.channel = "whatsapp"
    else:
        case.job.warranty_certificate_snapshot = None
    assert await deliver(case) is False
    case.storage.store_file.assert_not_awaited()
    case.send.assert_not_awaited()
