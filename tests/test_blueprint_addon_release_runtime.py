"""Isolated regressions: no live database, payments, or catalog mutations."""
import uuid
from decimal import Decimal
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError
from sqlalchemy.dialects import postgresql

from app.exceptions import ServiceOSException
from app.engines.admin_catalog.addon_runtime import resolve_addons, validate_mapping, validate_frozen_addons
from app.engines.admin_catalog.blueprint_release import build_release_manifest, validate_release
from app.engines.admin_catalog.service_option_service import ServiceOptionService
from app.engines.execution.home_service_router import CatalogAddonBody, staff_add_catalog_addon
from app.engines.home_service_booking.service import HomeServiceChatbotBookingService


def mapping(**changes):
    fields = dict(id=uuid.uuid4(), master_service_id=uuid.uuid4(), job_type_id=uuid.uuid4(),
        service_option_id=uuid.uuid4(), deleted_at=None, status='active', usage='OPTIONAL',
        customer_selectable=True, available_before_booking=True, technician_selectable=True,
        available_after_inspection=True, affects_estimate=True, quantity_supported=True,
        minimum_quantity=1, maximum_quantity=3)
    return NS(**{**fields, **changes})


def addon_db(row):
    return MagicMock(get=AsyncMock(side_effect=[row, NS(name='Extra cleaning', status='active')]),
        scalar=AsyncMock(return_value=NS(pricing_model='FIXED', effective_from=None, effective_to=None)))


@pytest.mark.parametrize('changes,actor', [
    ({'status':'inactive'}, 'customer'), ({'usage':'DISABLED'}, 'customer'),
    ({'deleted_at':True}, 'customer'), ({'job_type_id':None}, 'customer'),
    ({'customer_selectable':False}, 'customer'), ({'available_before_booking':False}, 'customer'),
    ({'technician_selectable':False}, 'technician'), ({'available_after_inspection':False}, 'technician'),
    ({}, 'unknown'),
])
def test_mapping_rejects_ineligible_actor_or_scope(changes, actor):
    row = mapping(**changes)
    with pytest.raises(ServiceOSException):
        validate_mapping(row, service_id=row.master_service_id, job_type_id=row.job_type_id, actor=actor)


def test_mapping_rejects_other_service_and_job_type():
    row = mapping()
    for service_id, job_type_id in [(uuid.uuid4(), row.job_type_id), (row.master_service_id, uuid.uuid4())]:
        with pytest.raises(ServiceOSException):
            validate_mapping(row, service_id=service_id, job_type_id=job_type_id, actor='customer')


@pytest.mark.asyncio
@pytest.mark.parametrize('quantity', [0, -1, 1.5, True, '2', 4])
async def test_quantity_is_whole_positive_and_within_mapping_bounds(quantity):
    row = mapping()
    with pytest.raises(ServiceOSException):
        await resolve_addons(addon_db(row), tenant_id=uuid.uuid4(), service_id=row.master_service_id,
            job_type_id=row.job_type_id, selections=[{'mapping_id':str(row.id), 'quantity':quantity}])


@pytest.mark.asyncio
async def test_prices_come_from_provider_and_client_price_is_ignored():
    row = mapping()
    price = {'unit_price':'25.00', 'total':'50.00', 'currency':'INR'}
    with patch.object(ServiceOptionService, 'resolve_tenant_option_price', AsyncMock(return_value=price)) as resolver:
        lines = await resolve_addons(addon_db(row), tenant_id=uuid.uuid4(), service_id=row.master_service_id,
            job_type_id=row.job_type_id, selections=[{'mapping_id':str(row.id), 'quantity':2, 'unit_price':0}])
    assert lines[0]['total'] == '50.00'
    assert resolver.await_args.args[1:] == (row.id, 2)


@pytest.mark.asyncio
async def test_duplicate_addons_are_rejected():
    row = mapping()
    with patch.object(ServiceOptionService, 'resolve_tenant_option_price', AsyncMock(return_value={'unit_price':'25', 'total':'25', 'currency':'INR'})):
        with pytest.raises(ServiceOSException, match='once'):
            await resolve_addons(addon_db(row), tenant_id=uuid.uuid4(), service_id=row.master_service_id,
                job_type_id=row.job_type_id, selections=[{'mapping_id':str(row.id)}] * 2)


@pytest.mark.asyncio
@pytest.mark.parametrize('actor', ['customer', 'technician'])
async def test_range_price_never_silently_becomes_a_fixed_charge(actor):
    row = mapping()
    db = addon_db(row)
    db.scalar.return_value.pricing_model = 'RANGE'
    with pytest.raises(ServiceOSException) as error:
        await resolve_addons(db, tenant_id=uuid.uuid4(), service_id=row.master_service_id,
            job_type_id=row.job_type_id, selections=[{'mapping_id':str(row.id)}], actor=actor)
    assert error.value.error_code == 'ADDON_ESTIMATE_REQUIRED'


@pytest.mark.asyncio
async def test_nonpriced_addon_does_not_need_fake_provider_price():
    row = mapping(affects_estimate=False)
    db = addon_db(row)
    db.scalar.return_value.pricing_model = None
    with patch.object(ServiceOptionService, 'resolve_tenant_option_price', AsyncMock()) as price:
        lines = await resolve_addons(db, tenant_id=uuid.uuid4(), service_id=row.master_service_id,
            job_type_id=row.job_type_id, selections=[{'mapping_id':str(row.id)}])
    price.assert_not_awaited()
    assert lines[0]['total'] == '0.00'


@pytest.mark.asyncio
async def test_changed_price_requires_reconfirmation():
    draft = NS(price_snapshot={'selected_addons':[{'mapping_id':str(uuid.uuid4())}], 'addon_lines':[{'total':'25'}]},
        selected_tenant_id=uuid.uuid4(), offering_id=uuid.uuid4(), job_type_id=uuid.uuid4())
    with patch('app.engines.admin_catalog.addon_runtime.resolve_addons', AsyncMock(return_value=[{'total':'30'}])):
        with pytest.raises(ServiceOSException) as error:
            await validate_frozen_addons(MagicMock(), draft)
    assert error.value.error_code == 'ADDON_PRICE_CHANGED'


@pytest.mark.parametrize('quantity', [True, '2', 0, -1, 2.5])
def test_technician_request_rejects_coerced_quantity(quantity):
    with pytest.raises(ValidationError):
        CatalogAddonBody(quote_id=uuid.uuid4(), mapping_id=uuid.uuid4(), quantity=quantity)


@pytest.mark.asyncio
@pytest.mark.parametrize('scenario,code', [('foreign','ADDON_QUOTE_ACCESS_DENIED'),
    ('superseded','ADDON_QUOTE_NOT_EDITABLE'), ('locked','ADDON_QUOTE_NOT_EDITABLE'),
    ('sent','ADDON_QUOTE_NOT_EDITABLE'), ('duplicate','ADDON_ALREADY_ADDED')])
async def test_technician_cannot_change_foreign_locked_or_duplicate_estimate(scenario, code):
    from app.engines.quote_checklist.quote_service import ServiceJobQuoteService
    from app.engines.execution import home_service_router as router
    job = NS(id=uuid.uuid4(), tenant_id=uuid.uuid4(), status='inspection_done')
    quote = NS(id=uuid.uuid4(), job_id=job.id, tenant_id=job.tenant_id, is_current=True, status='draft', locked_at=None)
    if scenario == 'foreign': quote.tenant_id = uuid.uuid4()
    if scenario == 'superseded': quote.is_current = False
    if scenario == 'locked': quote.locked_at = True
    if scenario == 'sent': quote.status = 'sent_to_customer'
    db = MagicMock(scalar=AsyncMock(return_value=uuid.uuid4() if scenario == 'duplicate' else None))
    user = NS(user_id=uuid.uuid4(), tenant_id=job.tenant_id)
    request = NS(state=NS(request_id='test'))
    with patch.object(router._svc, '_get_job', AsyncMock(return_value=job)), \
         patch.object(router._svc, '_assert_staff_owns_job'), \
         patch.object(router, '_staff_member_id', AsyncMock(return_value=user.user_id)), \
         patch.object(ServiceJobQuoteService, '_get_quote', AsyncMock(return_value=quote)) as get_quote, \
         patch.object(ServiceJobQuoteService, 'add_item', AsyncMock()) as add:
        with pytest.raises(ServiceOSException) as error:
            await staff_add_catalog_addon(job.id, CatalogAddonBody(quote_id=quote.id, mapping_id=uuid.uuid4()), request, user, db)
    assert error.value.error_code == code
    assert get_quote.await_args.kwargs['for_update'] is True
    add.assert_not_awaited()


@pytest.mark.asyncio
async def test_release_manifest_covers_all_tabs_without_tenant_prices():
    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    db = MagicMock(execute=AsyncMock(return_value=result))
    manifest = await build_release_manifest(db, uuid.uuid4())
    assert {'job_types', 'workflows', 'dimensions', 'questions', 'question_options', 'question_rules',
        'problems', 'options', 'checklists', 'checklist_versions', 'checklist_sections', 'checklist_items',
        'types', 'brands', 'option_definitions', 'problem_definitions'} <= manifest.keys()
    queries = '\n'.join(str(call.args[0].compile(dialect=postgresql.dialect())) for call in db.execute.await_args_list)
    assert 'tenant_supported_service_options' not in queries


@pytest.mark.asyncio
async def test_release_blocks_missing_job_types_without_writing():
    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    db = MagicMock(execute=AsyncMock(return_value=result))
    with pytest.raises(ServiceOSException) as error:
        await validate_release(db, uuid.uuid4())
    assert error.value.error_code == 'BLUEPRINT_RELEASE_INCOMPLETE'
    db.add.assert_not_called()
    db.commit.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize('version_status,passes', [('PUBLISHED', True), ('DRAFT', False)])
async def test_release_requires_published_checklist_version(version_status, passes):
    from app.engines.admin_catalog.dimension_service import CatalogDimensionService
    from app.engines.admin_catalog.job_type_blueprint_service import JobTypeBlueprintService
    link_result, mapping_result = MagicMock(), MagicMock()
    link_result.scalars.return_value.all.return_value = [NS(id=uuid.uuid4(), job_type_id=uuid.uuid4())]
    mapping_result.scalars.return_value.all.return_value = [NS(checklist_template_version_id=uuid.uuid4())]
    db = MagicMock(execute=AsyncMock(side_effect=[link_result, mapping_result]),
        get=AsyncMock(side_effect=[NS(status=version_status, checklist_template_id=uuid.uuid4()), NS(status='active')]))
    with patch.object(CatalogDimensionService, 'get_blueprint_readiness', AsyncMock(return_value={'checks':[]})), \
         patch.object(JobTypeBlueprintService, 'review_workflow_steps', AsyncMock(return_value={'errors':[]})), \
         patch.object(JobTypeBlueprintService, 'get_workflow', AsyncMock(return_value={'checklist_required':True})):
        if passes:
            await validate_release(db, uuid.uuid4())
        else:
            with pytest.raises(ServiceOSException) as error:
                await validate_release(db, uuid.uuid4())
            assert error.value.error_code == 'BLUEPRINT_RELEASE_INCOMPLETE'


@pytest.mark.asyncio
async def test_existing_booking_keeps_frozen_workflow_pricing():
    service_id, job_type_id, workflow_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    db = MagicMock(get=AsyncMock(return_value=NS(master_service_id=service_id, job_type_id=job_type_id,
        pricing_behavior='inspection_required')))
    svc = HomeServiceChatbotBookingService(db=db)
    actual = await svc._effective_pricing_model(NS(id=service_id, pricing_model='fixed'), job_type_id, workflow_id)
    assert actual == 'visit_fee_plus_quote'
    db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_addon_total_is_added_once_when_price_is_recomputed():
    result = MagicMock()
    result.scalars.return_value.first.return_value = None
    db = MagicMock(get=AsyncMock(return_value=None), execute=AsyncMock(return_value=result))
    svc = HomeServiceChatbotBookingService(db=db)
    svc._effective_pricing_model = AsyncMock(return_value='fixed')
    svc._resolve_provider_consultation_fee = AsyncMock(return_value=None)
    svc._resolve_selected_tenant_price = AsyncMock(return_value={'minimum_price':100, 'maximum_price':100})
    draft = NS(category_id=uuid.uuid4(), city='Delhi', offering_id=uuid.uuid4(), job_type_id=uuid.uuid4(),
        selected_tenant_id=uuid.uuid4(), service_job_workflow_id=None,
        price_snapshot={'selected_addons':[{'mapping_id':str(uuid.uuid4()), 'quantity':2}]})
    with patch('app.engines.admin_catalog.addon_runtime.resolve_addons', AsyncMock(return_value=[{'total':'50.00'}])), \
         patch('app.engines.vertical_monetization.calculation_service.get_current_policy_by_vertical_key', AsyncMock(return_value=None)):
        first = await svc._compute_price_snapshot(draft, NS())
        draft.price_snapshot = first
        second = await svc._compute_price_snapshot(draft, NS())
    assert first['base_price'] == second['base_price'] == 150
    assert second['service_base_price'] == 100
    assert second['customer_total'] == 150
