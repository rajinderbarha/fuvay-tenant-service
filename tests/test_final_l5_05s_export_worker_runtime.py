"""FINAL-L5-05S — Export Worker, Secure File Generation, Download
Authorization and Retention Certification.

FINAL-L5-05R closed the export *authorization* gap (every resource has an
export permission and cross-tenant/unknown-resource requests are rejected)
but explicitly documented that no worker, file generator, or storage layer
existed anywhere -- a job could only ever sit PENDING forever. This sprint
builds the missing execution pipeline: a database-backed worker
(`app/jobs/export_worker.py`, FOR UPDATE SKIP LOCKED claiming), 5 real
resource query adapters (`resource_adapters.py`), a private local storage
service (`export_storage.py`), and download/cancel/retry endpoints.

Tests here cover:
  1. Resource adapter registry correctness (only 5 RUNTIME_SUPPORTED).
  2. Storage service round-trip + path-traversal defenses, unit-level.
  3. Real-Postgres worker claiming concurrency -- FOR UPDATE SKIP LOCKED
     must guarantee each pending job is claimed by exactly one caller even
     under concurrent ticks (not a mocked assertion).
  4. Real end-to-end file generation: a job created against a
     RUNTIME_SUPPORTED resource is actually processed by the worker and a
     real file lands in the private storage directory with a matching
     checksum/row_count.
  5. Retry/failure classification (retryable vs. non-retryable prefixes).
  6. Cleanup expiry: an expired completed job's file is deleted and its
     row is transitioned to `expired` with `storage_key` cleared.
  7. Download endpoint static-ordering guards (permission re-check before
     status/expiry/existence, consistent with FINAL-L5-05R's established
     "authorize-before-anything-else" source-inspection pattern).
"""
from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import get_settings

ROOT = Path(__file__).parent.parent


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


class TestResourceAdapterRegistry:
    def test_exactly_five_resources_are_runtime_supported(self):
        from app.engines.enterprise_grid.resource_adapters import RESOURCE_ADAPTERS
        assert set(RESOURCE_ADAPTERS.keys()) == {
            "admin_reviews", "admin_finance_topups", "admin_audit_logs",
            "admin_tenants", "admin_categories",
        }

    def test_is_runtime_supported_matches_registry(self):
        from app.engines.enterprise_grid.resource_adapters import is_runtime_supported
        assert is_runtime_supported("admin_categories") is True
        assert is_runtime_supported("admin_pricing_tiers") is False
        assert is_runtime_supported("totally_fake_resource") is False

    def test_runtime_supported_resources_are_a_subset_of_authorization_mapped_resources(self):
        # Every RUNTIME_SUPPORTED resource must also be a real, permission-
        # mapped resource (FINAL-L5-05R) -- a worker must never be able to
        # generate a file for a resource with no export permission mapping.
        from app.engines.enterprise_grid.resource_adapters import RESOURCE_ADAPTERS
        from app.engines.enterprise_grid.filter_registry import RESOURCE_EXPORT_PERMISSIONS
        for key in RESOURCE_ADAPTERS:
            assert key in RESOURCE_EXPORT_PERMISSIONS, f"{key} has a file adapter but no export permission mapping"

    @pytest.mark.asyncio
    async def test_fetch_rows_raises_generator_unavailable_for_unsupported_resource(self):
        from app.engines.enterprise_grid.resource_adapters import fetch_rows
        with pytest.raises(ValueError) as exc:
            await fetch_rows(AsyncMock(), "admin_pricing_tiers", None, {})
        assert str(exc.value).startswith("EXPORT_GENERATOR_UNAVAILABLE")

    def test_worker_recognizes_generator_unavailable_as_non_retryable(self):
        from app.jobs.export_worker import NON_RETRYABLE_PREFIXES
        assert "EXPORT_GENERATOR_UNAVAILABLE" in NON_RETRYABLE_PREFIXES
        assert "EXPORT_CROSS_TENANT_FORBIDDEN" in NON_RETRYABLE_PREFIXES
        assert "PERMISSION_DENIED" in NON_RETRYABLE_PREFIXES


class TestExportStorageServiceUnit:
    def test_sanitize_filename_strips_path_traversal_and_unsafe_chars(self):
        from app.engines.enterprise_grid.export_storage import sanitize_filename
        assert sanitize_filename("../../etc/passwd") == "passwd"
        assert sanitize_filename("..\\..\\windows\\system32") == "system32"
        assert sanitize_filename("report<script>.csv") == "report_script_.csv"
        assert sanitize_filename("") == "export"

    def test_key_to_path_rejects_traversal_even_though_keys_are_server_generated(self, tmp_path):
        from app.engines.enterprise_grid import export_storage as mod
        with patch.object(mod, "EXPORTS_DIR", tmp_path):
            svc = mod.ExportStorageService()
            for bad_key in ("../../secret", "/etc/passwd", "\\windows\\system32"):
                with pytest.raises(ValueError):
                    svc._key_to_path(bad_key)

    def test_upload_exists_read_delete_round_trip(self, tmp_path):
        from app.engines.enterprise_grid import export_storage as mod
        with patch.object(mod, "EXPORTS_DIR", tmp_path):
            svc = mod.ExportStorageService()
            job_id = uuid.uuid4()
            tenant_id = uuid.uuid4()
            content = b"name,status\r\nAlpha,active\r\n"
            stored = svc.upload_private(job_id, tenant_id, "categories.csv", content, "text/csv")

            assert svc.exists(stored.storage_key) is True
            assert svc.read_bytes(stored.storage_key) == content
            assert stored.file_size == len(content)
            import hashlib
            assert stored.checksum == hashlib.sha256(content).hexdigest()

            assert svc.delete(stored.storage_key) is True
            assert svc.exists(stored.storage_key) is False
            # deleting a second time is a no-op, not an error
            assert svc.delete(stored.storage_key) is False

    def test_export_storage_directory_is_never_the_public_uploads_directory(self):
        from app.engines.enterprise_grid.export_storage import EXPORTS_DIR
        assert "uploads" not in str(EXPORTS_DIR)
        assert str(EXPORTS_DIR) in (str(Path("var") / "exports"), "var\\exports", "var/exports")

    def test_main_py_does_not_mount_the_exports_directory_as_static_files(self):
        src = _read("app/main.py")
        assert 'StaticFiles(directory="var' not in src
        assert 'directory="var/exports"' not in src.replace("\\", "/")


@pytest.mark.skipif(
    os.environ.get("SERVICEOS_RUN_REAL_DB_TESTS", "1") != "1",
    reason="requires a real reachable Postgres instance",
)
class TestRealDatabaseWorker:
    """Real Postgres, real transactions, real FOR UPDATE SKIP LOCKED
    row-claiming -- not mocks (mission rule: 'do not return READY without
    worker concurrency testing')."""

    @pytest.fixture
    def real_engine(self):
        settings = get_settings()
        engine = create_async_engine(settings.DATABASE_URL, pool_size=10, max_overflow=10)
        yield engine

    @pytest.fixture
    def session_factory(self, real_engine, monkeypatch):
        factory = async_sessionmaker(real_engine, expire_on_commit=False)
        # The autouse conftest `mock_database` fixture replaces
        # app.database._async_session_factory with a MagicMock for every
        # test by default. export_worker.py's run_worker_tick/run_cleanup
        # call app.database.get_session_factory() internally -- for these
        # real-concurrency tests that must resolve to a REAL factory bound
        # to the same Postgres instance the test fixture itself uses.
        monkeypatch.setattr("app.database._async_session_factory", factory)
        return factory

    async def _make_job(self, session_factory, resource_key="admin_categories", status="pending",
                         requested_by=None, tenant_id=None, **extra):
        from app.engines.enterprise_grid.models import EnterpriseExportJob
        job_id = uuid.uuid4()
        async with session_factory() as db:
            job = EnterpriseExportJob(
                id=job_id,
                requested_by_user_id=requested_by or uuid.uuid4(),
                tenant_id=tenant_id,
                resource_key=resource_key,
                status=status,
                export_format="csv",
                filters={},
                columns=[],
                expires_at=extra.pop("expires_at", datetime.now(timezone.utc) + timedelta(hours=24)),
                **extra,
            )
            db.add(job)
            await db.commit()
        return job_id

    async def _cleanup_jobs(self, session_factory, job_ids):
        async with session_factory() as db:
            for jid in job_ids:
                await db.execute(text("DELETE FROM enterprise_export_jobs WHERE id = :id"), {"id": str(jid)})
            await db.commit()

    @pytest.mark.asyncio
    async def test_concurrent_claims_never_double_claim_the_same_pending_job(self, session_factory):
        from app.jobs.export_worker import _claim_next_job

        job_ids = [await self._make_job(session_factory, resource_key="admin_pricing_tiers")
                   for _ in range(6)]
        try:
            async def claim_one():
                async with session_factory() as db:
                    job = await _claim_next_job(db)
                    return job.id if job else None

            results = await asyncio.gather(*[claim_one() for _ in range(6)])
            claimed = [r for r in results if r is not None]
            assert len(claimed) == len(set(claimed)) == 6, (
                f"expected 6 distinct claims with zero duplicates, got {claimed}"
            )

            from app.engines.enterprise_grid.models import EnterpriseExportJob
            from sqlalchemy import func
            async with session_factory() as verify_db:
                count_row = await verify_db.execute(
                    select(func.count()).select_from(EnterpriseExportJob).where(
                        EnterpriseExportJob.id.in_(job_ids),
                        EnterpriseExportJob.status == "processing",
                    )
                )
                assert count_row.scalar_one() == 6, "all 6 jobs must be claimed (status=processing)"
        finally:
            await self._cleanup_jobs(session_factory, job_ids)

    @pytest.mark.asyncio
    async def test_claimed_job_is_marked_processing_with_worker_id_and_timestamps(self, session_factory):
        from app.jobs.export_worker import _claim_next_job, WORKER_ID

        job_id = await self._make_job(session_factory, resource_key="admin_pricing_tiers")
        try:
            async with session_factory() as db:
                job = await _claim_next_job(db)
                assert job is not None
                assert job.status == "processing"
                assert job.worker_id == WORKER_ID
                assert job.claimed_at is not None
                assert job.started_at is not None
        finally:
            await self._cleanup_jobs(session_factory, [job_id])

    @pytest.mark.asyncio
    async def test_worker_generates_a_real_file_for_a_runtime_supported_resource(self, session_factory):
        from app.jobs.export_worker import run_worker_tick
        from app.engines.enterprise_grid.export_storage import ExportStorageService
        from app.engines.enterprise_grid.models import EnterpriseExportJob

        job_id = await self._make_job(session_factory, resource_key="admin_categories")
        try:
            result = await run_worker_tick(batch_size=10)
            assert result["processed"] >= 1

            async with session_factory() as db:
                job = (await db.execute(
                    select(EnterpriseExportJob).where(EnterpriseExportJob.id == job_id)
                )).scalars().first()
                assert job.status == "completed", f"expected completed, got {job.status} ({job.error_message})"
                assert job.storage_key is not None
                assert job.checksum is not None
                assert job.row_count is not None and job.row_count >= 0
                assert job.file_size is not None and job.file_size > 0
                assert job.progress == 100
                assert job.completed_at is not None

                storage = ExportStorageService()
                assert storage.exists(job.storage_key)
                content = storage.read_bytes(job.storage_key)
                import hashlib
                assert hashlib.sha256(content).hexdigest() == job.checksum
                assert content.startswith(b"name,slug,status,created_at") or b"name" in content.split(b"\r\n")[0]
                storage.delete(job.storage_key)
        finally:
            await self._cleanup_jobs(session_factory, [job_id])

    @pytest.mark.asyncio
    async def test_worker_fails_controlled_for_unsupported_resource_without_retry_loop(self, session_factory):
        from app.jobs.export_worker import run_worker_tick
        from app.engines.enterprise_grid.models import EnterpriseExportJob

        job_id = await self._make_job(session_factory, resource_key="admin_pricing_tiers")
        try:
            await run_worker_tick(batch_size=10)
            async with session_factory() as db:
                job = (await db.execute(
                    select(EnterpriseExportJob).where(EnterpriseExportJob.id == job_id)
                )).scalars().first()
                assert job.status == "failed"
                assert job.error_code == "EXPORT_GENERATOR_UNAVAILABLE"
                assert job.retry_count == 0, "non-retryable errors must not increment retry_count / loop"
        finally:
            await self._cleanup_jobs(session_factory, [job_id])

    @pytest.mark.asyncio
    async def test_stale_processing_job_is_recovered_to_pending_then_eventually_fails(self, session_factory):
        from app.jobs.export_worker import _recover_stale_running_jobs, MAX_RETRIES
        from app.engines.enterprise_grid.models import EnterpriseExportJob

        stale_claim = datetime.now(timezone.utc) - timedelta(minutes=30)
        job_id = await self._make_job(
            session_factory, resource_key="admin_categories", status="processing",
            worker_id="dead-worker-1", claimed_at=stale_claim, started_at=stale_claim,
            retry_count=MAX_RETRIES,
        )
        try:
            async with session_factory() as db:
                recovered = await _recover_stale_running_jobs(db)
                assert recovered >= 1

            async with session_factory() as db:
                job = (await db.execute(
                    select(EnterpriseExportJob).where(EnterpriseExportJob.id == job_id)
                )).scalars().first()
                # retry_count already at MAX_RETRIES -> must fail, not loop forever
                assert job.status == "failed"
                assert job.error_code == "EXPORT_WORKER_TIMEOUT"
        finally:
            await self._cleanup_jobs(session_factory, [job_id])

    @pytest.mark.asyncio
    async def test_cleanup_expires_completed_job_past_expiry_and_deletes_its_file(self, session_factory):
        from app.jobs.export_worker import run_cleanup
        from app.engines.enterprise_grid.export_storage import ExportStorageService
        from app.engines.enterprise_grid.models import EnterpriseExportJob

        storage = ExportStorageService()
        job_id = uuid.uuid4()
        stored = storage.upload_private(job_id, None, "expired.csv", b"a,b\r\n1,2\r\n", "text/csv")

        past = datetime.now(timezone.utc) - timedelta(hours=1)
        await self._make_job(
            session_factory, resource_key="admin_categories", status="completed",
            expires_at=past, storage_key=stored.storage_key, filename=stored.filename,
            content_type=stored.content_type, file_size=stored.file_size, checksum=stored.checksum,
            completed_at=datetime.now(timezone.utc) - timedelta(hours=25),
        )
        # override the auto-generated job_id used inside _make_job by re-reading it back
        async with session_factory() as db:
            row = (await db.execute(
                select(EnterpriseExportJob).where(EnterpriseExportJob.storage_key == stored.storage_key)
            )).scalars().first()
            real_job_id = row.id
        try:
            assert storage.exists(stored.storage_key)
            await run_cleanup()

            async with session_factory() as db:
                job = (await db.execute(
                    select(EnterpriseExportJob).where(EnterpriseExportJob.id == real_job_id)
                )).scalars().first()
                assert job.status == "expired"
                assert job.storage_key is None
            assert not storage.exists(stored.storage_key), "expired file must be deleted from private storage"
        finally:
            await self._cleanup_jobs(session_factory, [real_job_id])


class TestDownloadEndpointAuthorizationOrdering:
    """Static source-inspection guards, matching the established
    FINAL-L5-05R pattern for verifying ordering of security checks without
    requiring a live server for every permutation."""

    def _block(self) -> str:
        src = _read("app/engines/enterprise_grid/router.py")
        start = src.index("async def download_export(")
        end = src.index("@enterprise_router", start + 10) if "@enterprise_router" in src[start + 10:] else len(src)
        return src[start:end]

    def test_download_rechecks_export_permission_before_returning_file(self):
        block = self._block()
        idx_perm = block.index("required_export_permission(job.resource_key)")
        idx_read = block.index("storage.read_bytes(job.storage_key)")
        assert idx_perm < idx_read, "permission must be re-checked before any file bytes are read"

    def test_download_checks_status_completed_before_reading_storage(self):
        block = self._block()
        idx_status = block.index('job.status != "completed"')
        idx_read = block.index("storage.read_bytes(job.storage_key)")
        assert idx_status < idx_read

    def test_download_checks_expiry_before_reading_storage(self):
        block = self._block()
        idx_expiry = block.index("EXPORT_JOB_EXPIRED")
        idx_read = block.index("storage.read_bytes(job.storage_key)")
        assert idx_expiry < idx_read

    def test_download_checks_storage_key_and_file_existence_before_reading(self):
        block = self._block()
        idx_exists = block.index("storage.exists(job.storage_key)")
        idx_read = block.index("storage.read_bytes(job.storage_key)")
        assert idx_exists < idx_read

    def test_download_writes_an_audit_record(self):
        block = self._block()
        assert 'operation="export.downloaded"' in block

    def test_get_export_job_scopes_by_requesting_user_not_just_job_id(self):
        # Knowing a job ID alone must never be sufficient (mission rule 15) --
        # get_export_job (used by download/retry/cancel) enforces
        # requested_by_user_id == caller, which is a tighter check than
        # tenant-scoping alone (correctly denies same-tenant coworkers too).
        src = _read("app/engines/enterprise_grid/services.py")
        start = src.index("async def get_export_job(")
        end = src.index("async def list_export_jobs(", start)
        block = src[start:end]
        assert "requested_by_user_id) != str(user_id)" in block
        assert "EXPORT_JOB_ACCESS_DENIED" in block


class TestCancelAndRetryStateMachineGuards:
    def test_cancel_only_allowed_from_pending_or_processing(self):
        src = _read("app/engines/enterprise_grid/router.py")
        start = src.index("async def cancel_export(")
        end = src.index("async def download_export(", start)
        block = src[start:end]
        assert '("pending", "processing")' in block
        assert "EXPORT_JOB_NOT_READY" in block

    def test_retry_only_allowed_from_failed_or_expired(self):
        src = _read("app/engines/enterprise_grid/router.py")
        start = src.index("async def retry_export(")
        end = src.index("async def cancel_export(", start)
        block = src[start:end]
        assert '("failed", "expired")' in block

    def test_retry_clears_worker_execution_state_not_just_status(self):
        # A retried job must not retain the previous attempt's worker_id/
        # claimed_at/storage_key -- otherwise a stale claim or an orphaned
        # file reference could survive a retry.
        src = _read("app/engines/enterprise_grid/router.py")
        start = src.index("async def retry_export(")
        end = src.index("async def cancel_export(", start)
        block = src[start:end]
        for field in ("job.worker_id", "job.claimed_at", "job.storage_key", "job.progress"):
            assert field in block, f"retry_export does not reset {field}"


class TestMigration135Shape:
    def test_status_check_constraint_uses_processing_not_running(self):
        src = _read("alembic/versions/135_export_worker_lifecycle.py")
        assert "'processing'" in src
        assert "'running'" not in src

    def test_all_new_columns_are_nullable_or_defaulted_for_backward_compatibility(self):
        src = _read("alembic/versions/135_export_worker_lifecycle.py")
        assert "nullable=True" in src
        assert 'server_default="0"' in src
