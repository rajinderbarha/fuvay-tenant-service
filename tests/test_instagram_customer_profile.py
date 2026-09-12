from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.engines.messaging_gateway import meta_client
from app.engines.messaging_gateway.service import MessagingGatewayService


@pytest.mark.asyncio
async def test_instagram_profile_lookup_returns_public_name_and_username(monkeypatch):
    class Response:
        status_code = 200
        text = '{"name":"Rajinder Barha","username":"@rajinderbarha"}'

    class Client:
        def __init__(self, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def get(self, url, *, headers, params):
            assert url.endswith("/v24.0/ig-scoped-123")
            assert headers["Authorization"] == "Bearer test-token"
            assert params == {"fields": "name,username"}
            return Response()

    monkeypatch.setattr(meta_client.httpx, "AsyncClient", Client)
    profile = await meta_client.fetch_instagram_profile(
        "ig-scoped-123", {"access_token": "test-token", "api_version": "v24.0"},
    )
    assert profile == {"name": "Rajinder Barha", "username": "rajinderbarha"}


@pytest.mark.asyncio
async def test_instagram_profile_is_persisted_on_thread_and_customer(monkeypatch):
    customer_id = uuid4()
    user = SimpleNamespace(
        id=customer_id,
        full_name="Instagram Customer",
        display_name=None,
        meta={"registration_source": "instagram_booking_dev"},
    )

    class DB:
        async def get(self, _model, row_id):
            assert row_id == customer_id
            return user

    async def profile(_sender_id, _config):
        return {"name": "Rajinder Barha", "username": "rajinderbarha"}

    monkeypatch.setattr(meta_client, "fetch_instagram_profile", profile)
    thread = SimpleNamespace(
        channel="instagram",
        channel_user_id="ig-scoped-123",
        display_name=None,
        channel_username=None,
        customer_id=customer_id,
    )
    service = MessagingGatewayService(DB(), channel_config={"access_token": "test"})
    await service._hydrate_instagram_profile(thread)

    assert thread.display_name == "Rajinder Barha"
    assert thread.channel_username == "rajinderbarha"
    assert user.full_name == "Rajinder Barha"
    assert user.display_name == "Rajinder Barha"
    assert user.meta["instagram_name"] == "Rajinder Barha"
    assert user.meta["instagram_username"] == "rajinderbarha"
