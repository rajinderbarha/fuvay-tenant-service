from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
import uuid

import pytest

from app.engines.tenant_engine.hs_customer_directory_service import (
    HomeServicesCustomerDirectoryService,
)


@pytest.mark.asyncio
async def test_customer_complaints_tab_returns_tenant_scoped_rows() -> None:
    customer_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    complaint = SimpleNamespace(
        id=uuid.uuid4(), complaint_number="CMP-100", job_id=uuid.uuid4(),
        title="Cooling issue", complaint_type="service_quality",
        priority="normal", severity="medium", sla_status="on_time",
        status="open", created_at=now, updated_at=now,
    )
    count_result = MagicMock()
    count_result.scalar.return_value = 1
    rows_result = MagicMock()
    rows_result.scalars.return_value.all.return_value = [complaint]
    db = MagicMock()
    db.execute = AsyncMock(side_effect=[count_result, rows_result])

    result = await HomeServicesCustomerDirectoryService(db).get_customer_complaints(
        customer_id, tenant_id=tenant_id,
    )

    assert result["total"] == 1
    assert result["items"][0]["complaint_id"] == str(complaint.id)
    assert result["items"][0]["status"] == "open"
    assert db.execute.await_count == 2


def test_confirmed_job_value_includes_current_verified_invoice_status() -> None:
    source = Path(
        "app/engines/tenant_engine/hs_customer_directory_service.py"
    ).read_text(encoding="utf-8")

    assert source.count('ServiceInvoice.payment_status.in_(("verified", "paid"))') == 2
    assert 'ServiceInvoice.payment_status == "paid"' not in source
