"""Scoped, server-priced add-ons shared by booking and technician estimates."""
import uuid
from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy import select
from app.engines.admin_catalog.models import ServiceOptionMapping, MasterServiceOption, TenantSupportedServiceOption
from app.engines.admin_catalog.service_option_service import ServiceOptionService
from app.exceptions import ServiceOSException


def validate_mapping(mapping, *, service_id, job_type_id, actor):
    if actor not in {'customer', 'technician'}:
        raise ServiceOSException('ADDON_ACTOR_NOT_ALLOWED', 'Unknown add-on selection role.', status_code=422)
    if (not mapping or mapping.deleted_at or mapping.status != 'active' or mapping.usage == 'DISABLED'
        or mapping.master_service_id != service_id or not job_type_id or mapping.job_type_id != job_type_id):
        raise ServiceOSException('ADDON_NOT_AVAILABLE', 'This add-on is not available for this service and job type.', status_code=422)
    permitted = (mapping.customer_selectable and mapping.available_before_booking) if actor == 'customer' else (mapping.technician_selectable and mapping.available_after_inspection)
    if not permitted:
        raise ServiceOSException('ADDON_ACTOR_NOT_ALLOWED', 'This add-on is not selectable at this stage.', status_code=422)


async def resolve_addons(db, *, tenant_id, service_id, job_type_id, selections, actor='customer'):
    if not isinstance(selections, list) or len(selections) > 50:
        raise ServiceOSException('INVALID_ADDONS', 'Provide at most 50 add-ons.', status_code=422)
    lines, seen = [], set()
    for item in selections:
        try:
            mapping_id = uuid.UUID(str(item['mapping_id']))
            quantity = item.get('quantity', 1)
            if type(quantity) is not int or quantity <= 0 or mapping_id in seen:
                raise ValueError()
        except (KeyError, TypeError, ValueError):
            raise ServiceOSException('INVALID_ADDONS', 'Select each add-on once with a positive whole quantity.', status_code=422)
        seen.add(mapping_id)
        mapping = await db.get(ServiceOptionMapping, mapping_id)
        validate_mapping(mapping, service_id=service_id, job_type_id=job_type_id, actor=actor)
        option = await db.get(MasterServiceOption, mapping.service_option_id)
        if not option or option.status != 'active':
            raise ServiceOSException('ADDON_NOT_AVAILABLE', 'The add-on has been retired.', status_code=422)
        row = await db.scalar(select(TenantSupportedServiceOption).where(
            TenantSupportedServiceOption.tenant_id == tenant_id,
            TenantSupportedServiceOption.service_option_mapping_id == mapping_id,
            TenantSupportedServiceOption.deleted_at.is_(None), TenantSupportedServiceOption.status == 'active'))
        if not row:
            raise ServiceOSException('ADDON_NOT_AVAILABLE', 'The provider does not offer this add-on.', status_code=422)
        now = datetime.now(timezone.utc)
        if (row.effective_from and row.effective_from > now) or (row.effective_to and row.effective_to < now):
            raise ServiceOSException('ADDON_NOT_AVAILABLE', 'The provider add-on price is outside its validity period.', status_code=422)
        if ((not mapping.quantity_supported and quantity != 1) or
            (mapping.quantity_supported and (quantity < (mapping.minimum_quantity or 1) or
             (mapping.maximum_quantity is not None and quantity > mapping.maximum_quantity)))):
            raise ServiceOSException('INVALID_ADDON_QUANTITY', 'Quantity is outside the permitted range.', status_code=422)
        if mapping.affects_estimate:
            # A price range is not permission to charge its minimum as a fixed price.
            if row.pricing_model not in ('FIXED', 'PER_UNIT'):
                raise ServiceOSException('ADDON_ESTIMATE_REQUIRED', 'This add-on needs an approved estimate and cannot be charged upfront.', status_code=422)
            price = await ServiceOptionService(db, None, None, 'addon-runtime').resolve_tenant_option_price(tenant_id, mapping_id, quantity)
            amounts = [Decimal(str(price[key])) for key in ('unit_price', 'total')]
            if price['currency'] != 'INR' or any(not value.is_finite() or value < 0 for value in amounts):
                raise ServiceOSException('INVALID_ADDON_PRICE', 'A valid INR price is required.', status_code=422)
        else:
            price = {'unit_price': '0.00', 'total': '0.00'}
        lines.append({'mapping_id': str(mapping_id), 'name': option.name, 'quantity': quantity,
                      'unit_price': price['unit_price'] if mapping.affects_estimate else '0.00',
                      'total': price['total'] if mapping.affects_estimate else '0.00', 'currency': 'INR'})
    return lines


async def validate_frozen_addons(db, draft):
    snapshot = draft.price_snapshot or {}
    selected = snapshot.get('selected_addons', [])
    if not selected:
        return
    lines = await resolve_addons(db, tenant_id=draft.selected_tenant_id, service_id=draft.offering_id,
                                job_type_id=draft.job_type_id, selections=selected)
    if lines != snapshot.get('addon_lines'):
        raise ServiceOSException('ADDON_PRICE_CHANGED', 'Add-on availability or price changed. Review the price again before confirming.', status_code=409)
