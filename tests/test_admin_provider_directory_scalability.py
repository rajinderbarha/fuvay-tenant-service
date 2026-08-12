from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.engines.tenant_engine.hs_provider_directory_service import (
    HomeServicesProviderDirectoryService,
)


@pytest.mark.asyncio
async def test_provider_summary_uses_one_database_aggregate_query():
    counts = SimpleNamespace(
        total_providers=1_000_000,
        pending_verification=20,
        active=999_000,
        setup_incomplete=800,
        changes_requested=50,
        suspended=100,
        rejected=30,
        needs_attention=150,
    )
    result = MagicMock()
    result.one.return_value = counts
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)

    summary = await HomeServicesProviderDirectoryService(db).get_summary()

    db.execute.assert_awaited_once()
    assert summary["total_providers"] == 1_000_000
    assert summary["active"] == 999_000
    assert summary["needs_attention"] == 150


def test_tenant_model_declares_large_directory_composite_indexes():
    names = {index.name for index in __import__(
        "app.engines.tenant_engine.models", fromlist=["Tenant"]
    ).Tenant.__table__.indexes}
    assert {
        "ix_tenants_vertical_created_id",
        "ix_tenants_vertical_status_created",
        "ix_tenants_vertical_verification_created",
    } <= names
