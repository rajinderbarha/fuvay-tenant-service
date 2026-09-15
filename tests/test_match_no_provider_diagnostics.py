"""A failed provider match must leave its exclusion reasons in the logs.

Social chat shows only "No service is currently available in ZIP code <zip>"
after serviceability has already passed. The per-provider reason codes are
the only way to tell which matching gate excluded a covering provider.
"""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.engines.home_service_booking import service as booking_service
from app.engines.home_service_booking.constants import ERR_NO_PROVIDER_AVAILABLE
from app.engines.home_service_booking.service import HomeServiceChatbotBookingService
from app.exceptions import ServiceOSException


async def test_no_eligible_provider_logs_exclusion_reasons():
    db = MagicMock()
    db.get = AsyncMock(return_value=MagicMock(vertical_type="home_services"))
    master_service_id, job_type_id, brand_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    excluded = [{"provider_name": "Guramrit Home Services", "reason_code": "BRAND_NOT_SUPPORTED"}]
    no_match = {"signals": None, "score": None, "candidate_count": 1,
                "excluded_count": 1, "excluded_providers": excluded}

    with patch(
        "app.engines.home_service_booking.matching_engine.select_best_provider",
        AsyncMock(return_value=no_match),
    ), patch.object(booking_service, "logger") as logger:
        with pytest.raises(ServiceOSException) as exc_info:
            await HomeServiceChatbotBookingService(db=db).match_provider_and_price(
                category_id=uuid.uuid4(), master_service_id=master_service_id,
                city="BASSIPATHANA", zipcode="140412",
                brand_id=brand_id, job_type_id=job_type_id,
            )

    assert exc_info.value.error_code == ERR_NO_PROVIDER_AVAILABLE
    assert exc_info.value.detail == "No service is currently available in ZIP code 140412."
    logger.warning.assert_called_once()
    event, fields = logger.warning.call_args.args[0], logger.warning.call_args.kwargs
    assert event == "home_service.matching.no_eligible_provider"
    assert fields["excluded_providers"] == excluded
    assert fields["candidate_count"] == 1
    assert fields["zipcode"] == "140412"
    assert fields["master_service_id"] == str(master_service_id)
    assert fields["job_type_id"] == str(job_type_id)
    assert fields["brand_id"] == str(brand_id)
