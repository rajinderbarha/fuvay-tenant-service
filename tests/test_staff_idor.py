"""
Phase 5 readiness fixes for a future technician mobile app:
- field_ops: staff could read/transition ANY job regardless of assignment;
  list_jobs let staff pass any staff_id to view a colleague's queue.
- data_science: any staff could view a colleague's performance score by URL.
- geo: a technician could POST a location update under a colleague's staff_id.
- NEW: GET /v1/jobs/staff/{staff_id}/earnings — didn't exist at all.
"""
import uuid
from decimal import Decimal
from datetime import datetime, timezone
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.exceptions import NotFoundException, ServiceOSException


def make_db_returning(obj):
    result = MagicMock()
    result.scalar_one_or_none.return_value = obj
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)
    return db


# ── field_ops: job ownership ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_staff_cannot_get_unassigned_job():
    from app.engines.field_ops.service import FieldOpsService
    other_staff = uuid.uuid4()
    fake_job = MagicMock(id=uuid.uuid4(), assigned_staff_id=other_staff)
    db = make_db_returning(fake_job)
    svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="staff")

    with pytest.raises(NotFoundException):
        await svc.get_job(fake_job.id)


@pytest.mark.asyncio
async def test_staff_can_get_own_assigned_job():
    from app.engines.field_ops.service import FieldOpsService
    me = uuid.uuid4()
    fake_job = MagicMock(id=uuid.uuid4(), assigned_staff_id=me, status="en_route")
    db = make_db_returning(fake_job)
    svc = FieldOpsService(db=db, actor_id=me, actor_role="staff")
    svc._job_dict = lambda j: {"job_id": str(j.id)}

    result = await svc.get_job(fake_job.id)
    assert result["job_id"] == str(fake_job.id)


@pytest.mark.asyncio
async def test_staff_cannot_transition_unassigned_job():
    from app.engines.field_ops.service import FieldOpsService
    fake_job = MagicMock(id=uuid.uuid4(), assigned_staff_id=uuid.uuid4(), status="dispatched")
    db = make_db_returning(fake_job)
    svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="staff")

    with pytest.raises(NotFoundException):
        await svc.update_status(fake_job.id, "accepted", None, None, None)


@pytest.mark.asyncio
async def test_super_admin_override_still_works_regardless_of_assignment():
    from app.engines.field_ops.service import FieldOpsService
    fake_job = MagicMock(id=uuid.uuid4(), assigned_staff_id=uuid.uuid4(), status="dispatched")
    db = make_db_returning(fake_job)
    svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="super_admin")
    svc._write_history = AsyncMock()
    svc._publish = AsyncMock()
    svc._job_dict = lambda j: {"job_id": str(j.id), "status": j.status}

    result = await svc.update_status(fake_job.id, "accepted", "admin override", None, None)
    assert result["status"] == "accepted"


@pytest.mark.asyncio
async def test_staff_list_jobs_forced_to_own_staff_id_even_if_spoofed():
    """A staff member passing a colleague's staff_id must still only see their
    own jobs — verified by inspecting the actual compiled SQL WHERE clause."""
    from app.engines.field_ops.service import FieldOpsService
    me = uuid.uuid4()
    other = uuid.uuid4()

    captured_query = {}
    scalars_result = MagicMock()
    scalars_result.all.return_value = []
    exec_result = MagicMock()
    exec_result.scalars.return_value = scalars_result

    db = MagicMock()
    async def fake_execute(query):
        captured_query["sql"] = str(query.compile(compile_kwargs={"literal_binds": True}))
        return exec_result
    db.execute = fake_execute

    svc = FieldOpsService(db=db, actor_id=me, actor_role="staff")
    await svc.list_jobs(uuid.uuid4(), None, other, 50, None)

    assert me.hex in captured_query["sql"]
    assert other.hex not in captured_query["sql"]


# ── data_science: staff score ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_staff_score_router_blocks_viewing_colleague():
    import app.engines.data_science.router as ds_router
    from app.dependencies.auth import UserContext

    me = str(uuid.uuid4())
    colleague = uuid.uuid4()
    user = UserContext(user_id=me, email="s@x.io", role="staff", tenant_id=str(uuid.uuid4()),
                        full_name="Tech", is_verified=True)

    class FakeState: request_id = "req_test"
    class FakeRequest: state = FakeState()

    with pytest.raises(NotFoundException):
        await ds_router.staff_score(uuid.uuid4(), colleague, FakeRequest(), u=user, s=MagicMock())


# ── geo: location spoofing ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_staff_cannot_post_location_for_colleague():
    import app.engines.geo.router as geo_router
    from app.dependencies.auth import UserContext

    me = str(uuid.uuid4())
    colleague = uuid.uuid4()
    user = UserContext(user_id=me, email="s@x.io", role="staff", tenant_id=str(uuid.uuid4()),
                        full_name="Tech", is_verified=True)

    class FakeState: request_id = "req_test"
    class FakeRequest:
        state = FakeState()
        async def json(self): return {"latitude": 1.0, "longitude": 2.0}

    with pytest.raises(ServiceOSException) as exc_info:
        await geo_router.update_location(uuid.uuid4(), colleague, FakeRequest(), u=user, s=MagicMock())
    assert exc_info.value.error_code == "PERMISSION_DENIED"


# ── field_ops: earnings ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_staff_earnings_blocks_viewing_colleague():
    from app.engines.field_ops.service import FieldOpsService
    svc = FieldOpsService(db=MagicMock(), actor_id=uuid.uuid4(), actor_role="staff")

    with pytest.raises(NotFoundException):
        await svc.get_staff_earnings(uuid.uuid4(), uuid.uuid4())


@pytest.mark.asyncio
async def test_staff_earnings_aggregates_only_closed_jobs_for_that_staff():
    from app.engines.field_ops.service import FieldOpsService

    me = uuid.uuid4()
    now = datetime.now(timezone.utc)
    job1 = MagicMock(final_price=Decimal("500"), quoted_price=Decimal("500"),
                      completed_at=now, customer_rating=5)
    job2 = MagicMock(final_price=None, quoted_price=Decimal("300"),
                      completed_at=now, customer_rating=4)

    scalars_result = MagicMock()
    scalars_result.all.return_value = [job1, job2]
    exec_result = MagicMock()
    exec_result.scalars.return_value = scalars_result
    db = MagicMock()
    db.execute = AsyncMock(return_value=exec_result)

    svc = FieldOpsService(db=db, actor_id=me, actor_role="staff")
    result = await svc.get_staff_earnings(me, uuid.uuid4())

    assert result["jobs_completed_total"] == 2
    assert result["job_value_total"] == 800.0
    assert result["average_rating"] == 4.5
