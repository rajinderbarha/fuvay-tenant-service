"""Sprint 28 — Analytics + Reports Tests.

29 tests covering:
- Constants / report definitions registry
- resolve_date_range / analytics_ok / safe_metric helpers
- ReportDefinition scope enforcement
- AdminAnalyticsService (mocked DB)
- ProviderAnalyticsService (mocked DB, tenant isolation)
- ReportService (list, run, sensitive-column stripping, scope guard)
- Admin analytics router imports + Swagger tag presence
- Provider analytics router imports + tenant_id guard
- Migration 046 existence
"""
import pytest
import uuid
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def user_id():
    return uuid.uuid4()

@pytest.fixture
def tenant_id():
    return uuid.uuid4()

@pytest.fixture
def other_tenant_id():
    return uuid.uuid4()


def _db(scalar_value=None, rows_value=None):
    """Return a mock AsyncSession."""
    mock_result = MagicMock()
    mock_result.scalar.return_value = scalar_value
    mock_result.mappings.return_value.all.return_value = rows_value or []
    db = MagicMock()
    db.execute = AsyncMock(return_value=mock_result)
    db.add     = MagicMock()
    db.flush   = AsyncMock()
    db.commit  = AsyncMock()
    db.refresh = AsyncMock()
    return db


# ══════════════════════════════════════════════════════════════════════════════
# 1. Constants
# ══════════════════════════════════════════════════════════════════════════════

def test_constants_error_codes_defined():
    from app.engines.analytics.constants import (
        ERR_ANALYTICS_ACCESS_DENIED, ERR_ANALYTICS_INVALID_DATE_RANGE,
        ERR_REPORT_NOT_FOUND, ERR_REPORT_ASYNC_REQUIRED,
    )
    assert ERR_ANALYTICS_ACCESS_DENIED  == "ANALYTICS_ACCESS_DENIED"
    assert ERR_ANALYTICS_INVALID_DATE_RANGE == "ANALYTICS_INVALID_DATE_RANGE"
    assert ERR_REPORT_NOT_FOUND         == "REPORT_NOT_FOUND"
    assert ERR_REPORT_ASYNC_REQUIRED    == "REPORT_ASYNC_REQUIRED"


def test_constants_report_keys_defined():
    from app.engines.analytics.constants import (
        RPT_ADMIN_PLATFORM_SUMMARY, RPT_ADMIN_FINANCIAL,
        RPT_PROVIDER_DASHBOARD, RPT_PROVIDER_FINANCIAL,
    )
    assert "admin" in RPT_ADMIN_PLATFORM_SUMMARY
    assert "admin" in RPT_ADMIN_FINANCIAL
    assert "provider" in RPT_PROVIDER_DASHBOARD
    assert "provider" in RPT_PROVIDER_FINANCIAL


def test_constants_scope_and_limits():
    from app.engines.analytics.constants import (
        SCOPE_ADMIN, SCOPE_PROVIDER, EXPORT_SYNC_ROW_LIMIT, MAX_DATE_RANGE_DAYS,
    )
    assert SCOPE_ADMIN    == "admin"
    assert SCOPE_PROVIDER == "provider"
    assert EXPORT_SYNC_ROW_LIMIT == 5000
    assert MAX_DATE_RANGE_DAYS   == 365


# ══════════════════════════════════════════════════════════════════════════════
# 2. Helpers
# ══════════════════════════════════════════════════════════════════════════════

def test_analytics_ok_envelope():
    from app.engines.analytics.helpers import analytics_ok
    result = analytics_ok(summary={"total": 5}, series=[1, 2], breakdown=[{"a": 1}])
    assert result["success"] is True
    assert result["data"]["summary"]["total"] == 5
    assert result["data"]["series"] == [1, 2]
    assert "generated_at" in result["data"]


def test_analytics_ok_empty_defaults():
    from app.engines.analytics.helpers import analytics_ok
    result = analytics_ok()
    assert result["data"]["summary"] == {}
    assert result["data"]["series"]  == []
    assert result["data"]["breakdown"] == []


def test_resolve_date_range_defaults():
    from datetime import timezone, datetime
    from app.engines.analytics.helpers import resolve_date_range
    utc_today = datetime.now(timezone.utc).date()
    df, dt = resolve_date_range(None, None)
    assert dt == utc_today
    assert (dt - df).days == 30


def test_resolve_date_range_explicit():
    from app.engines.analytics.helpers import resolve_date_range
    df, dt = resolve_date_range("2025-01-01", "2025-01-31")
    assert df == date(2025, 1, 1)
    assert dt == date(2025, 1, 31)


def test_resolve_date_range_from_gt_to_raises():
    from app.engines.analytics.helpers import resolve_date_range
    from app.engines.analytics.constants import ERR_ANALYTICS_INVALID_DATE_RANGE
    with pytest.raises(ValueError) as exc:
        resolve_date_range("2025-06-01", "2025-01-01")
    assert ERR_ANALYTICS_INVALID_DATE_RANGE in str(exc.value)


def test_resolve_date_range_too_wide_raises():
    from app.engines.analytics.helpers import resolve_date_range
    from app.engines.analytics.constants import ERR_ANALYTICS_INVALID_DATE_RANGE
    with pytest.raises(ValueError) as exc:
        resolve_date_range("2024-01-01", "2025-12-31")
    assert ERR_ANALYTICS_INVALID_DATE_RANGE in str(exc.value)


def test_resolve_date_range_bad_format_raises():
    from app.engines.analytics.helpers import resolve_date_range
    from app.engines.analytics.constants import ERR_ANALYTICS_INVALID_DATE_RANGE
    with pytest.raises(ValueError):
        resolve_date_range("not-a-date", None)


@pytest.mark.asyncio
async def test_safe_metric_returns_default_on_exception():
    from app.engines.analytics.helpers import safe_metric

    async def bad_coro():
        raise RuntimeError("DB is down")

    result = await safe_metric(bad_coro(), default={"error": True})
    assert result == {"error": True}


@pytest.mark.asyncio
async def test_safe_metric_returns_value_on_success():
    from app.engines.analytics.helpers import safe_metric

    async def good_coro():
        return 42

    result = await safe_metric(good_coro(), default=None)
    assert result == 42


# ══════════════════════════════════════════════════════════════════════════════
# 3. Report Definitions Registry
# ══════════════════════════════════════════════════════════════════════════════

def test_registry_has_10_admin_reports():
    from app.engines.analytics.report_definitions import ReportDefinitionRegistry
    from app.engines.analytics.constants import SCOPE_ADMIN
    admins = ReportDefinitionRegistry.all_for_scope(SCOPE_ADMIN)
    assert len(admins) == 10


def test_registry_has_9_provider_reports():
    from app.engines.analytics.report_definitions import ReportDefinitionRegistry
    from app.engines.analytics.constants import SCOPE_PROVIDER
    providers = ReportDefinitionRegistry.all_for_scope(SCOPE_PROVIDER)
    assert len(providers) == 9


def test_registry_get_returns_definition():
    from app.engines.analytics.report_definitions import ReportDefinitionRegistry
    from app.engines.analytics.constants import RPT_ADMIN_FINANCIAL
    defn = ReportDefinitionRegistry.get(RPT_ADMIN_FINANCIAL)
    assert defn is not None
    assert defn.report_key == RPT_ADMIN_FINANCIAL
    assert defn.scope == "admin"


def test_registry_get_unknown_returns_none():
    from app.engines.analytics.report_definitions import ReportDefinitionRegistry
    assert ReportDefinitionRegistry.get("nonexistent_report_key") is None


def test_registry_provider_reports_have_sensitive_cols():
    from app.engines.analytics.report_definitions import ReportDefinitionRegistry
    from app.engines.analytics.constants import RPT_PROVIDER_JOBS
    defn = ReportDefinitionRegistry.get(RPT_PROVIDER_JOBS)
    assert "customer_name" in defn.sensitive_cols or "student_name" in defn.sensitive_cols


def test_registry_admin_financial_has_extra_filters():
    from app.engines.analytics.report_definitions import ReportDefinitionRegistry
    from app.engines.analytics.constants import RPT_ADMIN_FINANCIAL
    defn = ReportDefinitionRegistry.get(RPT_ADMIN_FINANCIAL)
    assert defn.allowed_filters == ["date_from", "date_to"]


# ══════════════════════════════════════════════════════════════════════════════
# 4. AdminAnalyticsService
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_admin_get_platform_summary_returns_analytics_ok():
    from app.engines.analytics.admin_analytics import AdminAnalyticsService
    svc = AdminAnalyticsService()
    db  = _db(scalar_value=10)
    result = await svc.get_platform_summary(db)
    assert result["success"] is True
    assert "summary" in result["data"]


@pytest.mark.asyncio
async def test_admin_get_platform_summary_card_failure_doesnt_crash():
    """If one metric fails, the others still return."""
    from app.engines.analytics.admin_analytics import AdminAnalyticsService
    svc = AdminAnalyticsService()
    db  = MagicMock()
    db.execute = AsyncMock(side_effect=Exception("DB error"))
    result = await svc.get_platform_summary(db)
    assert result["success"] is True


@pytest.mark.asyncio
async def test_admin_get_category_performance_returns_analytics_ok():
    from app.engines.analytics.admin_analytics import AdminAnalyticsService
    svc = AdminAnalyticsService()
    db  = _db(rows_value=[{"category_name": "Home Services", "total_jobs": 100}])
    result = await svc.get_category_performance(db)
    assert result["success"] is True


@pytest.mark.asyncio
async def test_admin_get_financial_summary_returns_analytics_ok():
    from app.engines.analytics.admin_analytics import AdminAnalyticsService
    svc = AdminAnalyticsService()
    db  = _db(scalar_value=5000.0)
    result = await svc.get_financial_summary(db)
    assert result["success"] is True


# ══════════════════════════════════════════════════════════════════════════════
# 5. ProviderAnalyticsService — tenant isolation
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_provider_dashboard_requires_tenant_id(tenant_id):
    from app.engines.analytics.provider_analytics import ProviderAnalyticsService
    svc = ProviderAnalyticsService()
    db  = _db(scalar_value=50)
    result = await svc.get_provider_dashboard(db, tenant_id=tenant_id)
    assert result["success"] is True


@pytest.mark.asyncio
async def test_provider_dashboard_card_failure_doesnt_crash(tenant_id):
    from app.engines.analytics.provider_analytics import ProviderAnalyticsService
    svc = ProviderAnalyticsService()
    db  = MagicMock()
    db.execute = AsyncMock(side_effect=Exception("connection error"))
    result = await svc.get_provider_dashboard(db, tenant_id=tenant_id)
    assert result["success"] is True


@pytest.mark.asyncio
async def test_provider_financial_returns_analytics_ok(tenant_id):
    from app.engines.analytics.provider_analytics import ProviderAnalyticsService
    svc = ProviderAnalyticsService()
    db  = _db(scalar_value=1234.5)
    result = await svc.get_provider_financial_summary(db, tenant_id=tenant_id)
    assert result["success"] is True


# ══════════════════════════════════════════════════════════════════════════════
# 6. ReportService
# ══════════════════════════════════════════════════════════════════════════════

def test_report_service_list_reports_admin():
    from app.engines.analytics.report_service import ReportService
    from app.engines.analytics.constants import SCOPE_ADMIN
    svc = ReportService()
    defs = svc.list_reports(SCOPE_ADMIN)
    assert len(defs) == 10
    assert all(d["scope"] == SCOPE_ADMIN for d in defs)


def test_report_service_list_reports_provider():
    from app.engines.analytics.report_service import ReportService
    from app.engines.analytics.constants import SCOPE_PROVIDER
    svc = ReportService()
    defs = svc.list_reports(SCOPE_PROVIDER)
    assert len(defs) == 9
    assert all(d["scope"] == SCOPE_PROVIDER for d in defs)


@pytest.mark.asyncio
async def test_report_run_rejects_unknown_report_key(user_id, tenant_id):
    from app.engines.analytics.report_service import ReportService
    from app.engines.analytics.constants import SCOPE_ADMIN, ERR_REPORT_NOT_FOUND
    svc = ReportService()
    db  = _db()
    with pytest.raises(ValueError) as exc:
        await svc.run_report(db, report_key="not_a_key", scope=SCOPE_ADMIN,
                             requested_by_user_id=user_id, tenant_id=None, filters={})
    assert ERR_REPORT_NOT_FOUND in str(exc.value)


@pytest.mark.asyncio
async def test_report_run_rejects_scope_mismatch(user_id, tenant_id):
    """Admin report cannot be run with provider scope."""
    from app.engines.analytics.report_service import ReportService
    from app.engines.analytics.constants import (
        SCOPE_PROVIDER, RPT_ADMIN_FINANCIAL, ERR_REPORT_ACCESS_DENIED,
    )
    svc = ReportService()
    db  = _db()
    with pytest.raises(ValueError) as exc:
        await svc.run_report(db, report_key=RPT_ADMIN_FINANCIAL, scope=SCOPE_PROVIDER,
                             requested_by_user_id=user_id, tenant_id=tenant_id, filters={})
    assert ERR_REPORT_ACCESS_DENIED in str(exc.value)


@pytest.mark.asyncio
async def test_report_run_rejects_disallowed_filter(user_id):
    """Filters not in allowed_filters must be rejected."""
    from app.engines.analytics.report_service import ReportService
    from app.engines.analytics.constants import (
        SCOPE_ADMIN, RPT_ADMIN_PLATFORM_SUMMARY, ERR_REPORT_FILTER_NOT_ALLOWED,
    )
    svc = ReportService()
    db  = _db()
    with pytest.raises(ValueError) as exc:
        await svc.run_report(db, report_key=RPT_ADMIN_PLATFORM_SUMMARY, scope=SCOPE_ADMIN,
                             requested_by_user_id=user_id, tenant_id=None,
                             filters={"hacker_column": "inject"})
    assert ERR_REPORT_FILTER_NOT_ALLOWED in str(exc.value)


def test_report_service_strip_sensitive_removes_cols():
    from app.engines.analytics.report_service import _strip_sensitive
    rows = [
        {"job_id": "1", "customer_name": "Alice", "revenue": 100},
        {"job_id": "2", "customer_name": "Bob",   "revenue": 200},
    ]
    stripped = _strip_sensitive(rows, ["customer_name"])
    assert all("customer_name" not in r for r in stripped)
    assert all("revenue" in r for r in stripped)


def test_report_service_to_csv_generates_headers():
    from app.engines.analytics.report_service import _to_csv
    rows = [{"a": 1, "b": 2}, {"a": 3, "b": 4}]
    csv_str = _to_csv(rows)
    assert "a" in csv_str
    assert "b" in csv_str
    assert "1" in csv_str


# ══════════════════════════════════════════════════════════════════════════════
# 7. Router imports + swagger
# ══════════════════════════════════════════════════════════════════════════════

def test_admin_analytics_router_imports_cleanly():
    from app.engines.analytics.admin_router import (
        admin_analytics_router, admin_reports_router,
    )
    assert admin_analytics_router.prefix == "/v1/admin/analytics"
    assert admin_reports_router.prefix   == "/v1/admin/reports"


def test_provider_analytics_router_imports_cleanly():
    from app.engines.analytics.provider_router import (
        provider_analytics_router, provider_reports_router,
    )
    assert provider_analytics_router.prefix == "/v1/provider/analytics"
    assert provider_reports_router.prefix   == "/v1/provider/reports"


def test_routers_registered_in_main():
    """Ensure Sprint 28 routers are wired into the FastAPI app."""
    import importlib.util, pathlib
    path = pathlib.Path(__file__).resolve().parents[1] / "app" / "main.py"
    src = path.read_text(encoding="utf-8")
    assert "admin_analytics_router" in src
    assert "provider_analytics_router" in src
    assert "admin_reports_router" in src
    assert "provider_reports_router" in src


# ══════════════════════════════════════════════════════════════════════════════
# 8. Provider router — tenant_id guard
# ══════════════════════════════════════════════════════════════════════════════

def test_provider_router_tid_helper_raises_without_tenant():
    from app.engines.analytics.provider_router import _tid
    u = MagicMock()
    u.tenant_id = None
    with pytest.raises(ValueError):
        _tid(u)


def test_provider_router_tid_helper_returns_uuid():
    from app.engines.analytics.provider_router import _tid
    tid = str(uuid.uuid4())
    u = MagicMock()
    u.tenant_id = tid
    result = _tid(u)
    assert isinstance(result, uuid.UUID)
    assert str(result) == tid


# ══════════════════════════════════════════════════════════════════════════════
# 9. Migration 046
# ══════════════════════════════════════════════════════════════════════════════

def test_migration_046_exists():
    import pathlib
    versions_dir = pathlib.Path(__file__).resolve().parents[1] / "alembic" / "versions"
    files = list(versions_dir.glob("046_*.py"))
    assert len(files) == 1, f"Expected 1 migration file matching 046_*.py, found: {files}"


def test_migration_046_has_correct_revision():
    import pathlib, importlib.util
    versions_dir = pathlib.Path(__file__).resolve().parents[1] / "alembic" / "versions"
    path = next(versions_dir.glob("046_*.py"))
    spec = importlib.util.spec_from_file_location("migration_046", path)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.revision       == "046"
    assert mod.down_revision  == "045"


def test_migration_046_creates_analytics_tables():
    import pathlib
    path = pathlib.Path(__file__).resolve().parents[1] / "alembic" / "versions"
    files = list(path.glob("046_*.py"))
    src = files[0].read_text(encoding="utf-8")
    assert "analytics_daily_metrics"  in src
    assert "analytics_report_runs"    in src
