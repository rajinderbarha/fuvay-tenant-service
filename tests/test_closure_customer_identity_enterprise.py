from __future__ import annotations

import uuid
from datetime import date
from types import SimpleNamespace

import pytest

from app.engines.auth.admin_customers_router import _row_to_dict
from app.engines.provider_portal.router import _closure_job_impact


class _Rows:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows


class _DB:
    def __init__(self, rows):
        self.rows = rows
        self.params = None

    async def execute(self, _query, params):
        self.params = params
        return _Rows(self.rows)


@pytest.mark.asyncio
async def test_closure_impact_protects_started_and_preserves_prestart_jobs():
    rows = [
        SimpleNamespace(
            id=uuid.uuid4(), job_number="JOB-1", status="assigned",
            scheduled_time_window="10:00-12:00", assigned_staff_id=uuid.uuid4(),
            sla_breached_at=None,
        ),
        SimpleNamespace(
            id=uuid.uuid4(), job_number="JOB-2", status="inspection_started",
            scheduled_time_window="12:00-14:00", assigned_staff_id=uuid.uuid4(),
            sla_breached_at=object(),
        ),
    ]
    db = _DB(rows)

    impact = await _closure_job_impact(db, uuid.uuid4(), date(2026, 9, 28))

    assert impact["total_jobs"] == 2
    assert impact["protected_started_jobs"] == 1
    assert impact["pre_start_jobs"] == 1
    assert impact["requires_acknowledgement"] is True
    assert impact["policy"] == "honor_existing"
    assert impact["jobs"][1]["sla_breached"] is True


def test_admin_customer_never_exposes_internal_email_and_projects_channels():
    row = SimpleNamespace(
        id=uuid.uuid4(), full_name="Social Customer", phone="+919000000000",
        email="customer_ig_old@serviceos.internal", is_active=True,
        account_status="active", city="", district="", state="", zipcode="",
        health_band="new", total_bookings=0, completed_bookings=0,
        cancelled_bookings=0, complaints_count=0, reviews_count=0,
        average_rating=None, tenant_count=0, last_tenant_name="",
        last_booking_at=None, created_at=None, instagram_username="rajinderbarha",
        whatsapp_number="+919000000000",
        channels=[{"channel": "instagram", "username": "rajinderbarha"}],
        user_meta={"registration_source": "customer_app"}, customer_app_seen=True,
    )

    result = _row_to_dict(row)

    assert result["email"] == ""
    assert result["instagram_username"] == "rajinderbarha"
    assert {item["channel"] for item in result["channels"]} == {"instagram", "customer_app"}
    assert result["login_identifier"] == "phone"
