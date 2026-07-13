"""FINAL-L5-05AA — Export Rate Limit, Concurrency, Idempotency and Abuse
Protection Certification.

Runtime inventory at sprint start found the Enterprise Export creation
endpoint (`POST /v1/enterprise/exports`) had ZERO abuse-protection
controls despite the platform already having proven, reusable
infrastructure for exactly this purpose:

- `app.core.security.rate_limiter` (Redis sliding-window, atomic, already
  used by `platform_commerce.service.initiate_deposit`) had an
  `"api:export"` policy (5/hour) **already defined** in `RATE_LIMITS` but
  never actually called from `create_export` (confirmed via `git grep` --
  0 references anywhere in `app/engines/enterprise_grid/`).
- `app.core.security.idempotency_store` (generic `X-Idempotency-Key`
  pattern, 24h TTL) was similarly never wired in.
- No concurrent-job-count check existed at all -- an actor could submit
  unlimited simultaneous export jobs.
- No bound existed on `columns` count, selected-ID array length inside
  `filters`, or date-range width.

This sprint wires the existing rate limiter in, adds a new
idempotency-key column (migration 136) scoped per-actor via a partial
unique index, adds an atomic (Postgres advisory-lock-protected)
concurrent-job limit, and adds payload-bound validation -- reusing
established platform primitives rather than building parallel
infrastructure.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import get_settings
from app.engines.enterprise_grid.constants import (
    EXPORT_MAX_COLUMNS, EXPORT_MAX_SELECTED_IDS, EXPORT_MAX_DATE_RANGE_DAYS,
    EXPORT_MAX_CONCURRENT_JOBS_PER_ACTOR,
    ERR_EXPORT_FIELD_LIMIT, ERR_EXPORT_SELECTED_ID_LIMIT,
    ERR_EXPORT_DATE_RANGE_EXCEEDED, ERR_EXPORT_IDEMPOTENCY_CONFLICT,
    ERR_EXPORT_CONCURRENT_JOB_LIMIT,
)
from app.engines.enterprise_grid.services import ExportService


def _mock_db(active_count: int = 0, existing_job=None):
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    result = MagicMock()
    result.scalar_one.return_value = active_count
    result.scalars.return_value.first.return_value = existing_job
    db.execute = AsyncMock(return_value=result)
    return db


class TestPayloadBoundValidation:
    """Part 6/20/22/23: bounded payload, rejected before any DB write."""

    def test_field_count_limit_constant(self):
        assert EXPORT_MAX_COLUMNS > 0

    def test_selected_id_limit_constant(self):
        assert EXPORT_MAX_SELECTED_IDS > 0

    def test_date_range_limit_constant(self):
        assert EXPORT_MAX_DATE_RANGE_DAYS > 0

    def test_too_many_columns_rejected(self):
        svc = ExportService()
        columns = [f"col_{i}" for i in range(EXPORT_MAX_COLUMNS + 1)]
        with pytest.raises(ValueError, match=ERR_EXPORT_FIELD_LIMIT):
            svc._validate_payload_bounds(columns, {})

    def test_exactly_at_column_limit_passes(self):
        svc = ExportService()
        columns = [f"col_{i}" for i in range(EXPORT_MAX_COLUMNS)]
        svc._validate_payload_bounds(columns, {})  # must not raise

    def test_too_many_selected_ids_rejected(self):
        svc = ExportService()
        ids = [str(uuid.uuid4()) for _ in range(EXPORT_MAX_SELECTED_IDS + 1)]
        with pytest.raises(ValueError, match=ERR_EXPORT_SELECTED_ID_LIMIT):
            svc._validate_payload_bounds([], {"selected_ids": ids})

    def test_selected_ids_at_limit_passes(self):
        svc = ExportService()
        ids = [str(uuid.uuid4()) for _ in range(EXPORT_MAX_SELECTED_IDS)]
        svc._validate_payload_bounds([], {"ids": ids})  # must not raise

    def test_oversized_date_range_rejected(self):
        svc = ExportService()
        too_wide = {
            "date_from": "2020-01-01T00:00:00Z",
            "date_to": "2025-01-01T00:00:00Z",
        }
        with pytest.raises(ValueError, match=ERR_EXPORT_DATE_RANGE_EXCEEDED):
            svc._validate_payload_bounds([], too_wide)

    def test_date_range_within_limit_passes(self):
        svc = ExportService()
        ok_range = {"created_from": "2025-01-01T00:00:00Z", "created_to": "2025-06-01T00:00:00Z"}
        svc._validate_payload_bounds([], ok_range)  # must not raise

    def test_malformed_dates_do_not_crash_bound_check(self):
        # A malformed date is the filter-registry validation layer's
        # concern (a separate, pre-existing check) -- the bound-check must
        # not itself raise an unhandled exception on bad input.
        svc = ExportService()
        svc._validate_payload_bounds([], {"date_from": "not-a-date", "date_to": "also-not-a-date"})

    def test_field_order_does_not_change_fingerprint(self):
        # Mission Part 10 rule 3: "field order does not change fingerprint."
        svc = ExportService()
        fp1 = svc._fingerprint("admin_service_jobs", {"status": "completed", "city": "Delhi"},
                                ["a", "b", "c"], "csv")
        fp2 = svc._fingerprint("admin_service_jobs", {"city": "Delhi", "status": "completed"},
                                ["c", "a", "b"], "csv")
        assert fp1 == fp2

    def test_different_payload_changes_fingerprint(self):
        svc = ExportService()
        fp1 = svc._fingerprint("admin_service_jobs", {"status": "completed"}, ["a"], "csv")
        fp2 = svc._fingerprint("admin_service_jobs", {"status": "cancelled"}, ["a"], "csv")
        assert fp1 != fp2


class TestIdempotencyUnit:
    """Part 9/10/39: same key+payload -> replay; same key+different payload -> conflict."""

    @pytest.mark.asyncio
    async def test_no_key_always_creates_new_job(self):
        svc = ExportService()
        db = _mock_db(active_count=0, existing_job=None)
        with patch("app.engines.enterprise_grid.filter_registry.EnterpriseFilterRegistry.get_allowed_export_fields",
                   return_value=["status"]), \
             patch("app.engines.enterprise_grid.filter_registry.EnterpriseFilterRegistry.validate_filter",
                   return_value=True):
            job, is_replay = await svc.create_export_job(
                db, uuid.uuid4(), None, "admin_service_jobs",
                filters={}, columns=["status"], idempotency_key=None,
            )
        assert is_replay is False
        db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_same_key_same_payload_is_replay_no_new_job(self):
        svc = ExportService()
        actor_id = uuid.uuid4()
        existing = MagicMock()
        existing.resource_key = "admin_service_jobs"
        existing.filters = {"status": "completed"}
        existing.columns = ["status"]
        existing.export_format = "csv"
        db = _mock_db(active_count=0, existing_job=existing)
        with patch("app.engines.enterprise_grid.filter_registry.EnterpriseFilterRegistry.get_allowed_export_fields",
                   return_value=["status"]), \
             patch("app.engines.enterprise_grid.filter_registry.EnterpriseFilterRegistry.validate_filter",
                   return_value=True):
            job, is_replay = await svc.create_export_job(
                db, actor_id, None, "admin_service_jobs",
                filters={"status": "completed"}, columns=["status"],
                idempotency_key="client-key-123",
            )
        assert is_replay is True
        assert job is existing
        db.add.assert_not_called()  # no new row created for a replay

    @pytest.mark.asyncio
    async def test_same_key_different_payload_raises_conflict(self):
        svc = ExportService()
        existing = MagicMock()
        existing.resource_key = "admin_service_jobs"
        existing.filters = {"status": "completed"}
        existing.columns = ["status"]
        existing.export_format = "csv"
        db = _mock_db(active_count=0, existing_job=existing)
        with patch("app.engines.enterprise_grid.filter_registry.EnterpriseFilterRegistry.get_allowed_export_fields",
                   return_value=["status"]), \
             patch("app.engines.enterprise_grid.filter_registry.EnterpriseFilterRegistry.validate_filter",
                   return_value=True):
            with pytest.raises(ValueError, match=ERR_EXPORT_IDEMPOTENCY_CONFLICT):
                await svc.create_export_job(
                    db, uuid.uuid4(), None, "admin_service_jobs",
                    filters={"status": "cancelled"},  # different payload, same key
                    columns=["status"], idempotency_key="client-key-123",
                )


class TestConcurrentJobLimitUnit:
    @pytest.mark.asyncio
    async def test_at_limit_rejects_new_job(self):
        svc = ExportService()
        db = _mock_db(active_count=EXPORT_MAX_CONCURRENT_JOBS_PER_ACTOR, existing_job=None)
        with patch("app.engines.enterprise_grid.filter_registry.EnterpriseFilterRegistry.get_allowed_export_fields",
                   return_value=["status"]), \
             patch("app.engines.enterprise_grid.filter_registry.EnterpriseFilterRegistry.validate_filter",
                   return_value=True):
            with pytest.raises(ValueError, match=ERR_EXPORT_CONCURRENT_JOB_LIMIT):
                await svc.create_export_job(
                    db, uuid.uuid4(), None, "admin_service_jobs",
                    filters={}, columns=["status"],
                )
        db.add.assert_not_called()  # mission rule: denial creates no job

    @pytest.mark.asyncio
    async def test_below_limit_allows_job(self):
        svc = ExportService()
        db = _mock_db(active_count=EXPORT_MAX_CONCURRENT_JOBS_PER_ACTOR - 1, existing_job=None)
        with patch("app.engines.enterprise_grid.filter_registry.EnterpriseFilterRegistry.get_allowed_export_fields",
                   return_value=["status"]), \
             patch("app.engines.enterprise_grid.filter_registry.EnterpriseFilterRegistry.validate_filter",
                   return_value=True):
            job, is_replay = await svc.create_export_job(
                db, uuid.uuid4(), None, "admin_service_jobs",
                filters={}, columns=["status"],
            )
        db.add.assert_called_once()


class TestRouterDecisionOrder:
    """Part 7: resource/permission/scope checks must precede rate-limit and
    job creation -- static ordering guard (matches the established
    FINAL-L5-05R/05T pattern)."""

    def _block(self) -> str:
        from pathlib import Path
        src = (Path(__file__).parent.parent / "app/engines/enterprise_grid/router.py").read_text(encoding="utf-8")
        start = src.index("async def create_export(")
        end = src.index("async def list_exports(", start)
        return src[start:end]

    def test_resource_exists_check_precedes_rate_limit(self):
        block = self._block()
        idx_resource = block.index("resource_exists(body.resource_key)")
        idx_rate = block.index("rate_limiter.check_and_raise(")
        assert idx_resource < idx_rate

    def test_permission_check_precedes_rate_limit(self):
        block = self._block()
        idx_perm = block.index("required_export_permission(body.resource_key)")
        idx_rate = block.index("rate_limiter.check_and_raise(")
        assert idx_perm < idx_rate

    def test_rate_limit_precedes_job_creation(self):
        block = self._block()
        idx_rate = block.index("rate_limiter.check_and_raise(")
        idx_create = block.index("_export.create_export_job(")
        assert idx_rate < idx_create

    def test_rate_limiter_uses_existing_api_export_policy(self):
        block = self._block()
        assert 'limit_type="api:export"' in block

    def test_idempotency_key_header_extracted(self):
        block = self._block()
        assert "X-Idempotency-Key" in block


@pytest.mark.skipif(
    __import__("os").environ.get("SERVICEOS_RUN_REAL_DB_TESTS", "1") != "1",
    reason="requires a real reachable Postgres instance",
)
class TestRealConcurrencyAndIdempotency:
    """Part 12/40: real Postgres, real concurrency -- proves the advisory
    lock actually serializes the count-then-insert race, not just that the
    unit-test mock returns the right number."""

    @pytest.fixture
    def session_factory(self):
        settings = get_settings()
        engine = create_async_engine(settings.DATABASE_URL, pool_size=10, max_overflow=10)
        yield async_sessionmaker(engine, expire_on_commit=False)

    @pytest.mark.asyncio
    async def test_concurrent_creates_never_exceed_actor_limit(self, session_factory):
        import asyncio
        from app.engines.enterprise_grid.models import EnterpriseExportJob

        actor_id = uuid.uuid4()
        try:
            async def try_create(n: int):
                async with session_factory() as db:
                    svc = ExportService()
                    try:
                        job, _ = await svc.create_export_job(
                            db, actor_id, None, "admin_categories",
                            filters={}, columns=["name"],
                        )
                        return "ok"
                    except ValueError as e:
                        return str(e).split(":", 1)[0]

            # EXPORT_MAX_CONCURRENT_JOBS_PER_ACTOR + 2 simultaneous creates --
            # at most the limit may succeed, the rest must be denied.
            n_attempts = EXPORT_MAX_CONCURRENT_JOBS_PER_ACTOR + 2
            results = await asyncio.gather(*[try_create(i) for i in range(n_attempts)])
            successes = [r for r in results if r == "ok"]
            denials = [r for r in results if r == ERR_EXPORT_CONCURRENT_JOB_LIMIT]
            assert len(successes) == EXPORT_MAX_CONCURRENT_JOBS_PER_ACTOR, (
                f"expected exactly {EXPORT_MAX_CONCURRENT_JOBS_PER_ACTOR} successes, got: {results}"
            )
            assert len(denials) == n_attempts - EXPORT_MAX_CONCURRENT_JOBS_PER_ACTOR

            async with session_factory() as verify_db:
                count_row = await verify_db.execute(
                    select(EnterpriseExportJob).where(
                        EnterpriseExportJob.requested_by_user_id == actor_id
                    )
                )
                rows = count_row.scalars().all()
                assert len(rows) == EXPORT_MAX_CONCURRENT_JOBS_PER_ACTOR, (
                    "database row count must match the enforced limit exactly -- "
                    "proves the advisory lock actually serialized the race"
                )
        finally:
            async with session_factory() as cleanup_db:
                await cleanup_db.execute(text(
                    "DELETE FROM enterprise_export_jobs WHERE requested_by_user_id = :a"
                ), {"a": str(actor_id)})
                await cleanup_db.commit()

    @pytest.mark.asyncio
    async def test_concurrent_identical_idempotent_replay_creates_one_job(self, session_factory):
        import asyncio
        from app.engines.enterprise_grid.models import EnterpriseExportJob

        actor_id = uuid.uuid4()
        key = f"concurrency-test-{uuid.uuid4()}"
        try:
            async def try_create():
                async with session_factory() as db:
                    svc = ExportService()
                    job, is_replay = await svc.create_export_job(
                        db, actor_id, None, "admin_categories",
                        filters={}, columns=["name"], idempotency_key=key,
                    )
                    return job.id

            job_ids = await asyncio.gather(try_create(), try_create(), try_create())
            assert len(set(job_ids)) == 1, f"expected exactly 1 logical job, got: {set(job_ids)}"

            async with session_factory() as verify_db:
                rows = (await verify_db.execute(
                    select(EnterpriseExportJob).where(
                        EnterpriseExportJob.requested_by_user_id == actor_id,
                        EnterpriseExportJob.idempotency_key == key,
                    )
                )).scalars().all()
                assert len(rows) == 1, "exactly one database row for one idempotency identity"
        finally:
            async with session_factory() as cleanup_db:
                await cleanup_db.execute(text(
                    "DELETE FROM enterprise_export_jobs WHERE requested_by_user_id = :a"
                ), {"a": str(actor_id)})
                await cleanup_db.commit()

    @pytest.mark.asyncio
    async def test_two_different_actors_never_share_idempotency_identity(self, session_factory):
        """Same client-chosen key string used by two different actors must
        never collide -- the partial unique index is scoped per-actor."""
        actor_a, actor_b = uuid.uuid4(), uuid.uuid4()
        key = f"shared-key-{uuid.uuid4()}"
        try:
            async with session_factory() as db:
                svc = ExportService()
                job_a, replay_a = await svc.create_export_job(
                    db, actor_a, None, "admin_categories",
                    filters={}, columns=["name"], idempotency_key=key,
                )
            async with session_factory() as db:
                svc = ExportService()
                job_b, replay_b = await svc.create_export_job(
                    db, actor_b, None, "admin_categories",
                    filters={}, columns=["name"], idempotency_key=key,
                )
            assert job_a.id != job_b.id
            assert replay_a is False and replay_b is False
        finally:
            async with session_factory() as cleanup_db:
                await cleanup_db.execute(text(
                    "DELETE FROM enterprise_export_jobs WHERE requested_by_user_id IN (:a, :b)"
                ), {"a": str(actor_a), "b": str(actor_b)})
                await cleanup_db.commit()
