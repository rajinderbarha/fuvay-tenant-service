"""Sprint 26 — Enterprise Filters + Data Grid System tests."""
import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone


# ── helpers ───────────────────────────────────────────────────────────────────
def _uuid():
    return uuid.uuid4()


def _mock_db():
    db = AsyncMock()
    db.flush  = AsyncMock()
    db.commit = AsyncMock()
    db.delete = AsyncMock()
    db.add    = MagicMock()
    # FINAL-L5-05AA: create_export_job now issues an advisory-lock text()
    # call (return value discarded) and a concurrent-job-count select()
    # (needs .scalar_one() -> int) before every job creation. A bare
    # AsyncMock's auto-generated .scalar_one() is itself a MagicMock, which
    # is truthy and supports comparison operators -- `mock_result >= 3`
    # silently evaluates via MagicMock.__ge__ rather than raising, so every
    # test would incorrectly hit the concurrent-job-limit path without this
    # explicit stub (0 active jobs, well under any configured limit).
    _default_result = MagicMock()
    _default_result.scalar_one.return_value = 0
    _default_result.scalars.return_value.first.return_value = None
    _default_result.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=_default_result)
    return db


def _exec_result(item):
    r = MagicMock()
    r.scalars.return_value.first.return_value = item
    r.scalars.return_value.all.return_value   = [item] if item else []
    return r


# ── Filter Registry ────────────────────────────────────────────────────────────
from app.engines.enterprise_grid.filter_registry import EnterpriseFilterRegistry
from app.engines.enterprise_grid.constants import (
    SCOPE_ADMIN_GLOBAL, SCOPE_PROVIDER,
    ERR_GRID_RESOURCE_NOT_FOUND,
)


def test_registry_admin_service_jobs_exists():
    cfg = EnterpriseFilterRegistry.get_config("admin_service_jobs")
    assert cfg["scope_type"] == SCOPE_ADMIN_GLOBAL
    assert "status" in cfg["allowed_filters"]


def test_registry_provider_service_jobs_exists():
    cfg = EnterpriseFilterRegistry.get_config("provider_service_jobs")
    assert cfg["scope_type"] == SCOPE_PROVIDER
    assert "status" in cfg["allowed_filters"]


def test_registry_invalid_resource_raises():
    with pytest.raises(ValueError, match="GRID_RESOURCE_NOT_FOUND"):
        EnterpriseFilterRegistry.get_config("nonexistent_resource")


def test_registry_unknown_filter_not_allowed():
    assert EnterpriseFilterRegistry.validate_filter("admin_service_jobs", "unknown_col") is False


def test_registry_allowed_filter():
    assert EnterpriseFilterRegistry.validate_filter("admin_service_jobs", "status") is True


def test_registry_unknown_sort_not_allowed():
    assert EnterpriseFilterRegistry.validate_sort("admin_service_jobs", "random_field") is False


def test_registry_allowed_sort():
    assert EnterpriseFilterRegistry.validate_sort("admin_service_jobs", "created_at") is True


def test_registry_default_sort_applied():
    default = EnterpriseFilterRegistry.get_default_sort("admin_service_jobs")
    assert default["sort_by"] == "created_at"
    assert default["sort_direction"] == "desc"


def test_registry_sensitive_fields_blocked():
    assert EnterpriseFilterRegistry.is_sensitive("admin_service_jobs", "internal_admin_notes") is True


def test_registry_non_sensitive_field():
    assert EnterpriseFilterRegistry.is_sensitive("admin_service_jobs", "job_number") is False


def test_all_resources_have_required_keys():
    for key in EnterpriseFilterRegistry.all_resource_keys():
        cfg = EnterpriseFilterRegistry.get_config(key)
        assert "allowed_filters" in cfg
        assert "allowed_sort_fields" in cfg
        assert "default_sort" in cfg
        assert "scope_type" in cfg


def test_validate_columns_blocks_sensitive():
    invalid = EnterpriseFilterRegistry.validate_columns(
        "admin_service_jobs", ["internal_admin_notes"]
    )
    assert "internal_admin_notes" in invalid


def test_validate_columns_valid_column():
    invalid = EnterpriseFilterRegistry.validate_columns("admin_service_jobs", ["job_number"])
    assert invalid == []


# ── Query Service ─────────────────────────────────────────────────────────────
from app.engines.enterprise_grid.query_service import EnterpriseListQueryService


def test_query_service_pagination():
    svc = EnterpriseListQueryService()
    vq  = svc.parse_query_params("admin_service_jobs", {"page": "2", "page_size": "10"})
    assert vq.page      == 2
    assert vq.page_size == 10
    assert vq.offset    == 10


def test_query_service_defaults():
    svc = EnterpriseListQueryService()
    vq  = svc.parse_query_params("admin_service_jobs", {})
    assert vq.sort_by        == "created_at"
    assert vq.sort_direction == "desc"
    assert vq.page           == 1


def test_query_service_search():
    svc = EnterpriseListQueryService()
    vq  = svc.parse_query_params("admin_service_jobs", {"search": "JOB-001"})
    assert vq.search == "JOB-001"


def test_query_service_date_range_filter():
    svc = EnterpriseListQueryService()
    vq  = svc.parse_query_params("admin_service_jobs", {
        "created_from": "2025-01-01", "created_to": "2025-12-31"
    })
    assert "created_from" in vq.filters
    assert "created_to"   in vq.filters


def test_query_service_invalid_date_range():
    svc = EnterpriseListQueryService()
    from app.engines.enterprise_grid.constants import ERR_GRID_INVALID_DATE_RANGE
    with pytest.raises(ValueError, match="GRID_INVALID_DATE_RANGE"):
        svc.parse_query_params("admin_service_jobs", {
            "created_from": "2025-12-31", "created_to": "2025-01-01"
        })


def test_query_service_status_filter():
    svc = EnterpriseListQueryService()
    vq  = svc.parse_query_params("admin_service_jobs", {"status": "completed"})
    assert vq.filters.get("status") == "completed"


def test_query_service_invalid_sort_raises():
    svc = EnterpriseListQueryService()
    from app.engines.enterprise_grid.constants import ERR_GRID_SORT_NOT_ALLOWED
    with pytest.raises(ValueError, match="GRID_SORT_NOT_ALLOWED"):
        svc.parse_query_params("admin_service_jobs", {"sort_by": "malicious_col"})


def test_query_service_invalid_page():
    svc = EnterpriseListQueryService()
    from app.engines.enterprise_grid.constants import ERR_GRID_INVALID_PAGE
    with pytest.raises(ValueError, match="GRID_INVALID_PAGE"):
        svc.parse_query_params("admin_service_jobs", {"page": "0"})


def test_query_service_page_size_too_large():
    svc = EnterpriseListQueryService()
    from app.engines.enterprise_grid.constants import ERR_GRID_INVALID_PAGE_SIZE
    with pytest.raises(ValueError, match="GRID_INVALID_PAGE_SIZE"):
        svc.parse_query_params("admin_service_jobs", {"page_size": "999"})


def test_query_service_tenant_admin_scope():
    svc = EnterpriseListQueryService()
    tid = _uuid()
    effective = svc.validate_scope("admin_service_jobs", actor_tenant_id=None, requested_tenant_id=tid)
    assert effective == tid


def test_query_service_provider_scope_enforced():
    svc       = EnterpriseListQueryService()
    prov_tid  = _uuid()
    other_tid = _uuid()
    effective = svc.validate_scope("provider_service_jobs", actor_tenant_id=prov_tid, requested_tenant_id=other_tid)
    assert effective == prov_tid  # provider cannot override


def test_query_service_build_response():
    svc = EnterpriseListQueryService()
    vq  = svc.parse_query_params("admin_service_jobs", {"page": "1", "page_size": "10"})
    result = svc.build_response(vq, items=[{"id": "1"}], total_items=100)
    assert result["pagination"]["total_pages"] == 10
    assert result["pagination"]["has_next"]    is True
    assert result["pagination"]["has_previous"] is False
    assert len(result["items"]) == 1


# ── Saved Views Service ───────────────────────────────────────────────────────
from app.engines.enterprise_grid.services import SavedViewService
from app.engines.enterprise_grid.models import EnterpriseSavedView
from app.engines.enterprise_grid.constants import (
    VIS_PRIVATE, VIS_TENANT_SHARED,
    ERR_SAVED_VIEW_NOT_FOUND, ERR_SAVED_VIEW_ACCESS_DENIED,
    ERR_SAVED_VIEW_INVALID_FILTER, ERR_SAVED_VIEW_DUPLICATE_NAME,
)


@pytest.mark.asyncio
async def test_create_saved_view_success():
    svc = SavedViewService()
    db  = _mock_db()
    db.execute = AsyncMock(return_value=_exec_result(None))
    view = await svc.create_view(
        db, _uuid(), None, "admin", "admin_service_jobs",
        "My View", {"status": "open"}, {"sort_by": "created_at"}, [], 25, VIS_PRIVATE,
    )
    db.add.assert_called_once()
    db.commit.assert_awaited_once()
    assert view.view_name == "My View"


@pytest.mark.asyncio
async def test_create_saved_view_invalid_filter():
    svc = SavedViewService()
    db  = _mock_db()
    with pytest.raises(ValueError, match="SAVED_VIEW_INVALID_FILTER"):
        await svc.create_view(
            db, _uuid(), None, "admin", "admin_service_jobs",
            "Bad View", {"hack_filter": "x"}, {}, [], 25, VIS_PRIVATE,
        )


@pytest.mark.asyncio
async def test_create_saved_view_duplicate_name():
    svc      = SavedViewService()
    db       = _mock_db()
    existing = MagicMock(id=_uuid())
    db.execute = AsyncMock(return_value=_exec_result(existing))
    with pytest.raises(ValueError, match="SAVED_VIEW_DUPLICATE_NAME"):
        await svc.create_view(
            db, _uuid(), None, "admin", "admin_service_jobs",
            "Duplicate", {}, {}, [], 25, VIS_PRIVATE,
        )


@pytest.mark.asyncio
async def test_get_saved_view_not_found():
    svc = SavedViewService()
    db  = _mock_db()
    db.execute = AsyncMock(return_value=_exec_result(None))
    with pytest.raises(ValueError, match="SAVED_VIEW_NOT_FOUND"):
        await svc.get_view(db, _uuid(), _uuid(), None)


@pytest.mark.asyncio
async def test_get_saved_view_private_wrong_user():
    svc  = SavedViewService()
    db   = _mock_db()
    view = MagicMock(
        id=_uuid(), owner_user_id=_uuid(), visibility=VIS_PRIVATE, tenant_id=None
    )
    db.execute = AsyncMock(return_value=_exec_result(view))
    with pytest.raises(ValueError, match="SAVED_VIEW_ACCESS_DENIED"):
        await svc.get_view(db, view.id, _uuid(), None)


@pytest.mark.asyncio
async def test_delete_saved_view_not_owner():
    svc       = SavedViewService()
    db        = _mock_db()
    view_uid  = _uuid()
    view      = MagicMock(id=_uuid(), owner_user_id=view_uid, visibility=VIS_PRIVATE, tenant_id=None)
    db.execute = AsyncMock(return_value=_exec_result(view))
    with pytest.raises(ValueError, match="SAVED_VIEW_ACCESS_DENIED"):
        await svc.delete_view(db, view.id, _uuid(), None)


@pytest.mark.asyncio
async def test_tenant_shared_view_wrong_tenant():
    svc   = SavedViewService()
    db    = _mock_db()
    owner = _uuid()
    tid   = _uuid()
    view  = MagicMock(id=_uuid(), owner_user_id=owner, visibility=VIS_TENANT_SHARED, tenant_id=tid)
    db.execute = AsyncMock(return_value=_exec_result(view))
    with pytest.raises(ValueError, match="SAVED_VIEW_ACCESS_DENIED"):
        await svc.get_view(db, view.id, _uuid(), _uuid())  # different tenant


# ── Column Preferences ────────────────────────────────────────────────────────
from app.engines.enterprise_grid.services import ColumnPreferenceService
from app.engines.enterprise_grid.models import EnterpriseColumnPreference
from app.engines.enterprise_grid.constants import ERR_COLUMN_PREFERENCE_INVALID


@pytest.mark.asyncio
async def test_save_column_preferences_success():
    svc = ColumnPreferenceService()
    db  = _mock_db()
    db.execute = AsyncMock(return_value=_exec_result(None))
    prefs = await svc.save_preferences(
        db, _uuid(), None, "admin_service_jobs",
        [{"key": "job_number", "label": "Job #", "visible": True, "order": 1}], "compact",
    )
    db.add.assert_called_once()
    assert prefs.density == "compact"


@pytest.mark.asyncio
async def test_save_column_preferences_blocks_sensitive():
    svc = ColumnPreferenceService()
    db  = _mock_db()
    with pytest.raises(ValueError, match="COLUMN_PREFERENCE_INVALID"):
        await svc.save_preferences(
            db, _uuid(), None, "admin_service_jobs",
            [{"key": "internal_admin_notes", "visible": True, "order": 1}], "comfortable",
        )


@pytest.mark.asyncio
async def test_reset_column_preferences():
    svc  = ColumnPreferenceService()
    db   = _mock_db()
    pref = MagicMock()
    db.execute = AsyncMock(return_value=_exec_result(pref))
    defaults = await svc.reset_preferences(db, _uuid(), "admin_service_jobs")
    db.delete.assert_awaited_once()
    assert isinstance(defaults, list)


# ── Export Service ────────────────────────────────────────────────────────────
from app.engines.enterprise_grid.services import ExportService
from app.engines.enterprise_grid.models import EnterpriseExportJob
from app.engines.enterprise_grid.constants import ERR_EXPORT_FIELD_NOT_ALLOWED, ERR_EXPORT_JOB_NOT_FOUND


@pytest.mark.asyncio
async def test_create_export_job_success():
    svc = ExportService()
    db  = _mock_db()
    job, _ = await svc.create_export_job(
        db, _uuid(), None, "admin_service_jobs",
        filters={"status": "completed"},
        columns=["job_number", "status", "created_at"],
    )
    db.add.assert_called_once()
    assert job.status        == "pending"
    assert job.resource_key  == "admin_service_jobs"


@pytest.mark.asyncio
async def test_create_export_job_sensitive_field_blocked():
    svc = ExportService()
    db  = _mock_db()
    with pytest.raises(ValueError, match="EXPORT_FIELD_NOT_ALLOWED"):
        await svc.create_export_job(
            db, _uuid(), None, "admin_service_jobs",
            filters={}, columns=["internal_admin_notes"],
        )


@pytest.mark.asyncio
async def test_get_export_job_not_found():
    svc = ExportService()
    db  = _mock_db()
    db.execute = AsyncMock(return_value=_exec_result(None))
    with pytest.raises(ValueError, match="EXPORT_JOB_NOT_FOUND"):
        await svc.get_export_job(db, _uuid(), _uuid())


@pytest.mark.asyncio
async def test_get_export_job_wrong_user():
    svc = ExportService()
    db  = _mock_db()
    job = MagicMock(requested_by_user_id=_uuid())
    db.execute = AsyncMock(return_value=_exec_result(job))
    from app.engines.enterprise_grid.constants import ERR_EXPORT_JOB_ACCESS_DENIED
    with pytest.raises(ValueError, match="EXPORT_JOB_ACCESS_DENIED"):
        await svc.get_export_job(db, _uuid(), _uuid())


def test_generate_csv_excludes_sensitive():
    svc  = ExportService()
    rows = [{"job_number": "JOB-001", "status": "completed", "internal_admin_notes": "secret"}]
    csv  = svc.generate_csv("admin_service_jobs", ["job_number", "status", "internal_admin_notes"], rows)
    assert "secret" not in csv
    assert "JOB-001" in csv


def test_generate_csv_format():
    svc  = ExportService()
    rows = [{"job_number": "JOB-001", "status": "completed", "created_at": "2025-01-01"}]
    csv  = svc.generate_csv("admin_service_jobs", ["job_number", "status", "created_at"], rows)
    lines = csv.strip().split("\n")
    assert lines[0].startswith("job_number")
    assert "JOB-001" in lines[1]


# ── Provider scope tests ─────────────────────────────────────────────────────
def test_provider_resource_scope():
    cfg = EnterpriseFilterRegistry.get_config("provider_complaints")
    assert cfg["scope_type"] == SCOPE_PROVIDER


def test_provider_cannot_filter_by_tenant_id():
    allowed = EnterpriseFilterRegistry.get_config("provider_service_jobs")["allowed_filters"]
    assert "tenant_id" not in allowed


# ── Router import smoke tests ─────────────────────────────────────────────────
def test_enterprise_router_importable():
    from app.engines.enterprise_grid.router import enterprise_router
    assert enterprise_router.prefix == "/enterprise"


def test_enterprise_router_has_expected_routes():
    from app.engines.enterprise_grid.router import enterprise_router
    paths = [r.path for r in enterprise_router.routes]
    assert any("/saved-views" in p for p in paths)
    assert any("/column-preferences" in p for p in paths)
    assert any("/exports" in p for p in paths)
    assert any("/registry" in p for p in paths)


# ── Phase 7: Swagger / OpenAPI doc completeness ───────────────────────────────

def test_all_enterprise_routes_have_summary():
    from app.engines.enterprise_grid.router import enterprise_router
    for route in enterprise_router.routes:
        if hasattr(route, "summary"):
            assert route.summary, f"Route {getattr(route, 'path', '?')} missing summary"


def test_all_enterprise_routes_have_description():
    from app.engines.enterprise_grid.router import enterprise_router
    for route in enterprise_router.routes:
        if hasattr(route, "description") and hasattr(route, "summary"):
            assert route.description, f"Route {getattr(route, 'path', '?')} missing description"


def test_enterprise_router_tags_set():
    from app.engines.enterprise_grid.router import enterprise_router
    tagged = [r for r in enterprise_router.routes if hasattr(r, "tags") and r.tags]
    assert len(tagged) > 0, "No routes have tags set"


# ── Phase 7: Export row limit enforcement ─────────────────────────────────────

@pytest.mark.asyncio
async def test_export_row_limit_blocked_when_too_large():
    from app.engines.enterprise_grid.services import ExportService
    from app.engines.enterprise_grid.constants import (
        ENTERPRISE_SYNC_EXPORT_ROW_LIMIT, EXPORT_FAILED, ERR_EXPORT_ASYNC_REQUIRED,
    )
    from app.engines.enterprise_grid.models import EnterpriseExportJob

    svc = ExportService()
    db  = _mock_db()

    with patch("app.engines.enterprise_grid.services.EnterpriseFilterRegistry.get_allowed_export_fields",
               return_value=["status", "created_at"]):
        with patch("app.engines.enterprise_grid.services.EnterpriseFilterRegistry.validate_filter",
                   return_value=True):
            job, _ = await svc.create_export_job(
                db, _uuid(), _uuid(),
                resource_key="admin_service_jobs",
                filters={},
                columns=["status", "created_at"],
                estimated_row_count=ENTERPRISE_SYNC_EXPORT_ROW_LIMIT + 1,
            )

    assert job.status == EXPORT_FAILED
    assert ERR_EXPORT_ASYNC_REQUIRED in job.failure_reason


@pytest.mark.asyncio
async def test_export_row_limit_passes_when_within_threshold():
    from app.engines.enterprise_grid.services import ExportService
    from app.engines.enterprise_grid.constants import ENTERPRISE_SYNC_EXPORT_ROW_LIMIT, EXPORT_PENDING

    svc = ExportService()
    db  = _mock_db()

    with patch("app.engines.enterprise_grid.services.EnterpriseFilterRegistry.get_allowed_export_fields",
               return_value=["status", "created_at"]):
        with patch("app.engines.enterprise_grid.services.EnterpriseFilterRegistry.validate_filter",
                   return_value=True):
            job, _ = await svc.create_export_job(
                db, _uuid(), _uuid(),
                resource_key="admin_service_jobs",
                filters={},
                columns=["status", "created_at"],
                estimated_row_count=ENTERPRISE_SYNC_EXPORT_ROW_LIMIT,
            )

    assert job.status == EXPORT_PENDING
    assert job.failure_reason is None


@pytest.mark.asyncio
async def test_export_no_estimated_count_defaults_to_pending():
    from app.engines.enterprise_grid.services import ExportService
    from app.engines.enterprise_grid.constants import EXPORT_PENDING

    svc = ExportService()
    db  = _mock_db()

    with patch("app.engines.enterprise_grid.services.EnterpriseFilterRegistry.get_allowed_export_fields",
               return_value=["status"]):
        with patch("app.engines.enterprise_grid.services.EnterpriseFilterRegistry.validate_filter",
                   return_value=True):
            job, _ = await svc.create_export_job(
                db, _uuid(), None,
                resource_key="admin_audit_logs",
                filters={},
                columns=["status"],
                estimated_row_count=None,
            )

    assert job.status == EXPORT_PENDING


def test_export_async_required_constant_defined():
    from app.engines.enterprise_grid.constants import ERR_EXPORT_ASYNC_REQUIRED
    assert ERR_EXPORT_ASYNC_REQUIRED == "EXPORT_ASYNC_REQUIRED"


def test_enterprise_sync_export_row_limit_is_5000():
    from app.engines.enterprise_grid.constants import ENTERPRISE_SYNC_EXPORT_ROW_LIMIT
    assert ENTERPRISE_SYNC_EXPORT_ROW_LIMIT == 5000


# ── Phase 7: Registry completeness ────────────────────────────────────────────

def test_registry_has_39_resources():
    # P0 Enterprise Pricing Module Upgrade added 3 admin resources (23 -> 26):
    # admin_pricing_tiers, admin_tier_locations, admin_pricing_rules.
    # P0 Enterprise Finance Hub Upgrade added 5 more admin resources (26 -> 31):
    # admin_finance_deposits, admin_finance_topups, admin_finance_claims,
    # admin_finance_payouts, admin_finance_wallets.
    # P0 Enterprise Security & Threats SOC Upgrade added 4 more admin resources (31 -> 35):
    # admin_security_threats, admin_security_sessions, admin_ip_blocklist, admin_api_keys.
    # P0 Enterprise Customer Users Management Upgrade added 1 more admin resource (35 -> 36):
    # admin_customers.
    # P0 Enterprise Platform Settings Upgrade added 3 more admin resources (36 -> 39):
    # admin_settings, admin_feature_flags, admin_setting_audit_logs.
    from app.engines.enterprise_grid.filter_registry import EnterpriseFilterRegistry
    keys = EnterpriseFilterRegistry.all_resource_keys()
    assert len(keys) == 39, f"Expected 39 resources, got {len(keys)}"


def test_registry_has_32_admin_resources():
    from app.engines.enterprise_grid.filter_registry import EnterpriseFilterRegistry
    from app.engines.enterprise_grid.constants import SCOPE_ADMIN_GLOBAL
    admin_keys = [
        k for k in EnterpriseFilterRegistry.all_resource_keys()
        if EnterpriseFilterRegistry.get_config(k)["scope_type"] == SCOPE_ADMIN_GLOBAL
    ]
    assert len(admin_keys) == 32, f"Expected 32 admin resources, got {len(admin_keys)}"


def test_registry_has_7_provider_resources():
    from app.engines.enterprise_grid.filter_registry import EnterpriseFilterRegistry
    from app.engines.enterprise_grid.constants import SCOPE_PROVIDER
    provider_keys = [
        k for k in EnterpriseFilterRegistry.all_resource_keys()
        if EnterpriseFilterRegistry.get_config(k)["scope_type"] == SCOPE_PROVIDER
    ]
    assert len(provider_keys) == 7, f"Expected 7 provider resources, got {len(provider_keys)}"


def test_all_admin_resources_have_export_fields():
    from app.engines.enterprise_grid.filter_registry import EnterpriseFilterRegistry
    from app.engines.enterprise_grid.constants import SCOPE_ADMIN_GLOBAL
    for key in EnterpriseFilterRegistry.all_resource_keys():
        cfg = EnterpriseFilterRegistry.get_config(key)
        if cfg["scope_type"] == SCOPE_ADMIN_GLOBAL:
            fields = EnterpriseFilterRegistry.get_allowed_export_fields(key)
            assert fields, f"{key} has no allowed export fields"


def test_provider_scope_resources_no_tenant_id_filter():
    from app.engines.enterprise_grid.filter_registry import EnterpriseFilterRegistry
    from app.engines.enterprise_grid.constants import SCOPE_PROVIDER
    for key in EnterpriseFilterRegistry.all_resource_keys():
        cfg = EnterpriseFilterRegistry.get_config(key)
        if cfg["scope_type"] == SCOPE_PROVIDER:
            assert "tenant_id" not in cfg["allowed_filters"], \
                f"Provider resource {key} should not allow tenant_id filter"


# ── Phase 7: Export field security ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_export_blocked_sensitive_field():
    from app.engines.enterprise_grid.services import ExportService
    from app.engines.enterprise_grid.constants import ERR_EXPORT_FIELD_NOT_ALLOWED

    svc = ExportService()
    db  = _mock_db()

    with patch("app.engines.enterprise_grid.services.EnterpriseFilterRegistry.get_allowed_export_fields",
               return_value=["status", "created_at"]):
        with pytest.raises(ValueError, match=ERR_EXPORT_FIELD_NOT_ALLOWED):
            await svc.create_export_job(
                db, _uuid(), None,
                resource_key="admin_service_jobs",
                filters={},
                columns=["status", "internal_admin_notes"],
            )


# ── Phase 7: CSV generation security ─────────────────────────────────────────

def test_csv_generation_strips_sensitive_columns():
    from app.engines.enterprise_grid.services import ExportService

    svc  = ExportService()
    rows = [{"status": "open", "internal_notes": "secret", "created_at": "2026-01-01"}]

    with patch("app.engines.enterprise_grid.services.EnterpriseFilterRegistry.get_allowed_export_fields",
               return_value=["status", "created_at"]):
        csv_out = svc.generate_csv("admin_complaints", ["status", "internal_notes", "created_at"], rows)

    assert "internal_notes" not in csv_out
    assert "status" in csv_out
    assert "secret" not in csv_out
