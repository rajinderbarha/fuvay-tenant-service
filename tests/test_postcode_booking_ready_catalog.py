import uuid

import pytest


class _ScalarResult:
    def scalar_one_or_none(self):
        return None


class _DB:
    def __init__(self):
        self.info = {}

    async def execute(self, _statement):
        return _ScalarResult()

    def begin_nested(self):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False


@pytest.mark.asyncio
async def test_postcode_catalog_uses_production_matcher_and_caches_result(monkeypatch):
    from app.engines.home_service_booking import matching_engine
    from app.engines.home_service_booking import offering_catalog_service as catalog

    category_id = uuid.uuid4()
    ready_service = uuid.uuid4()
    unavailable_service = uuid.uuid4()
    ready_job = uuid.uuid4()
    unavailable_job = uuid.uuid4()

    async def pairs(_db, _zipcode):
        return [
            (category_id, ready_service, ready_job),
            (category_id, ready_service, unavailable_job),
            (category_id, unavailable_service, ready_job),
        ]

    calls = []

    async def match(_db, **kwargs):
        calls.append(kwargs)
        if (
            kwargs["offering_id"] == ready_service
            and kwargs["job_type_id"] == ready_job
        ):
            return {
                "signals": object(),
                "score": 91,
                "earliest_slot": {
                    "starts_at": "2026-09-20T10:00:00",
                    "date": "2026-09-20",
                    "time_window": "10:00-11:00",
                },
            }
        return {"signals": None, "score": None, "earliest_slot": None}

    monkeypatch.setattr(catalog, "_booking_candidate_pairs", pairs)
    monkeypatch.setattr(matching_engine, "select_best_provider", match)

    db = _DB()
    first = await catalog.booking_ready_service_matches(db, "140412")
    second = await catalog.booking_ready_service_matches(db, "140412")

    assert set(first) == {ready_service}
    assert first[ready_service]["job_type_ids"] == {ready_job}
    assert first[ready_service]["earliest_slot"]["time_window"] == "10:00-11:00"
    assert second is first
    assert len(calls) == 3
    assert all(call["zipcode"] == "140412" for call in calls)


@pytest.mark.asyncio
async def test_exact_type_priced_service_is_ready_when_a_real_type_can_match(monkeypatch):
    from app.engines.home_service_booking import matching_engine
    from app.engines.home_service_booking import offering_catalog_service as catalog

    category_id = uuid.uuid4()
    service_id = uuid.uuid4()
    job_type_id = uuid.uuid4()
    tap_type_id = uuid.uuid4()
    basin_type_id = uuid.uuid4()

    async def pairs(_db, _zipcode):
        return [(category_id, service_id, job_type_id)]

    async def priceable_types(_db, _service_id, _job_type_id):
        assert _service_id == service_id
        assert _job_type_id == job_type_id
        return [tap_type_id, basin_type_id]

    calls = []

    async def match(_db, **kwargs):
        calls.append(kwargs)
        selected_type = kwargs.get("offering_type_id")
        if selected_type is None:
            return {
                "signals": None,
                "score": None,
                "excluded_providers": [{"reason_code": "TYPE_SELECTION_REQUIRED"}],
            }
        if selected_type == tap_type_id:
            return {
                "signals": object(),
                "score": 88,
                "earliest_slot": {
                    "starts_at": "2026-09-21T10:00:00",
                    "date": "2026-09-21",
                    "time_window": "10:00-11:00",
                },
            }
        return {"signals": None, "score": None, "excluded_providers": []}

    monkeypatch.setattr(catalog, "_booking_candidate_pairs", pairs)
    monkeypatch.setattr(catalog, "_priceable_type_ids", priceable_types)
    monkeypatch.setattr(matching_engine, "select_best_provider", match)

    result = await catalog.booking_ready_service_matches(_DB(), "140412")

    assert set(result) == {service_id}
    assert result[service_id]["job_type_ids"] == {job_type_id}
    assert result[service_id]["type_ids"] == {tap_type_id}
    assert result[service_id]["type_job_type_ids"] == {
        tap_type_id: {job_type_id},
    }
    assert [call.get("offering_type_id") for call in calls] == [
        None, tap_type_id, basin_type_id,
    ]


@pytest.mark.asyncio
async def test_problem_catalog_excludes_job_types_without_ready_provider(monkeypatch):
    from types import SimpleNamespace

    from app.engines.ai_conversation.backend_tools import BackendToolExecutor
    from app.engines.home_service_booking import offering_catalog_service as catalog

    offering_id = uuid.uuid4()
    ready_job = uuid.uuid4()
    unavailable_job = uuid.uuid4()
    draft = SimpleNamespace(
        offering_id=offering_id,
        zipcode="140412",
    )
    ready_problem = SimpleNamespace(
        id=uuid.uuid4(), name="Not cooling", description=None,
        icon_url=None, image_url=None, job_type_id=ready_job,
    )
    unavailable_problem = SimpleNamespace(
        id=uuid.uuid4(), name="Installation", description=None,
        icon_url=None, image_url=None, job_type_id=unavailable_job,
    )

    async def readiness(_db, _zipcode):
        return {offering_id: {"job_type_ids": {ready_job}}}

    monkeypatch.setattr(catalog, "booking_ready_service_matches", readiness)

    class _Rows:
        def all(self):
            return [ready_problem, unavailable_problem]

    class _ProblemDB:
        async def get(self, _model, _record_id):
            return draft

        async def execute(self, _statement):
            return _Rows()

    result = await BackendToolExecutor(
        _ProblemDB(), None, channel="instagram",
    )._tool_get_service_problems(str(uuid.uuid4()))

    assert [problem["name"] for problem in result["problems"]] == ["Not cooling"]


@pytest.mark.asyncio
async def test_problem_catalog_uses_selected_type_readiness(monkeypatch):
    from types import SimpleNamespace

    from app.engines.ai_conversation.backend_tools import BackendToolExecutor
    from app.engines.home_service_booking import offering_catalog_service as catalog

    offering_id = uuid.uuid4()
    selected_type_id = uuid.uuid4()
    ready_job = uuid.uuid4()
    other_type_job = uuid.uuid4()
    draft = SimpleNamespace(
        offering_id=offering_id,
        offering_type_id=selected_type_id,
        zipcode="140412",
    )
    rows = [
        SimpleNamespace(
            id=uuid.uuid4(), name="Tap installation", description=None,
            icon_url=None, image_url=None, job_type_id=ready_job,
        ),
        SimpleNamespace(
            id=uuid.uuid4(), name="Repair", description=None,
            icon_url=None, image_url=None, job_type_id=other_type_job,
        ),
    ]

    async def readiness(_db, _zipcode):
        return {
            offering_id: {
                "job_type_ids": {ready_job, other_type_job},
                "type_job_type_ids": {selected_type_id: {ready_job}},
            }
        }

    monkeypatch.setattr(catalog, "booking_ready_service_matches", readiness)

    class _Rows:
        def all(self):
            return rows

    class _ProblemDB:
        async def get(self, _model, _record_id):
            return draft

        async def execute(self, _statement):
            return _Rows()

    result = await BackendToolExecutor(
        _ProblemDB(), None, channel="instagram",
    )._tool_get_service_problems(str(uuid.uuid4()))

    assert [problem["name"] for problem in result["problems"]] == ["Tap installation"]


@pytest.mark.asyncio
async def test_covered_postcode_with_no_ready_provider_gets_honest_message(monkeypatch):
    from app.engines.messaging_gateway import flow
    from app.engines.messaging_gateway.constants import CHANNEL_WHATSAPP

    class _Thread:
        zipcode = "140412"
        city = "Bassi Pathana"
        ai_session_id = None
        customer_id = "customer-1"
        channel = CHANNEL_WHATSAPP

    async def no_ready_categories(_db, _zipcode):
        return []

    async def covered(_db, _zipcode):
        return True

    monkeypatch.setattr(flow, "_serviceable_categories", no_ready_categories)
    monkeypatch.setattr(flow, "_has_published_service_coverage", covered)

    turn = await flow._next_step(
        object(), _Thread(), None, None, CHANNEL_WHATSAPP, 0,
    )

    assert "Providers cover Bassi Pathana (140412)" in turn.text
    assert "eligible provider" in turn.text
    assert "open slot" in turn.text
