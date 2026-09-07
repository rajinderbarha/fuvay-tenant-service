"""Deterministic, session-scoped add-on review shared by both Meta channels."""
import hashlib
import json
import uuid

from fastapi import HTTPException
from sqlalchemy import select

from app.exceptions import ServiceOSException
from app.engines.home_service_booking.models import HomeServiceBookingDraft
from app.engines.home_service_booking.service import HomeServiceChatbotBookingService
from app.engines.admin_catalog.addon_runtime import validate_frozen_addons
from app.engines.messaging_gateway.constants import PICK_ADDON, PICKER_SEP


def token(draft):
    price = draft.get('price_snapshot') or {}
    data = [str(draft.get('id')), str(draft.get('selected_tenant_id')), str(draft.get('job_type_id')),
            price.get('selected_addons', []), price.get('addon_lines', []), price.get('customer_total')]
    return hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()[:16]


def needs_review(draft):
    price = draft.get('price_snapshot') or {}
    return bool(price.get('selected_addons')) and price.get('social_addons_reviewed') != token(draft)


async def _owned(db, thread, draft_id):
    # A WhatsApp sender may not yet have a customer account. The verified
    # thread/session, never a supplied draft ID alone, owns that draft.
    row = (await db.execute(select(HomeServiceBookingDraft).where(
        HomeServiceBookingDraft.id == uuid.UUID(str(draft_id)),
        HomeServiceBookingDraft.ai_session_id == thread.ai_session_id,
    ).with_for_update().execution_options(populate_existing=True))).scalar_one_or_none()
    if row is None or not thread.ai_session_id:
        raise ServiceOSException('ADDON_CHAT_ACCESS_DENIED', 'This booking is not part of your current conversation.', status_code=403)
    if thread.customer_id and row.customer_id and row.customer_id != thread.customer_id:
        raise ServiceOSException('ADDON_CHAT_ACCESS_DENIED', 'This booking belongs to another customer.', status_code=403)
    HomeServiceChatbotBookingService(db)._assert_not_terminal(row)
    return row


def _id(draft, action, *args):
    return PICKER_SEP.join([PICK_ADDON, str(draft['id']), token(draft), action, *map(str, args)])


def _menu(draft, options, page=0, notice=None):
    from app.engines.messaging_gateway.flow import Turn
    price = draft.get('price_snapshot') or {}
    selected = {item['mapping_id']: item['quantity'] for item in price.get('selected_addons', [])}
    lines = ['Optional add-ons — prices set by your provider.']
    lines.extend(f"{item['name']} × {item['quantity']}: INR {item['total']}" for item in price.get('addon_lines', []))
    lines.append(f"Updated booking total: INR {price.get('customer_total', '—')} (before any emergency surcharge shown in the final summary).")
    if notice:
        lines.insert(0, notice)
    page = max(0, min(page, max(0, (len(options) - 1) // 5)))
    rows = []
    for option in options[page * 5:(page + 1) * 5]:
        mapping_id = option['service_option_mapping_id']
        quantity = selected.get(mapping_id, 0)
        rows.append({'id': _id(draft, 'choose', mapping_id), 'title': option['name'],
            'description': f"INR {option['unit_price']} each · Selected: {quantity}"})
    if page:
        rows.append({'id': _id(draft, 'page', page - 1), 'title': 'Previous add-ons'})
    if (page + 1) * 5 < len(options):
        rows.append({'id': _id(draft, 'page', page + 1), 'title': 'More add-ons'})
    if selected:
        rows.append({'id': _id(draft, 'clear'), 'title': 'Remove all add-ons'})
    rows.append({'id': _id(draft, 'done'), 'title': 'Accept total & next' if selected else 'Continue without extras'})
    return Turn('\n'.join(lines), {'body': 'Choose an add-on, or continue with the displayed total.',
        'rows': rows, 'list_button': 'Review add-ons', 'section_title': 'Provider add-ons'})


async def step(db, thread, draft, channel, *, force=False, page=0, notice=None):
    price = (draft or {}).get('price_snapshot') or {}
    if price.get('pricing_mode') != 'fixed' or not draft.get('selected_tenant_id'):
        return None  # Inspection extras belong in the customer-approved quote.
    if not force and price.get('social_addons_reviewed') == token(draft):
        return None
    svc = HomeServiceChatbotBookingService(db)
    await _owned(db, thread, draft['id'])
    catalog = await svc.get_addons(uuid.UUID(str(draft['id'])), thread.customer_id)
    if not catalog['options'] and not price.get('selected_addons'):
        return None
    return _menu(draft, catalog['options'], page, notice)


async def handle(db, thread, draft, channel, payload):
    from app.engines.messaging_gateway.flow import Turn
    if not draft:
        return Turn('That add-on menu has expired. Start with your current booking.')
    parts = payload.split(PICKER_SEP)
    if len(parts) < 3 or parts[0] != str(draft['id']):
        return Turn('That add-on menu belongs to an older booking. Please use the current menu.')
    try:
        row = await _owned(db, thread, draft['id'])
        current = row.to_dict()
        if parts[1] != token(current):
            return await step(db, thread, current, channel, force=True,
                notice='Your selection or price has changed. Please use this updated menu.')
        action = parts[2]
        if (current.get('price_snapshot') or {}).get('pricing_mode') != 'fixed':
            return Turn('Extras for this service need a customer-approved inspection estimate.')
        svc = HomeServiceChatbotBookingService(db)
        catalog = await svc.get_addons(row.id, thread.customer_id)
        options = catalog['options']
        selected = {item['mapping_id']: item['quantity'] for item in (row.price_snapshot or {}).get('selected_addons', [])}
        if action == 'page' and len(parts) == 4:
            return _menu(current, options, int(parts[3]))
        if action == 'done' and len(parts) == 3:
            try:
                await validate_frozen_addons(db, row)
            except ServiceOSException as exc:
                if exc.error_code != 'ADDON_PRICE_CHANGED':
                    raise
                await svc.set_addons(row.id, thread.customer_id,
                    [{'mapping_id': key, 'quantity': value} for key, value in selected.items()])
                return await step(db, thread, row.to_dict(), channel, force=True,
                    notice='The provider price changed. Review and accept the new total.')
            await svc.confirm_price_choice(row.id, 'standard', thread.customer_id)
            row.price_snapshot = {**row.price_snapshot, 'social_addons_reviewed': token(row.to_dict())}
            await db.commit()
            return None
        if action == 'clear' and len(parts) == 3:
            selected = {}
        elif action in {'choose', 'set'} and len(parts) in {4, 5}:
            mapping_id = parts[3]
            option = next((o for o in options if o['service_option_mapping_id'] == mapping_id), None)
            if action == 'choose' and option and mapping_id in selected:
                quantity = selected[mapping_id]
                rows = []
                if option.get('quantity_supported'):
                    if option.get('maximum_quantity') is None or quantity < option['maximum_quantity']:
                        rows.append({'id': _id(current, 'set', mapping_id, quantity + 1), 'title': 'Increase quantity'})
                    if quantity > (option.get('minimum_quantity') or 1):
                        rows.append({'id': _id(current, 'set', mapping_id, quantity - 1), 'title': 'Decrease quantity'})
                rows.extend([{'id': _id(current, 'set', mapping_id, 0), 'title': 'Remove add-on'},
                             {'id': _id(current, 'page', 0), 'title': 'Back to add-ons'}])
                return Turn(f"{option['name']} · {quantity} × INR {option['unit_price']}",
                    {'body': 'Change quantity or remove this add-on.', 'rows': rows,
                     'list_button': 'Change add-on', 'section_title': 'Quantity'})
            quantity = int(parts[4]) if action == 'set' and len(parts) == 5 else (
                (option.get('minimum_quantity') or 1) if option and option.get('quantity_supported') else 1)
            if quantity == 0 and mapping_id in selected:
                selected.pop(mapping_id)
            elif option:
                selected[mapping_id] = quantity
            else:
                raise ServiceOSException('ADDON_NOT_AVAILABLE', 'This add-on is no longer available.', status_code=422)
        else:
            return Turn('Please choose an action from the current add-on menu.')
        await svc.set_addons(row.id, thread.customer_id,
            [{'mapping_id': key, 'quantity': value} for key, value in selected.items()])
        return _menu(row.to_dict(), options, notice='Selection updated. Please review the new total.')
    except (ServiceOSException, HTTPException, ValueError) as exc:
        # Domain failures remain recoverable; never turn one into acceptance.
        message = getattr(exc, 'message', None) or getattr(exc, 'detail', None) or 'Please use the current add-on menu.'
        if 'options' in locals() and getattr(exc, 'error_code', '') != 'ADDON_CHAT_ACCESS_DENIED':
            return _menu(row.to_dict(), options, notice=str(message))
        return Turn(str(message))
