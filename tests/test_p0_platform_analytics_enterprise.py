"""P0 Platform Analytics Enterprise — 20 tests.

Tests cover PlatformAnalyticsService methods and platform_router imports.
All DB calls are mocked; no live DB needed.
"""
from __future__ import annotations

import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock


# ── Mock DB factory ───────────────────────────────────────────────────────────

def _db(scalar_value=None, rows_value=None):
    """Return a mock AsyncSession."""
    mock_result = MagicMock()
    mock_result.scalar.return_value = scalar_value
    mock_result.mappings.return_value.all.return_value = rows_value or []
    db = MagicMock()
    db.execute = AsyncMock(return_value=mock_result)
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    return db


def _db_rows(rows: list[dict]):
    """Return a mock DB that yields specific rows from fetchall()."""
    mock_result = MagicMock()
    mock_result.scalar.return_value = len(rows)
    mock_result.fetchall.return_value = [MagicMock(_mapping=r) for r in rows]
    db = MagicMock()
    db.execute = AsyncMock(return_value=mock_result)
    return db


# ── Import guard ──────────────────────────────────────────────────────────────

def test_platform_service_imports():
    from app.engines.analytics.platform_service import PlatformAnalyticsService
    svc = PlatformAnalyticsService()
    assert svc is not None


def test_platform_router_imports():
    from app.engines.analytics.platform_router import platform_analytics_router
    assert platform_analytics_router is not None
    routes = [r.path for r in platform_analytics_router.routes]
    assert any("platform/summary" in r for r in routes)
    assert any("operational-alerts" in r for r in routes)
    assert any("finance/summary" in r for r in routes)


# ── 1. Platform summary loads ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_platform_summary_loads():
    from app.engines.analytics.platform_service import PlatformAnalyticsService
    db = _db(scalar_value=5)
    svc = PlatformAnalyticsService()
    result = await svc.get_platform_summary(db)
    assert isinstance(result, dict)
    required_keys = [
        "active_tenants", "total_jobs", "platform_revenue",
        "completed_job_deductions", "provider_direct_service_value",
        "avg_job_rating", "complaint_rate", "pending_approvals",
        "new_providers", "customer_service_credits_issued",
        "security_deposit_held", "active_customers",
    ]
    for k in required_keys:
        assert k in result, f"Missing key: {k}"


# ── 2. Summary returns zeros when no data ─────────────────────────────────────

@pytest.mark.asyncio
async def test_platform_summary_returns_zeros_on_no_data():
    from app.engines.analytics.platform_service import PlatformAnalyticsService
    db = _db(scalar_value=0)
    svc = PlatformAnalyticsService()
    result = await svc.get_platform_summary(db)
    assert result["active_tenants"] == 0
    assert result["platform_revenue"] == 0.0
    assert result["complaint_rate"] == 0.0


# ── 3. Platform trends loads ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_platform_trends_loads():
    from app.engines.analytics.platform_service import PlatformAnalyticsService
    db = _db()
    svc = PlatformAnalyticsService()
    result = await svc.get_platform_trends(db)
    assert "jobs_trend" in result
    assert "revenue_trend" in result
    assert "tenant_growth" in result
    assert "complaint_trend" in result
    assert isinstance(result["jobs_trend"], list)


# ── 4. Operational alerts loads ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_operational_alerts_loads():
    from app.engines.analytics.platform_service import PlatformAnalyticsService
    db = _db_rows([])
    svc = PlatformAnalyticsService()
    result = await svc.get_operational_alerts(db)
    assert "items" in result
    assert "total" in result
    assert isinstance(result["items"], list)


# ── 5. Category performance loads ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_category_performance_loads():
    from app.engines.analytics.platform_service import PlatformAnalyticsService
    db = _db_rows([])
    svc = PlatformAnalyticsService()
    result = await svc.get_category_performance(db)
    assert "items" in result
    assert isinstance(result["items"], list)


# ── 6. Provider performance loads ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_provider_performance_loads():
    from app.engines.analytics.platform_service import PlatformAnalyticsService
    db = _db_rows([])
    svc = PlatformAnalyticsService()
    result = await svc.get_provider_performance(db)
    assert "items" in result
    assert isinstance(result["items"], list)


# ── 7. Finance summary loads ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_finance_summary_loads():
    from app.engines.analytics.platform_service import PlatformAnalyticsService
    db = _db(scalar_value=0)
    svc = PlatformAnalyticsService()
    result = await svc.get_finance_summary(db)
    assert isinstance(result, dict)
    for k in ["platform_revenue", "package_revenue", "subscription_revenue",
              "usage_credit_topups", "completed_job_deductions",
              "customer_service_credits_issued", "security_deposits_held",
              "failed_deductions"]:
        assert k in result, f"Missing finance key: {k}"


# ── 8. provider_direct_service_value separate from platform_revenue ───────────

@pytest.mark.asyncio
async def test_provider_direct_service_value_is_separate():
    from app.engines.analytics.platform_service import PlatformAnalyticsService
    db = _db(scalar_value=0)
    svc = PlatformAnalyticsService()
    result = await svc.get_platform_summary(db)
    assert "provider_direct_service_value" in result
    # Finance summary should NOT have provider_direct_service_value — it's not platform revenue
    fin = await svc.get_finance_summary(db)
    assert "provider_direct_service_value" not in fin


# ── 9. No payout/withdrawal field in finance response ─────────────────────────

@pytest.mark.asyncio
async def test_no_payout_withdrawal_in_finance():
    from app.engines.analytics.platform_service import PlatformAnalyticsService
    db = _db(scalar_value=0)
    svc = PlatformAnalyticsService()
    result = await svc.get_finance_summary(db)
    for key in result.keys():
        assert "payout" not in key.lower(), f"Forbidden key found: {key}"
        assert "withdrawal" not in key.lower(), f"Forbidden key found: {key}"
        assert "escrow" not in key.lower(), f"Forbidden key found: {key}"


# ── 10. Quality summary loads ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_quality_summary_loads():
    from app.engines.analytics.platform_service import PlatformAnalyticsService
    db = _db(scalar_value=0)
    svc = PlatformAnalyticsService()
    result = await svc.get_quality_summary(db)
    assert "avg_rating" in result
    assert "review_count" in result
    assert "complaint_rate" in result
    assert "dispute_rate" in result
    assert "sla_success_rate" in result


# ── 11. Complaints summary loads ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_complaints_summary_loads():
    from app.engines.analytics.platform_service import PlatformAnalyticsService
    db = _db(scalar_value=0)
    svc = PlatformAnalyticsService()
    result = await svc.get_complaints_summary(db)
    assert "total_complaints" in result
    assert "open_complaints" in result
    assert "resolved_complaints" in result
    assert "avg_resolution_hours" in result
    assert "customer_service_credits_issued" in result
    assert "tenant_responsible_count" in result


# ── 12. Complaints breakdown loads ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_complaints_breakdown_loads():
    from app.engines.analytics.platform_service import PlatformAnalyticsService
    db = _db_rows([])
    svc = PlatformAnalyticsService()
    result = await svc.get_complaints_breakdown(db)
    assert "by_severity" in result
    assert "by_type" in result


# ── 13. Geography summary loads ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_geography_summary_loads():
    from app.engines.analytics.platform_service import PlatformAnalyticsService
    db = _db_rows([])
    svc = PlatformAnalyticsService()
    result = await svc.get_geography_summary(db)
    assert "top_cities" in result
    assert isinstance(result["top_cities"], list)


# ── 14. Customer summary loads ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_customer_summary_loads():
    from app.engines.analytics.platform_service import PlatformAnalyticsService
    db = _db(scalar_value=0)
    svc = PlatformAnalyticsService()
    result = await svc.get_customer_summary(db)
    assert "active_customers" in result
    assert "new_customers" in result
    assert "bookings_per_customer" in result
    assert "customer_service_credits_used" in result
    assert "customer_complaints" in result


# ── 15. Summary respects date params ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_summary_respects_date_params():
    from app.engines.analytics.platform_service import PlatformAnalyticsService
    db = _db(scalar_value=0)
    svc = PlatformAnalyticsService()
    # Should not raise with explicit dates
    result = await svc.get_platform_summary(db, date_from="2025-01-01", date_to="2025-12-31")
    assert isinstance(result, dict)
    assert "active_tenants" in result


# ── 16. Summary respects vertical filter ─────────────────────────────────────

@pytest.mark.asyncio
async def test_summary_respects_vertical_filter():
    from app.engines.analytics.platform_service import PlatformAnalyticsService
    db = _db(scalar_value=0)
    svc = PlatformAnalyticsService()
    result = await svc.get_platform_summary(db, vertical="home_services")
    assert isinstance(result, dict)
    assert "active_tenants" in result


# ── 17. Export report creates record ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_export_report_creates_record():
    from app.engines.analytics.platform_service import PlatformAnalyticsService
    db = _db()
    svc = PlatformAnalyticsService()
    result = await svc.export_report(db, "platform_summary", {"date_from": "2025-01-01"}, "user-123")
    assert "export_id" in result
    assert result["status"] == "queued"
    assert "download_url" in result


# ── 18. Resolve alert returns status ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_resolve_alert_returns_status():
    from app.engines.analytics.platform_service import PlatformAnalyticsService
    db = _db()
    svc = PlatformAnalyticsService()
    result = await svc.resolve_alert(db, "alert_pending_abc123")
    assert result["status"] == "resolved"
    assert "alert_id" in result


# ── 19. Ignore alert returns status ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_ignore_alert_returns_status():
    from app.engines.analytics.platform_service import PlatformAnalyticsService
    db = _db()
    svc = PlatformAnalyticsService()
    result = await svc.ignore_alert(db, "alert_pending_abc123")
    assert result["status"] == "ignored"
    assert "alert_id" in result


# ── 20. Finance by vertical loads ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_finance_by_vertical_loads():
    from app.engines.analytics.platform_service import PlatformAnalyticsService
    db = _db_rows([])
    svc = PlatformAnalyticsService()
    result = await svc.get_finance_by_vertical(db)
    assert "items" in result
    assert isinstance(result["items"], list)
