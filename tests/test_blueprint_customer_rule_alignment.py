import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from sqlalchemy.dialects import postgresql
from app.engines.admin_catalog.tenant_service import TenantCatalogService
from app.engines.home_service_booking.service import HomeServiceChatbotBookingService


@pytest.mark.asyncio
async def test_dimension_query_includes_null_defaults_and_exact_scope():
    result = MagicMock()
    result.all.return_value = []
    db = MagicMock(execute=AsyncMock(return_value=result))
    await TenantCatalogService(db)._dimension_rules(uuid.uuid4(), uuid.uuid4())
    sql = str(db.execute.call_args.args[0].compile(dialect=postgresql.dialect()))
    assert 'job_type_id IS NULL' in sql and ' OR ' in sql


@pytest.mark.asyncio
@pytest.mark.parametrize('enabled,ask,required,expected', [(True, True, True, True), (False, True, True, False), (True, False, True, False), (True, True, False, False)])
async def test_customer_uses_dimension_rules_not_legacy_flags(enabled, ask, required, expected):
    db = MagicMock(get=AsyncMock(return_value=SimpleNamespace(schedule_required=False, address_required=False)))
    service = HomeServiceChatbotBookingService(db=db)
    offering = SimpleNamespace(id=uuid.uuid4(), is_type_required=not expected, is_brand_required=False, requires_schedule=True)
    draft = SimpleNamespace(job_type_id=uuid.uuid4(), service_job_workflow_id=uuid.uuid4(), issue_summary='Install', city='Delhi', offering_type_id=None)
    with patch.object(TenantCatalogService, '_dimension_rules', AsyncMock(return_value={'type': {'enabled':enabled, 'ask_customer':ask, 'required':required}})):
        fields = await service._get_required_field_list(offering, draft)
        missing = await service._compute_missing_fields(draft, offering)
    assert ('offering_type_id' in fields) is expected
    assert ('offering_type_id' in missing) is expected
    assert 'preferred_date' not in fields
