"""
Pytest configuration for Fuvay tests.
Phase 1+2: uses mocks for DB/Redis so tests run without Docker.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone


@pytest.fixture(autouse=True)
def mock_database(monkeypatch):
    """Mock DB session — returns None for scalar lookups (user not found in tests)."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_result.scalars.return_value.all.return_value = []
    
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()
    mock_session.flush = AsyncMock()
    mock_session.add = MagicMock()

    mock_factory = MagicMock(return_value=mock_session)
    monkeypatch.setattr("app.database._async_session_factory", mock_factory)
    monkeypatch.setattr("app.database._engine", MagicMock())


@pytest.fixture(autouse=True)
def mock_redis(monkeypatch):
    """Mock Redis — tokens are NOT blacklisted by default (exists returns 0)."""
    mock_r = AsyncMock()
    mock_r.ping = AsyncMock(return_value=True)
    mock_r.get = AsyncMock(return_value=None)
    mock_r.set = AsyncMock(return_value=True)
    mock_r.setex = AsyncMock(return_value=True)
    mock_r.delete = AsyncMock(return_value=1)
    mock_r.keys = AsyncMock(return_value=[])
    mock_r.publish = AsyncMock(return_value=1)
    mock_r.incr = AsyncMock(return_value=1)
    mock_r.expire = AsyncMock(return_value=True)
    # CRITICAL: exists must return 0 so tokens are not treated as blacklisted
    mock_r.exists = AsyncMock(return_value=0)
    
    monkeypatch.setattr("app.redis_client._redis", mock_r)


@pytest.fixture(autouse=True)
def offline_card_artwork(monkeypatch):
    """Instagram card artwork is verified by fetching it the way Meta would.

    The suite must not reach the network, so the check is off by default and a
    test that wants it asks for the `verify_card_artwork` fixture.
    """
    from app.config import get_settings
    from app.engines.messaging_gateway import problem_cards

    problem_cards.reset_artwork_cache()
    monkeypatch.setattr(get_settings(), "INSTAGRAM_CARD_VERIFY_TIMEOUT_SECONDS", 0.0)


@pytest.fixture
def verify_card_artwork(monkeypatch):
    """Turn card verification back on, with its HTTP client under the test's
    control. Returns a dict of `url -> (status, content-type)` to answer with;
    anything not listed answers 404, and `.fetched` records every URL asked
    for, so a test can prove a verdict came from the cache."""
    from app.config import get_settings
    from app.engines.messaging_gateway import problem_cards

    class Answers(dict):
        fetched: list

    answers = Answers()
    answers.fetched = fetched = []

    class Response:
        def __init__(self, status_code, content_type):
            self.status_code = status_code
            self.headers = {"content-type": content_type} if content_type else {}

    class Client:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get(self, url, **kwargs):
            fetched.append(url)
            status, content_type = answers.get(url, (404, "text/html"))
            return Response(status, content_type)

    problem_cards.reset_artwork_cache()
    monkeypatch.setattr(get_settings(), "INSTAGRAM_CARD_VERIFY_TIMEOUT_SECONDS", 3.5)
    monkeypatch.setattr(problem_cards, "_artwork_client", lambda timeout: Client())
    return answers
