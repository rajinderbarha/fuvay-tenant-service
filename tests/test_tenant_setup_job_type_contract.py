"""Exact job-type contract shared by Admin setup, tenant setup and booking."""
from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.engines.admin_catalog.tenant_service import TenantCatalogService
from app.engines.home_service_booking.service import HomeServiceChatbotBookingService


def _result(*, one=None, scalar=None):
    result = MagicMock()
    result.scalar_one_or_none.return_value = one
    result.scalars.return_value.first.return_value = scalar
    result.scalars.return_value.all.return_value = [scalar] if scalar is not None else []
    return result


@pytest.mark.asyncio
async def test_tenant_price_uses_exact_job_type_and_only_published_offering():
    tenant_id, master_id, repair_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    tenant_service = SimpleNamespace(id=uuid.uuid4())
    db = AsyncMock()
    db.execute.return_value = _result(scalar=tenant_service)
    service = HomeServiceChatbotBookingService(db)
    service._assert_tenant_owns_ts = MagicMock()
    resolved = {"resolved": True, "minimum_price": 900}
    service_resolver = AsyncMock(return_value=resolved)
    # The method instantiates the canonical resolver; patch only its method.
    from app.engines.admin_catalog import tenant_service as module
    original = module.TenantCatalogService.resolve_tenant_price
    module.TenantCatalogService.resolve_tenant_price = service_resolver
    try:
        result = await service._resolve_tenant_price_for(
            tenant_id, master_id, None, None, job_type_id=repair_id,
        )
    finally:
        module.TenantCatalogService.resolve_tenant_price = original

    assert result == resolved
    sql = str(db.execute.await_args.args[0])
    assert "tenant_services.job_type_id" in sql
    assert "tenant_services.is_enabled" in sql
    assert "tenant_services.setup_status" in sql


@pytest.mark.asyncio
async def test_tenant_price_without_job_type_fails_closed_when_ambiguous():
    db = AsyncMock()
    result = _result()
    result.scalars.return_value.all.return_value = [SimpleNamespace(), SimpleNamespace()]
    db.execute.return_value = result
    service = HomeServiceChatbotBookingService(db)

    resolved = await service._resolve_tenant_price_for(
        uuid.uuid4(), uuid.uuid4(), None, None, job_type_id=None,
    )

    assert resolved is None


@pytest.mark.asyncio
async def test_effective_pricing_behavior_is_exact_job_type_workflow():
    db = AsyncMock()
    db.execute.return_value = _result(one="inspection_required")
    service = HomeServiceChatbotBookingService(db)
    offering = SimpleNamespace(id=uuid.uuid4(), pricing_model="fixed")

    result = await service._effective_pricing_model(offering, uuid.uuid4())

    assert result == "visit_fee_plus_quote"
    sql = str(db.execute.await_args.args[0])
    assert "service_job_workflow.job_type_id" in sql
    assert "service_job_workflow.status" in sql


@pytest.mark.asyncio
async def test_setup_revision_is_resolved_from_exact_job_type_link():
    db = AsyncMock()
    db.execute.return_value = _result(one=7)
    service = TenantCatalogService(db)

    revision = await service._setup_rule_revision(uuid.uuid4(), uuid.uuid4())

    assert revision == 7
    sql = str(db.execute.await_args.args[0])
    assert "master_service_job_types.master_service_id" in sql
    assert "master_service_job_types.job_type_id" in sql
