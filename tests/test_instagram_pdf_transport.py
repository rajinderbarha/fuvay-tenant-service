"""Instagram PDF payload and error handling, with every HTTP request isolated."""
import json
from types import SimpleNamespace as NS

import httpx
import pytest

from app.engines.messaging_gateway import meta_client
from app.engines.messaging_gateway.constants import CHANNEL_INSTAGRAM, CHANNEL_WHATSAPP


IG = {"access_token": "test-ig-token", "instagram_account_id": "17890001",
      "api_version": "v26.0"}
PDF_URL = "https://files.example.test/warranty/BK-1042.pdf?signature=abc%2B123"


@pytest.fixture
def transport(monkeypatch):
    state = NS(calls=[], replies=[(200, {"message_id": "pdf-1"})], exception=None)

    class Client:
        def __init__(self, **kwargs):
            assert kwargs["timeout"] == 15.0

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, **kwargs):
            state.calls.append(NS(url=url, **kwargs))
            if state.exception:
                raise state.exception
            status, response = state.replies.pop(0)
            return NS(status_code=status, text=json.dumps(response))

    monkeypatch.setattr(meta_client.httpx, "AsyncClient", Client)
    monkeypatch.setattr(meta_client, "_cfg", lambda *args: "")
    return state


@pytest.mark.asyncio
async def test_pdf_is_a_native_instagram_file_attachment(transport):
    result = await meta_client.send_document("igsid-1", PDF_URL, config=IG)

    [request] = transport.calls
    assert request.url == "https://graph.instagram.com/v26.0/17890001/messages"
    assert request.headers == {"Authorization": "Bearer test-ig-token"}
    assert request.json == {
        "recipient": {"id": "igsid-1"},
        "message": {"attachment": {"type": "file", "payload": {"url": PDF_URL}}},
    }
    assert result == {"sent": True, "status": 200,
                      "response": {"message_id": "pdf-1"}, "delivery_mode": "attachment"}


@pytest.mark.asyncio
@pytest.mark.parametrize("url", [
    "", None, "http://files.example.test/warranty.pdf", "file:///C:/warranty.pdf",
    "javascript:alert(1)", "https:///missing-host.pdf", "https://[malformed/pdf",
    "https://files.example.test:wrong/warranty.pdf",
    "https://user:password@files.example.test/warranty.pdf",
    "https://files.example.test/warranty.pdf#secret",
    "https://files.example.test/war\nranty.pdf",
    "https://files.example.test/war ranty.pdf",
    "https://files.example.test\\warranty.pdf",
])
async def test_invalid_document_urls_never_leave_the_application(transport, url):
    assert await meta_client.send_document("igsid-1", url, config=IG) == {
        "sent": False, "reason": "invalid_document_url",
    }
    assert transport.calls == []


@pytest.mark.asyncio
async def test_missing_config_and_other_channels_send_nothing(transport):
    assert await meta_client.send_document("igsid-1", PDF_URL, config={}) == {
        "sent": False, "reason": "channel_not_configured",
    }
    assert await meta_client.send_document(
        "igsid-1", PDF_URL, channel=CHANNEL_WHATSAPP, config=IG,
    ) == {"sent": False, "reason": "unsupported_document_channel"}
    assert transport.calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize("message", [
    "Unsupported attachment type", "Attachment type file is not supported",
    "Unsupported file type", "Invalid message data", "Upload attachment failure",
    "Attachment URL could not be fetched",
])
async def test_explicit_unsupported_file_response_falls_back_to_the_pdf_link(transport, message):
    transport.replies = [
        (400, {"error": {"code": 100, "message": message}}),
        (200, {"message_id": "link-1"}),
    ]
    result = await meta_client.send_document(
        "igsid-1", PDF_URL, channel=CHANNEL_INSTAGRAM, config=IG,
    )
    assert len(transport.calls) == 2
    assert transport.calls[1].json == {
        "recipient": {"id": "igsid-1"}, "message": {"text": f"Download your PDF:\n{PDF_URL}"},
    }
    assert result["sent"] is True and result["delivery_mode"] == "download_link"
    assert result["response"]["message_id"] == "link-1"


@pytest.mark.asyncio
@pytest.mark.parametrize("status, response", [
    (401, {"error": {"code": 190, "message": "Access token expired"}}),
    (400, {"error": {"code": 10, "message": "Outside allowed messaging window"}}),
    (400, {"error": {"code": 100, "message": "Invalid recipient"}}),
    (400, {"error": {"code": 190, "message": "Unsupported attachment type"}}),
    (429, {"error": {"code": 100, "message": "Unsupported attachment type"}}),
    (500, "Internal server error"),
    (400, {"error": "Unexpected error"}),
])
async def test_unrelated_failures_do_not_send_a_second_message(transport, status, response):
    transport.replies = [(status, response)]
    result = await meta_client.send_document("igsid-1", PDF_URL, config=IG)
    assert result["sent"] is False
    assert len(transport.calls) == 1


@pytest.mark.asyncio
async def test_timeout_is_reported_without_retrying_an_ambiguous_send(transport):
    transport.exception = httpx.ReadTimeout("Meta did not respond")
    result = await meta_client.send_document("igsid-1", PDF_URL, config=IG)
    assert result == {"sent": False, "reason": "transport_error"}
    assert len(transport.calls) == 1


@pytest.mark.asyncio
async def test_link_fallback_failure_is_returned(transport):
    transport.replies = [
        (400, {"error": {"code": 100, "message": "Unsupported attachment type"}}),
        (401, {"error": {"code": 190, "message": "Token expired"}}),
    ]
    result = await meta_client.send_document("igsid-1", PDF_URL, config=IG)
    assert result["sent"] is False and result["status"] == 401
    assert result["delivery_mode"] == "download_link"
    assert len(transport.calls) == 2


@pytest.mark.asyncio
async def test_long_signed_link_is_never_split_or_truncated(transport):
    transport.replies = [
        (400, {"error": {"code": 100, "message": "Unsupported attachment type"}}),
    ]
    result = await meta_client.send_document("igsid-1", PDF_URL + "a" * 1000, config=IG)
    assert result["sent"] is False
    assert len(transport.calls) == 1
