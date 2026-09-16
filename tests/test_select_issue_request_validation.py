"""A malformed select-issue body must be a 422, never a 500.

`POST /v1/customer/home-services/assistant-bootstrap/select-issue` used to read
an unvalidated `await r.json()` and index it directly (`body["category_slug"]`,
`body["issue_id"]`). A request missing either field raised KeyError, which the
generic handler turned into **500 INTERNAL_ERROR** -- "An unexpected error
occurred. Our team has been notified." Reproduced against staging on
2026-09-16 by posting `issue_ids` (plural) instead of `issue_id`: a plain
client mistake reported as a server fault, and alerting noise for something no
server-side fix can prevent. A malformed `ai_session_id` or `master_service_id`
took the same route through `uuid.UUID(...)`'s ValueError.
"""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.dependencies.auth import get_current_user, UserContext

ENDPOINT = "/v1/customer/home-services/assistant-bootstrap/select-issue"


def _customer_ctx() -> UserContext:
    return UserContext(
        user_id=str(uuid.uuid4()), email="customer@serviceos.local", role="customer",
        tenant_id=None, full_name="Demo Customer", is_verified=True,
    )


async def _post(body: dict):
    app.dependency_overrides[get_current_user] = lambda: _customer_ctx()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            return await client.post(ENDPOINT, headers={"Authorization": "Bearer x"}, json=body)
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_missing_issue_id_is_a_validation_error_not_a_server_error():
    # The exact shape that produced the 500: plural `issue_ids`, no `issue_id`.
    res = await _post({
        "category_slug": "home_services", "zipcode": "140412",
        "issue_ids": [str(uuid.uuid4())], "service_group_slug": "ac-hvac",
    })
    assert res.status_code == 422, res.text
    assert res.json()["error_code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_missing_category_slug_is_a_validation_error():
    res = await _post({"issue_id": str(uuid.uuid4()), "zipcode": "140412"})
    assert res.status_code == 422, res.text


@pytest.mark.asyncio
async def test_a_malformed_uuid_field_is_a_validation_error_not_a_server_error():
    res = await _post({
        "category_slug": "home_services", "issue_id": str(uuid.uuid4()),
        "ai_session_id": "not-a-uuid",
    })
    assert res.status_code == 422, res.text


@pytest.mark.asyncio
async def test_an_empty_body_is_a_validation_error():
    res = await _post({})
    assert res.status_code == 422, res.text


@pytest.mark.asyncio
async def test_unknown_extra_fields_are_still_ignored_not_rejected():
    """Other callers post supersets of this body, so extra keys must not 422.

    Note the endpoint answers BOTH request-validation failures and ordinary
    business rejections with 422, so the status alone proves nothing here --
    the discriminator is `error_code`. A well-formed body must get past
    validation and be rejected on catalog grounds instead.
    """
    res = await _post({
        "category_slug": "home_services", "issue_id": str(uuid.uuid4()),
        "zipcode": "140412", "some_future_field": "ignored",
    })
    assert res.json()["error_code"] != "VALIDATION_ERROR", res.text
