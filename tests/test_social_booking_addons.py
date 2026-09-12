"""Social add-on regressions; all database and transport calls are isolated."""
import copy
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.engines.messaging_gateway import addons, flow, meta_client, pickers
from app.engines.messaging_gateway.constants import PICKER_PREFIXES, PICK_ADDON
from app.engines.home_service_booking.service import HomeServiceChatbotBookingService
from app.exceptions import ServiceOSException


@pytest.fixture
def context(monkeypatch):
    thread = NS(ai_session_id=uuid.uuid4(), customer_id=None, channel='whatsapp')
    row = NS(id=uuid.uuid4(), selected_tenant_id=uuid.uuid4(), job_type_id=uuid.uuid4(),
        ai_session_id=thread.ai_session_id, customer_id=None, status='provider_matched',
        price_snapshot={'pricing_mode':'fixed', 'customer_total':100, 'standard_price':100,
                        'selected_addons':[], 'addon_lines':[]})
    row.to_dict = lambda: dict(id=str(row.id), selected_tenant_id=str(row.selected_tenant_id),
        job_type_id=str(row.job_type_id), status=row.status, price_snapshot=copy.deepcopy(row.price_snapshot))
    option = dict(service_option_mapping_id=str(uuid.uuid4()), name='Extra cleaning',
        unit_price='25.00', minimum_quantity=1, maximum_quantity=2, quantity_supported=True)
    svc = MagicMock()
    svc.get_addons = AsyncMock(return_value={'options':[option]})
    svc.confirm_price_choice = AsyncMock()
    async def select(draft_id, customer_id, selections):
        lines = [{'mapping_id':s['mapping_id'], 'name':option['name'], 'quantity':s['quantity'],
                  'unit_price':option['unit_price'], 'total':str(float(option['unit_price']) * s['quantity'])}
                 for s in selections]
        total = 100 + sum(float(line['total']) for line in lines)
        row.price_snapshot = dict(pricing_mode='fixed', selected_addons=selections, addon_lines=lines,
                                  customer_total=total, standard_price=total)
    svc.set_addons = AsyncMock(side_effect=select)
    monkeypatch.setattr(addons, 'HomeServiceChatbotBookingService', lambda db: svc)
    owner = AsyncMock(return_value=row)
    monkeypatch.setattr(addons, '_owned', owner)
    frozen = AsyncMock()
    monkeypatch.setattr(addons, 'validate_frozen_addons', frozen)
    db = MagicMock(commit=AsyncMock())
    return NS(thread=thread, row=row, option=option, svc=svc, db=db, owner=owner, frozen=frozen)


def payload(turn, action):
    return next(r['id'].partition('|')[2] for r in turn.picker['rows'] if r['id'].split('|')[3] == action)


@pytest.mark.asyncio
@pytest.mark.parametrize('channel', ['whatsapp', 'instagram'])
async def test_both_channels_select_and_explicitly_accept_updated_total(context, channel):
    c = context
    c.thread.channel = channel
    turn = await addons.step(c.db, c.thread, c.row.to_dict(), channel)
    assert '100' in turn.text
    assert PICK_ADDON in PICKER_PREFIXES
    updated = await addons.handle(c.db, c.thread, c.row.to_dict(), channel, payload(turn, 'choose'))
    assert '125' in updated.text and 'Extra cleaning' in updated.text
    assert addons.needs_review(c.row.to_dict())
    c.svc.confirm_price_choice.assert_not_awaited()
    result = await addons.handle(c.db, c.thread, c.row.to_dict(), channel, payload(updated, 'done'))
    assert result is None
    c.svc.confirm_price_choice.assert_awaited_once_with(c.row.id, 'standard', c.thread.customer_id)
    assert not addons.needs_review(c.row.to_dict())


@pytest.mark.asyncio
async def test_duplicate_old_button_never_increments_quantity(context):
    c = context
    turn = await addons.step(c.db, c.thread, c.row.to_dict(), 'whatsapp')
    tap = payload(turn, 'choose')
    await addons.handle(c.db, c.thread, c.row.to_dict(), 'whatsapp', tap)
    repeated = await addons.handle(c.db, c.thread, c.row.to_dict(), 'whatsapp', tap)
    assert 'changed' in repeated.text
    assert c.svc.set_addons.await_count == 1
    assert c.row.price_snapshot['selected_addons'][0]['quantity'] == 1


@pytest.mark.asyncio
async def test_quantity_controls_respect_maximum_and_allow_removal(context):
    c = context
    initial = await addons.step(c.db, c.thread, c.row.to_dict(), 'instagram')
    selected = await addons.handle(c.db, c.thread, c.row.to_dict(), 'instagram', payload(initial, 'choose'))
    quantity = await addons.handle(c.db, c.thread, c.row.to_dict(), 'instagram', payload(selected, 'choose'))
    increment = next(r['id'].partition('|')[2] for r in quantity.picker['rows'] if r['title'] == 'Increase quantity')
    selected = await addons.handle(c.db, c.thread, c.row.to_dict(), 'instagram', increment)
    quantity = await addons.handle(c.db, c.thread, c.row.to_dict(), 'instagram', payload(selected, 'choose'))
    assert 'Increase quantity' not in [r['title'] for r in quantity.picker['rows']]
    remove = next(r['id'].partition('|')[2] for r in quantity.picker['rows'] if r['title'] == 'Remove add-on')
    await addons.handle(c.db, c.thread, c.row.to_dict(), 'instagram', remove)
    assert c.row.price_snapshot['selected_addons'] == []
    assert c.row.price_snapshot['customer_total'] == 100


@pytest.mark.asyncio
async def test_price_change_is_shown_and_never_autoaccepted(context):
    c = context
    turn = await addons.step(c.db, c.thread, c.row.to_dict(), 'whatsapp')
    turn = await addons.handle(c.db, c.thread, c.row.to_dict(), 'whatsapp', payload(turn, 'choose'))
    c.option['unit_price'] = '40.00'
    c.frozen.side_effect = ServiceOSException('ADDON_PRICE_CHANGED', 'Review new price.', status_code=409)
    updated = await addons.handle(c.db, c.thread, c.row.to_dict(), 'whatsapp', payload(turn, 'done'))
    assert '140' in updated.text and 'price changed' in updated.text
    c.svc.confirm_price_choice.assert_not_awaited()
    assert addons.needs_review(c.row.to_dict())


@pytest.mark.asyncio
async def test_old_booking_button_cannot_touch_current_draft(context):
    c = context
    turn = await addons.handle(c.db, c.thread, c.row.to_dict(), 'whatsapp', f'{uuid.uuid4()}|anything|clear')
    assert 'older booking' in turn.text
    c.owner.assert_not_awaited()
    c.svc.set_addons.assert_not_awaited()


@pytest.mark.asyncio
async def test_session_ownership_is_enforced_by_database_query():
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db = MagicMock(execute=AsyncMock(return_value=result))
    thread = NS(ai_session_id=uuid.uuid4(), customer_id=None)
    with pytest.raises(ServiceOSException) as error:
        await addons._owned(db, thread, uuid.uuid4())
    assert error.value.error_code == 'ADDON_CHAT_ACCESS_DENIED'
    statement = db.execute.await_args.args[0]
    assert thread.ai_session_id in statement.compile().params.values()
    assert 'FOR UPDATE' in str(statement)


@pytest.mark.asyncio
async def test_inspection_job_does_not_offer_upfront_addons(context):
    c = context
    c.row.price_snapshot['pricing_mode'] = 'inspection'
    assert await addons.step(c.db, c.thread, c.row.to_dict(), 'instagram') is None
    c.owner.assert_not_awaited()


@pytest.mark.asyncio
async def test_no_options_does_not_introduce_an_empty_step(context):
    c = context
    c.svc.get_addons.return_value = {'options':[]}
    assert await addons.step(c.db, c.thread, c.row.to_dict(), 'whatsapp') is None


@pytest.mark.asyncio
async def test_retired_selected_addons_can_still_be_cleared(context):
    c = context
    await c.svc.set_addons(c.row.id, None, [{'mapping_id':c.option['service_option_mapping_id'], 'quantity':1}])
    c.svc.get_addons.return_value = {'options':[]}
    turn = await addons.step(c.db, c.thread, c.row.to_dict(), 'instagram')
    await addons.handle(c.db, c.thread, c.row.to_dict(), 'instagram', payload(turn, 'clear'))
    assert c.row.price_snapshot['selected_addons'] == []


@pytest.mark.asyncio
async def test_stale_confirm_button_cannot_bypass_addon_review(context):
    c = context
    await c.svc.set_addons(c.row.id, None, [{'mapping_id':c.option['service_option_mapping_id'], 'quantity':1}])
    executor = NS(_tool_confirm_home_service_booking=AsyncMock())
    result = await flow._confirm(c.db, c.thread, executor, c.row.to_dict())
    assert 'Review' in result[0]
    executor._tool_confirm_home_service_booking.assert_not_awaited()


def test_addon_menu_pages_fit_both_channels(context):
    c = context
    options = [{**c.option, 'service_option_mapping_id':str(uuid.uuid4()), 'name':f'Extra {i}'} for i in range(23)]
    for page in range(5):
        menu = addons._menu(c.row.to_dict(), options, page)
        assert len(menu.picker['rows']) <= 10
        assert len({r['id'] for r in menu.picker['rows']}) == len(menu.picker['rows'])


@pytest.mark.asyncio
async def test_chat_required_fields_use_shared_blueprint_resolver(monkeypatch):
    row = NS(offering_id=uuid.uuid4(), to_dict=lambda:{'id':str(uuid.uuid4())})
    result = MagicMock()
    result.scalars.return_value.first.return_value = row
    offering = NS(is_type_required=False, is_brand_required=False, requires_schedule=True)
    db = MagicMock(execute=AsyncMock(return_value=result), get=AsyncMock(return_value=offering))
    resolver = AsyncMock(return_value=['brand_id'])
    monkeypatch.setattr(HomeServiceChatbotBookingService, '_get_required_field_list', resolver)
    draft = await flow._draft(db, NS(ai_session_id=uuid.uuid4()))
    assert draft['required_fields'] == ['brand_id']
    resolver.assert_awaited_once_with(offering, row)


@pytest.mark.asyncio
async def test_unscheduled_workflow_does_not_query_slots():
    db = MagicMock()
    assert await pickers._slot_picker(db, {'required_fields':['city']}, uuid.uuid4(), None, 'instagram', 0) is None
    db.execute.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize('channel,size', [('instagram',900), ('whatsapp',4096)])
async def test_financial_summaries_are_chunked_not_truncated(monkeypatch, channel, size):
    calls = []
    async def post(url, token, payload):
        calls.append(payload['message']['text'] if channel == 'instagram' else payload['text']['body'])
        return {'sent':True}
    monkeypatch.setattr(meta_client, '_endpoint', lambda *args: ('test-url','test-token'))
    monkeypatch.setattr(meta_client, '_post', post)
    text = 'x' * (size * 2) + 'FINAL PRICE INR 500'
    result = await meta_client.send_text('test', text, channel=channel)
    assert result['sent'] and len(calls) == 3
    assert ''.join(calls) == text
    assert all(len(part) <= size for part in calls)


@pytest.mark.asyncio
@pytest.mark.parametrize('channel', ['whatsapp', 'instagram'])
async def test_flow_routes_to_addons_before_final_confirmation(context, monkeypatch, channel):
    c = context
    c.thread.channel = channel
    c.thread.customer_id = uuid.uuid4()
    c.thread.zipcode, c.thread.city = '140412', 'Test city'
    c.thread.pending_phone_ciphertext = None
    draft = {**c.row.to_dict(), 'preferred_date':'2026-09-10',
             'address_snapshot':{'address_line_1':'House 7 Test Road'}}
    monkeypatch.setattr(flow, '_serviceable_categories', AsyncMock(return_value=['home_services']))
    monkeypatch.setattr(pickers, 'build_picker', AsyncMock(return_value=None))
    executor = NS(customer_id=c.thread.customer_id, _tool_get_home_service_booking_summary=AsyncMock())
    turn = await flow._next_step(c.db, c.thread, executor, draft, channel, 0)
    assert any(r['id'].startswith('ao|') for r in turn.picker['rows'])
    executor._tool_get_home_service_booking_summary.assert_not_awaited()


@pytest.mark.asyncio
async def test_review_summary_lists_lines_and_edit_action(context):
    c = context
    await c.svc.set_addons(c.row.id, None, [{'mapping_id':c.option['service_option_mapping_id'], 'quantity':1}])
    c.row.price_snapshot['social_addons_reviewed'] = addons.token(c.row.to_dict())
    executor = NS(_tool_get_home_service_booking_summary=AsyncMock(return_value={'summary':{'booking_summary':{
        'offering_name':'Cleaning', 'price_estimate':c.row.price_snapshot}}}))
    turn = await flow._confirm_step(executor, c.row.to_dict(), c.thread)
    assert 'Extra cleaning' in turn.text and '25.0' in turn.text
    assert [r['title'] for r in turn.picker['rows']] == ['Confirm booking', 'Edit add-ons', 'Start over']


@pytest.mark.asyncio
async def test_incomplete_summary_does_not_offer_confirmation():
    executor = NS(_tool_get_home_service_booking_summary=AsyncMock(return_value={'summary':{'booking_summary':{
        'ready_for_confirmation':False, 'missing':['brand_id']}}}))
    turn = await flow._confirm_step(executor, {'id':str(uuid.uuid4())}, None)
    assert turn.picker is None and 'brand_id' in turn.text


@pytest.mark.asyncio
async def test_failed_summary_delivery_withholds_confirmation_buttons(monkeypatch):
    from app.engines.messaging_gateway.service import MessagingGatewayService
    from app.engines.messaging_gateway.meta_client import InboundMessage
    db = MagicMock(flush=AsyncMock(), commit=AsyncMock())
    thread = MagicMock()
    thread.id = uuid.uuid4()
    thread.opted_out = False
    thread.human_handoff = False
    thread.blocked_until = None
    thread.last_options = ['old-option']
    # Mid-conversation: recent enough that this message continues the
    # thread rather than opening a new one.
    thread.last_inbound_at = datetime.now(timezone.utc) - timedelta(minutes=5)
    gateway = MessagingGatewayService(db, channel_config={})
    gateway.get_or_create_thread = AsyncMock(return_value=thread)
    gateway.resolve_customer = AsyncMock(return_value=None)
    gateway._rate_limited = AsyncMock(return_value=False)
    gateway._advance = AsyncMock(return_value=('New total: INR 125', {
        'body':'Confirm?', 'rows':[{'id':'cf|yes', 'title':'Confirm'}],
        'list_button':'Choose', 'section_title':'Review'}))
    monkeypatch.setattr('app.engines.messaging_gateway.service.rate_limiter.check', AsyncMock(return_value=(True, None)))
    monkeypatch.setattr(meta_client, 'send_text', AsyncMock(return_value={'sent':False}))
    options = AsyncMock()
    monkeypatch.setattr(meta_client, 'send_options', options)
    result = await gateway.handle_inbound(InboundMessage(channel='instagram', provider_message_id='test-no-delivery',
        from_id='test-user', business_id='test-business', message_type='text', text='Review'))
    assert not result['reply_sent']
    options.assert_not_awaited()
    assert thread.last_options is None
