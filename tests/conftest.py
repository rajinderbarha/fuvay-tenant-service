"""
Pytest configuration for ServiceOS tests.
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
