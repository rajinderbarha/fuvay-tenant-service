"""Missing signup category grants: isolated tests, no live data changes."""
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.dialects import postgresql

from app.engines.entitlement.service import EntitlementService, entitlement_service
from app.engines.admin_catalog.tenant_service import TenantCatalogService
from app.exceptions import ServiceOSException


def scalar(value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


@pytest.fixture
def repair_case():
    tenant_id, group_id, vertical_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    module = NS(status='ACTIVE', effective_from=None, effective_until=None, source='tenant_registration',
                configuration={'grant_policy':'active_vertical_service_groups'})
    state = NS(tenant=NS(id=tenant_id, status='onboarding_pending'),
        group=NS(id=group_id, category_id=uuid.uuid4(), status='active', deleted_at=None),
        category=NS(is_active=True, vertical_type='home_services', category_type='home_services'),
        vertical=NS(id=vertical_id, is_enabled=True), category_row=None, module=module,
        enrollment=NS(status='draft_setup'), registration=uuid.uuid4())
    db = MagicMock(commit=AsyncMock(), flush=AsyncMock())
    def configure():
        db.execute = AsyncMock(side_effect=[scalar(state.tenant), scalar(state.vertical), scalar(state.category_row),
            scalar(state.module), scalar(state.enrollment), scalar(state.registration)])
        db.get = AsyncMock(side_effect=[state.group, state.category])
    svc = EntitlementService()
    svc.has_category_entitlement = AsyncMock(side_effect=[False, True])
    svc.assign_module_entitlement = AsyncMock()
    svc.assign_category_entitlement = AsyncMock()
    return NS(state=state, db=db, svc=svc, configure=configure,
              args={'tenant_id':tenant_id, 'category_id':group_id, 'actor_id':uuid.uuid4(), 'actor_role':'tenant_owner'})


@pytest.mark.asyncio
async def test_new_service_group_gets_missing_signup_grant(repair_case):
    c = repair_case
    c.configure()
    assert await c.svc.ensure_registration_category_access(c.db, **c.args)
    c.svc.assign_module_entitlement.assert_not_awaited()
    grant = c.svc.assign_category_entitlement.await_args.kwargs
    assert grant['tenant_id'] == c.args['tenant_id']
    assert grant['category_id'] == c.args['category_id']
    assert grant['source'] == 'tenant_registration' and grant['commit'] is False
    c.db.commit.assert_not_awaited()
    assert 'FOR UPDATE' in str(c.db.execute.await_args_list[0].args[0])


@pytest.mark.asyncio
async def test_legacy_completed_signup_repairs_module_and_group(repair_case):
    c = repair_case
    c.state.module = None
    c.configure()
    assert await c.svc.ensure_registration_category_access(c.db, **c.args)
    c.svc.assign_module_entitlement.assert_awaited_once()
    c.svc.assign_category_entitlement.assert_awaited_once()
    query = c.db.execute.await_args_list[-1].args[0]
    sql = str(query.compile(dialect=postgresql.dialect()))
    assert 'created_tenant_id' in sql and 'selected_vertical_key' in sql
    assert 'completed' in query.compile().params.values()
    c.db.commit.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize('status', ['INACTIVE','SUSPENDED','EXPIRED','PENDING','ARCHIVED','ACTIVE'])
async def test_existing_category_decision_is_never_overwritten(repair_case, status):
    c = repair_case
    c.state.category_row = NS(status=status)
    c.configure()
    assert not await c.svc.ensure_registration_category_access(c.db, **c.args)
    c.svc.assign_category_entitlement.assert_not_awaited()
    c.svc.assign_module_entitlement.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize('reason', ['inactive','suspended','expired','future','different_vertical','inactive_group',
    'deleted_group','disabled_vertical','suspended_enrollment','missing_enrollment','missing_signup','admin_restricted','suspended_tenant'])
async def test_missing_grant_does_not_bypass_access_controls(repair_case, reason):
    c = repair_case
    now = datetime.now(timezone.utc)
    if reason == 'inactive': c.state.module.status = 'INACTIVE'
    if reason == 'suspended': c.state.module.status = 'SUSPENDED'
    if reason == 'expired': c.state.module.effective_until = now - timedelta(days=1)
    if reason == 'future': c.state.module.effective_from = now + timedelta(days=1)
    if reason == 'different_vertical': c.state.category.vertical_type = 'real_estate'
    if reason == 'inactive_group': c.state.group.status = 'inactive'
    if reason == 'deleted_group': c.state.group.deleted_at = now
    if reason == 'disabled_vertical': c.state.vertical.is_enabled = False
    if reason == 'suspended_enrollment': c.state.enrollment.status = 'suspended'
    if reason == 'missing_enrollment': c.state.enrollment = None
    if reason == 'missing_signup': c.state.module, c.state.registration = None, None
    if reason == 'admin_restricted':
        c.state.module.configuration = None
        c.state.module.source = 'admin_manual'
    if reason == 'suspended_tenant': c.state.tenant.status = 'suspended'
    c.configure()
    assert not await c.svc.ensure_registration_category_access(c.db, **c.args)
    c.svc.assign_module_entitlement.assert_not_awaited()
    c.svc.assign_category_entitlement.assert_not_awaited()


@pytest.mark.asyncio
async def test_concurrent_repeat_sees_existing_grant(repair_case):
    c = repair_case
    c.configure()
    c.svc.has_category_entitlement = AsyncMock(return_value=True)
    assert await c.svc.ensure_registration_category_access(c.db, **c.args)
    c.svc.assign_category_entitlement.assert_not_awaited()


@pytest.mark.asyncio
async def test_canonical_resolver_rejects_cross_tenant_or_vertical_parents():
    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    db = MagicMock(execute=AsyncMock(return_value=result))
    tenant_id = uuid.uuid4()
    assert not await EntitlementService().has_category_entitlement(db, tenant_id, uuid.uuid4())
    query = db.execute.await_args.args[0]
    sql = str(query.compile(dialect=postgresql.dialect()))
    assert 'tenant_module_entitlements.tenant_id = tenant_category_entitlements.tenant_id' in sql
    assert 'verticals.key = coalesce' in sql
    assert 'service_groups.deleted_at IS NULL' in sql
    assert [tenant_id] in query.compile().params.values()


@pytest.mark.asyncio
@pytest.mark.parametrize('repaired', [True, False])
async def test_offer_checkbox_attempts_scoped_repair_before_denial(repaired):
    tenant_id, group_id = uuid.uuid4(), uuid.uuid4()
    master = NS(id=uuid.uuid4(), category_id=uuid.uuid4(), service_group_id=group_id, is_active=True)
    # vertical_type is read by tenant_service.py's provider_owns_prices check,
    # added after this test in the same session -- a real Home Services
    # category row always carries it.
    db = MagicMock(execute=AsyncMock(side_effect=[scalar(master), scalar(NS(is_active=True, vertical_type="home_services"))]))
    svc = TenantCatalogService(db, actor_tenant_id=tenant_id, actor_role='tenant_owner', actor_id=uuid.uuid4())
    # Stop after the entitlement gate, before creating real service records.
    svc._resolve_active_job_type = AsyncMock(side_effect=ServiceOSException('TEST_PAST_ENTITLEMENT', 'passed gate', status_code=422))
    with patch.object(entitlement_service, 'has_category_entitlement', AsyncMock(return_value=False)), \
         patch.object(entitlement_service, 'ensure_registration_category_access', AsyncMock(return_value=repaired)) as repair:
        with pytest.raises(ServiceOSException) as error:
            await svc.enable_service({'master_service_id':str(master.id)})
    assert error.value.error_code == ('TEST_PAST_ENTITLEMENT' if repaired else 'CATEGORY_NOT_ENTITLED')
    assert repair.await_args.kwargs['tenant_id'] == tenant_id
    assert repair.await_args.kwargs['category_id'] == group_id
