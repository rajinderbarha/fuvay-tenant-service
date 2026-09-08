import os
import uuid
from unittest.mock import AsyncMock, MagicMock
import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from app.engines.tenant_engine.hs_provider_directory_service import HomeServicesProviderDirectoryService


@pytest.mark.asyncio
async def test_roster_includes_members_without_logins_and_respects_assignment(monkeypatch):
    from app.engines.tenant_engine import provider_team_projection as projection
    monkeypatch.setattr(projection, "get_seat_usage", AsyncMock(return_value={"entitled_seats": 3, "used_seats": 1}))
    result = MagicMock()
    base = dict(id=uuid.uuid4(), user_id=None, full_name="Technician", member_type="technician", status="active", can_receive_assignment=True, availability_state="available", login_enabled=None, active_jobs=0)
    result.mappings.return_value.all.return_value = [base, {**base, "id": uuid.uuid4(), "member_type": "staff", "can_receive_assignment": False}]
    db = MagicMock(execute=AsyncMock(return_value=result))
    data = await projection.provider_team_projection(db, uuid.uuid4())
    assert data["total_staff"] == 2 and data["available_staff"] == 1
    assert data["staff"][0]["login_status"] == "Not created"
    assert data["technician_count"] == 1


@pytest.mark.asyncio
@pytest.mark.skipif(os.getenv("RUN_LOCAL_PROVIDER_DETAIL_TEST") != "1", reason="Local PostgreSQL integration")
async def test_all_admin_tabs_and_tenant_progress_use_same_saved_state():
    from app.config import get_settings
    from app.engines.vertical_catalog.home_services_setup_service import get_setup_overview
    url = make_url(get_settings().DATABASE_URL)
    assert url.host in {"localhost", "127.0.0.1", "::1"}
    engine = create_async_engine(url, echo=False)
    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            try:
                async with AsyncSession(bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint") as db:
                    tid = (await db.execute(text("SELECT id FROM tenants WHERE vertical='home_services' ORDER BY created_at DESC LIMIT 1"))).scalar_one()
                    service = HomeServicesProviderDirectoryService(db)
                    detail = await service.get_provider_detail(tid)
                    setup = await get_setup_overview(db, tid)
                    assert detail["profile_completion_percentage"] == setup["progress"]["percentage"]
                    if detail["enrollment_status"] != "active": assert detail["is_bookable"] is False
                    services = await service.get_provider_services(tid)
                    enabled = [s for s in services["services"] if s["is_active"] and s["is_enabled"]]
                    assert services["missing_price_config_count"] == sum(not s["price_configured"] for s in enabled)
                    assert "business_hours" in services and "schedule_exceptions" in services
                    team = await service.get_provider_team(tid)
                    assert team["total_staff"] == (await db.execute(text("SELECT count(*) FROM provider_team_members WHERE tenant_id=:tid AND deleted_at IS NULL"), {"tid":tid})).scalar_one()
                    finance = await service.get_provider_finance(tid)
                    assert finance["technician_seats"]["entitled"] == team["seat_usage"]["entitled_seats"]
                    await service.get_provider_quality(tid)
                    await service.get_provider_operations(tid)
                    activity = await service.get_provider_activity(tid)
                    assert all("uploaded_at" in d and "version" in d for d in activity["documents"])
            finally: await transaction.rollback()
    finally: await engine.dispose()
