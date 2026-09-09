"""Regression coverage for the Admin dashboard/provider status mismatch."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_SERVICE = (ROOT / "app/engines/dashboard_command_center/service.py").read_text(encoding="utf-8-sig")
DASHBOARD_ROUTER = (ROOT / "app/engines/dashboard_command_center/admin_router.py").read_text(encoding="utf-8-sig")
PROVIDER_ROUTER = (ROOT / "app/engines/provider_portal/router.py").read_text(encoding="utf-8-sig")
PROVIDER_ADMIN = (ROOT / "app/engines/provider_portal/admin_router.py").read_text(encoding="utf-8-sig")
BOOKABILITY_QUERY = (ROOT / "app/engines/provider_portal/bookability_query.py").read_text(encoding="utf-8-sig")
BOOKING_SERVICE = (ROOT / "app/engines/home_service_booking/service.py").read_text(encoding="utf-8-sig")
MATCHING = (ROOT / "app/engines/home_service_booking/matching_engine.py").read_text(encoding="utf-8-sig")
DASHBOARD_PAGE = (ROOT / "frontend/super-admin/app/admin/dashboard/page.tsx").read_text(encoding="utf-8-sig")


def test_dashboard_uses_one_latest_provider_level_snapshot_per_tenant():
    assert "WITH latest_provider_status AS" in DASHBOARD_SERVICE
    assert "SELECT DISTINCT ON (tenant_id)" in DASHBOARD_SERVICE
    assert "WHERE category_id IS NULL" in DASHBOARD_SERVICE
    assert "ORDER BY tenant_id, created_at DESC, id DESC" in DASHBOARD_SERVICE
    assert "LEFT JOIN latest_provider_status pvs" in DASHBOARD_SERVICE


def test_dashboard_refresh_recomputes_instead_of_only_refetching():
    assert "async def refresh_provider_bookability" in DASHBOARD_SERVICE
    assert "_evaluate_provider_bookability" in DASHBOARD_SERVICE
    refresh_handler = DASHBOARD_ROUTER.split("async def refresh(", 1)[1].split("@router.post", 1)[0]
    assert "refresh_provider_bookability" in refresh_handler
    assert "await db.commit()" in refresh_handler
    assert "after=result" in refresh_handler


def test_provider_tab_synchronizes_existing_stale_snapshots_once():
    assert 'if (tab !== "providers" || providerSyncStarted.current) return' in DASHBOARD_PAGE
    assert "refreshAction.execute()" in DASHBOARD_PAGE
    assert "lifecycle.refetch()" in DASHBOARD_PAGE
    assert "atRisk.refetch()" in DASHBOARD_PAGE


def test_approval_immediately_persists_recomputed_bookability():
    approval = PROVIDER_ADMIN.split("async def approve_provider_onboarding", 1)[1].split("@admin_router.post", 1)[0]
    assert "_evaluate_provider_bookability" in approval
    assert "_persist_provider_bookability" in approval


def test_status_persistence_targets_provider_level_row_and_preserves_holds():
    persistence = PROVIDER_ROUTER.split("async def _persist_provider_bookability", 1)[1].split("@router.post", 1)[0]
    assert "category_id IS NULL" in persistence
    assert "ORDER BY created_at DESC, id DESC LIMIT 1" in persistence
    assert "ADMIN_VISIBILITY_HOLD" in persistence
    assert "ADMIN_BOOKABILITY_HOLD" in persistence


def test_booking_and_matching_use_same_provider_level_snapshot():
    assert "_PROVIDER_VISIBILITY_STATUSES.c.category_id.is_(None)" in BOOKABILITY_QUERY
    assert "_PROVIDER_VISIBILITY_STATUSES.c.id.desc()" in BOOKABILITY_QUERY
    assert "category_id IS NULL" in BOOKING_SERVICE
    assert "category_id IS NULL" in MATCHING


def test_dashboard_surfaces_the_real_first_blocker_message():
    at_risk = DASHBOARD_SERVICE.split("async def get_at_risk_tenants", 1)[1].split("async def get_compliance_security", 1)[0]
    assert 'blocker.get("message")' in at_risk
    assert 'blocker_reason or "Provider is not bookable"' in at_risk
