from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.engines.global_services.models import GlobalServiceLead, PlatformGlobalService
from app.engines.global_services.service import GlobalServicesService
from app.exceptions import NotFoundException, ServiceOSException


@pytest.mark.asyncio
async def test_customer_lead_is_created_for_active_nationwide_service() -> None:
    service_id = uuid.uuid4()
    customer_id = uuid.uuid4()
    global_service = PlatformGlobalService(
        id=service_id,
        name="Web Development",
        display_order=1,
        is_active=True,
    )
    db = MagicMock()
    db.get = AsyncMock(return_value=global_service)
    db.flush = AsyncMock()

    result = await GlobalServicesService(db).create_lead(
        {
            "global_service_id": str(service_id),
            "name": "QA Customer",
            "phone": "9876543210",
            "zipcode": "140412",
            "message": "Build a customer portal",
        },
        customer_id=customer_id,
    )

    lead = db.add.call_args.args[0]
    assert isinstance(lead, GlobalServiceLead)
    assert lead.global_service_id == service_id
    assert lead.customer_id == customer_id
    assert lead.zipcode == "140412"
    assert lead.status == "new"
    assert result["global_service_id"] == str(service_id)


@pytest.mark.asyncio
async def test_customer_cannot_submit_to_inactive_global_service() -> None:
    service_id = uuid.uuid4()
    global_service = PlatformGlobalService(
        id=service_id,
        name="Retired service",
        display_order=99,
        is_active=False,
    )
    db = MagicMock()
    db.get = AsyncMock(return_value=global_service)

    with pytest.raises(NotFoundException):
        await GlobalServicesService(db).create_lead(
            {
                "global_service_id": str(service_id),
                "name": "QA Customer",
                "phone": "9876543210",
            },
            customer_id=uuid.uuid4(),
        )

    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_customer_lead_requires_name_and_phone() -> None:
    service_id = uuid.uuid4()
    global_service = PlatformGlobalService(
        id=service_id,
        name="Mobile App Development",
        display_order=2,
        is_active=True,
    )
    db = MagicMock()
    db.get = AsyncMock(return_value=global_service)

    with pytest.raises(ServiceOSException) as error:
        await GlobalServicesService(db).create_lead(
            {"global_service_id": str(service_id), "name": ""},
            customer_id=uuid.uuid4(),
        )

    assert error.value.error_code == "GLOBAL_SERVICE_LEAD_FIELDS_REQUIRED"
    db.add.assert_not_called()
