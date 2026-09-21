import uuid

import pytest


class _ScalarResult:
    def scalar_one_or_none(self):
        return None


def _problem(service_id, job_type_id, default_type_id=None):
    """One customer-visible problem row, as `_customer_problem_rows` returns it."""
    from types import SimpleNamespace

    return SimpleNamespace(
        service_id=service_id, problem_id=uuid.uuid4(),
        job_type_id=job_type_id, default_type_id=default_type_id,
    )


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

    ready_problem = _problem(ready_service, ready_job)
    unavailable_problem = _problem(ready_service, unavailable_job)

    async def problems(_db, service_ids):
        assert service_ids == [ready_service]
        return [ready_problem, unavailable_problem]

    monkeypatch.setattr(catalog, "_booking_candidate_pairs", pairs)
    monkeypatch.setattr(catalog, "_customer_problem_rows", problems)
    monkeypatch.setattr(matching_engine, "select_best_provider", match)

    db = _DB()
    first = await catalog.booking_ready_service_matches(db, "140412")
    second = await catalog.booking_ready_service_matches(db, "140412")

    assert set(first) == {ready_service}
    assert first[ready_service]["job_type_ids"] == {ready_job}
    assert first[ready_service]["problem_ids"] == {ready_problem.problem_id}
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

    async def problems(_db, _service_ids):
        return [_problem(service_id, job_type_id)]

    monkeypatch.setattr(catalog, "_booking_candidate_pairs", pairs)
    monkeypatch.setattr(catalog, "_priceable_type_ids", priceable_types)
    monkeypatch.setattr(catalog, "_customer_problem_rows", problems)
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
async def test_problem_catalog_shows_only_problems_a_ready_provider_takes(monkeypatch):
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
    # A ready job type, but the problem's built-in type is one nobody takes.
    unbookable_problem = SimpleNamespace(
        id=uuid.uuid4(), name="New pipeline for appliance", description=None,
        icon_url=None, image_url=None, job_type_id=ready_job,
    )

    async def readiness(_db, _zipcode):
        return {offering_id: {
            "job_type_ids": {ready_job},
            "problem_ids": {ready_problem.id},
        }}

    monkeypatch.setattr(catalog, "booking_ready_service_matches", readiness)

    class _Rows:
        def all(self):
            return [ready_problem, unavailable_problem, unbookable_problem]

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
                "problem_ids": {row.id for row in rows},
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


def _patch_readiness(monkeypatch, *, pairs, problems, match, priceable=()):
    from app.engines.home_service_booking import matching_engine
    from app.engines.home_service_booking import offering_catalog_service as catalog

    async def candidate_pairs(_db, _zipcode):
        return pairs

    async def priceable_types(_db, _service_id, _job_type_id):
        return list(priceable)

    async def problem_rows(_db, _service_ids):
        return problems

    monkeypatch.setattr(catalog, "_booking_candidate_pairs", candidate_pairs)
    monkeypatch.setattr(catalog, "_priceable_type_ids", priceable_types)
    monkeypatch.setattr(catalog, "_customer_problem_rows", problem_rows)
    monkeypatch.setattr(matching_engine, "select_best_provider", match)
    return catalog


_MATCHED = {"signals": object(), "score": 80}
_TYPE_REQUIRED = {
    "signals": None,
    "excluded_providers": [{"reason_code": "TYPE_SELECTION_REQUIRED"}],
}
_UNMATCHED = {
    "signals": None,
    "excluded_providers": [{"reason_code": "TYPE_NOT_SUPPORTED"}],
}


@pytest.mark.asyncio
async def test_problem_needing_an_unpriced_built_in_type_is_not_bookable(monkeypatch):
    """Do not offer Pipeline merely because another Plumbing type matches."""
    category_id, service_id, job_type_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    tap_type_id, pipeline_type_id = uuid.uuid4(), uuid.uuid4()
    tap = _problem(service_id, job_type_id)
    pipeline = _problem(service_id, job_type_id, pipeline_type_id)
    probed = []

    async def match(_db, **kwargs):
        probed.append(kwargs.get("offering_type_id"))
        return _MATCHED if kwargs.get("offering_type_id") == tap_type_id else _TYPE_REQUIRED

    catalog = _patch_readiness(
        monkeypatch, pairs=[(category_id, service_id, job_type_id)],
        problems=[tap, pipeline], match=match, priceable=[tap_type_id],
    )
    result = await catalog.booking_ready_service_matches(_DB(), "140412")

    assert result[service_id]["problem_ids"] == {tap.problem_id}
    assert probed == [None, tap_type_id]


@pytest.mark.asyncio
async def test_problem_built_in_type_is_bookable_when_a_provider_prices_it(monkeypatch):
    category_id, service_id, job_type_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    pipeline_type_id = uuid.uuid4()
    pipeline = _problem(service_id, job_type_id, pipeline_type_id)

    async def match(_db, **kwargs):
        return _MATCHED if kwargs.get("offering_type_id") == pipeline_type_id else _TYPE_REQUIRED

    catalog = _patch_readiness(
        monkeypatch, pairs=[(category_id, service_id, job_type_id)],
        problems=[pipeline], match=match, priceable=[pipeline_type_id],
    )
    result = await catalog.booking_ready_service_matches(_DB(), "140412")

    assert result[service_id]["problem_ids"] == {pipeline.problem_id}


@pytest.mark.asyncio
async def test_built_in_type_is_proven_when_its_job_type_matched_without_one(monkeypatch):
    """Matching with no type says nothing about THIS type, and choosing the
    problem sets it on the booking, so it has to be matched on its own."""
    category_id, service_id, job_type_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    split_type_id, window_type_id = uuid.uuid4(), uuid.uuid4()
    plain = _problem(service_id, job_type_id)
    split_gas = _problem(service_id, job_type_id, split_type_id)
    split_noise = _problem(service_id, job_type_id, split_type_id)
    window_gas = _problem(service_id, job_type_id, window_type_id)
    probed = []

    async def match(_db, **kwargs):
        probed.append(kwargs.get("offering_type_id"))
        return _MATCHED if kwargs.get("offering_type_id") in (None, split_type_id) else _UNMATCHED

    catalog = _patch_readiness(
        monkeypatch, pairs=[(category_id, service_id, job_type_id)],
        problems=[plain, split_gas, split_noise, window_gas], match=match,
    )
    result = await catalog.booking_ready_service_matches(_DB(), "140412")

    assert result[service_id]["problem_ids"] == {
        plain.problem_id, split_gas.problem_id, split_noise.problem_id,
    }
    # One match per distinct type, however many problems share it.
    assert probed == [None, split_type_id, window_type_id]
    # `type_ids` stays the priced types the Type question may offer.
    assert result[service_id]["type_ids"] == set()


@pytest.mark.asyncio
async def test_service_with_no_bookable_problem_is_not_offered(monkeypatch):
    """A service card must never lead to "There is nothing bookable here"."""
    category_id, job_type_id, pipeline_type_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    needs_untaken_type = uuid.uuid4()
    no_visible_problem = uuid.uuid4()
    bookable = uuid.uuid4()

    async def match(_db, **kwargs):
        return _UNMATCHED if kwargs.get("offering_type_id") else _MATCHED

    catalog = _patch_readiness(
        monkeypatch,
        pairs=[
            (category_id, needs_untaken_type, job_type_id),
            (category_id, no_visible_problem, job_type_id),
            (category_id, bookable, job_type_id),
        ],
        problems=[
            _problem(needs_untaken_type, job_type_id, pipeline_type_id),
            _problem(bookable, job_type_id),
        ],
        match=match,
    )
    result = await catalog.booking_ready_service_matches(_DB(), "140412")

    assert set(result) == {bookable}


@pytest.mark.asyncio
async def test_tap_on_a_service_nobody_here_can_take_starts_no_draft(monkeypatch):
    """An older carousel stays tappable. Starting a draft for a service no
    technician here can take led straight to "nothing bookable here"."""
    from types import SimpleNamespace

    from app.engines.messaging_gateway import flow

    started = []

    async def abandon(_db, _thread):
        return 0

    async def not_ready(_db, zipcode, category_slug, offering_slug):
        assert (zipcode, category_slug, offering_slug) == (
            "140412", "home-services", "geyser-repair",
        )
        return False

    class Executor:
        async def _tool_start_home_service_draft(self, **kwargs):
            started.append(kwargs)
            return {"draft_id": "d-new"}

    monkeypatch.setattr(flow, "abandon_social_booking_drafts", abandon)
    monkeypatch.setattr(flow, "_offering_ready", not_ready)
    thread = SimpleNamespace(zipcode="140412", city="Bassi Pathana")

    note, page, draft = await flow._apply_tap(
        object(), thread, Executor(), "of|home-services|geyser-repair", None,
    )

    assert started == []
    # No draft and page 0: `advance` goes on to show the ready services.
    assert note == flow.SERVICE_NOT_READY.format(zipcode="140412")
    assert page == 0 and draft is None


@pytest.mark.asyncio
async def test_empty_problem_list_offers_the_ready_services_instead(monkeypatch):
    from types import SimpleNamespace

    from app.engines.messaging_gateway import flow
    from app.engines.messaging_gateway.constants import CHANNEL_INSTAGRAM

    ready_services = flow.Turn("2 services are available.", {
        "rows": [{"id": "of|home-services|ac-service", "title": "AC Service"}],
    })
    shown_for = []

    async def next_step(_db, _thread, _executor, draft, _channel, _page, identity=None):
        shown_for.append(draft)
        return ready_services

    class Executor:
        async def _tool_get_service_problems(self, draft_id):
            return {"problems": []}

    monkeypatch.setattr(flow, "_next_step", next_step)

    turn = await flow._problem_step(
        object(), SimpleNamespace(zipcode="140412"), Executor(),
        {"id": "draft-1"}, CHANNEL_INSTAGRAM, 0,
    )

    assert shown_for == [None]   # the service list, not this draft again
    assert turn.text == (
        f"{flow.SERVICE_NOT_READY.format(zipcode='140412')}\n\n"
        "2 services are available."
    )
    assert turn.picker["rows"][0]["title"] == "AC Service"


@pytest.mark.asyncio
async def test_services_shown_right_after_the_pincode_are_filtered_by_it(monkeypatch):
    """The executor is built before the customer's reply is applied, so on the
    turn they TYPE their pincode it still held none. The service cards sent
    right then were every service published anywhere, and a tap on one no
    technician here could take ended on "nothing bookable here"."""
    from app.engines.home_service_booking import offering_catalog_service as catalog
    from app.engines.messaging_gateway import flow
    from app.engines.messaging_gateway.constants import CHANNEL_INSTAGRAM

    class _Thread:
        zipcode = None
        city = None
        ai_session_id = None
        customer_id = None
        last_options = None
        channel = CHANNEL_INSTAGRAM
        channel_user_id = "ig-1"
        display_name = "Customer"

    class _Category:
        slug = "home-services"
        name = "Home Services"
        image_url = icon_url = description = None

    class _DB:
        async def execute(self, _statement):
            return type("R", (), {"all": lambda _self: []})()

    offered_for = []

    async def offerings(_db, _category_slug, zipcode):
        offered_for.append(zipcode)
        return {"offerings": [
            {"id": str(uuid.uuid4()), "slug": "ac-service", "name": "AC Service"},
        ]}

    async def categories(_db, zipcode):
        assert zipcode == "140412"
        return [_Category()]

    async def area_city(_db, _zipcode):
        return "Bassi Pathana"

    monkeypatch.setattr(flow, "_serviceable_categories", categories)
    monkeypatch.setattr(flow, "_area_city", area_city)
    monkeypatch.setattr(catalog, "list_serviceable_offerings", offerings)

    turn = await flow.advance(
        _DB(), _Thread(), text="140412", reply_id=None, channel=CHANNEL_INSTAGRAM,
    )

    assert offered_for == ["140412"]
    assert [row["title"] for row in turn.picker["rows"]] == ["AC Service"]


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
