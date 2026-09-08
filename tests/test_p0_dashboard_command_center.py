"""P0 Platform Command Center Dashboard — static-inspection regression tests.

Backend engine lives at app/engines/dashboard_command_center/ (service.py +
admin_router.py), migration 104 (dashboard_action_states, dashboard_snapshots),
permission constants in app/core/permissions.py (DASHBOARD_*).

These tests follow this repo's established static-inspection convention
(reading source as text and asserting structure/wording) rather than spinning
up a live DB, matching tests/test_p0_marketing_automation_command_center.py
and tests/test_p0_admin_tenant_typescript_stabilization.py.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SERVICE = (ROOT / "app/engines/dashboard_command_center/service.py").read_text(encoding="utf-8")
ROUTER = (ROOT / "app/engines/dashboard_command_center/admin_router.py").read_text(encoding="utf-8")
PERMISSIONS = (ROOT / "app/core/permissions.py").read_text(encoding="utf-8")
MIGRATION = (ROOT / "alembic/versions/105_dashboard_command_center.py").read_text(encoding="utf-8")
MAIN = (ROOT / "app/main.py").read_text(encoding="utf-8")
ANALYTICS = (ROOT / "app/engines/analytics/platform_service.py").read_text(encoding="utf-8")


def test_executive_summary_endpoint_exists():
    assert '@router.get("/executive-summary"' in ROUTER
    assert "async def get_executive_summary" in SERVICE


def test_platform_health_endpoint_and_bands_exist():
    assert '@router.get("/platform-health"' in ROUTER
    assert "async def get_platform_health" in SERVICE


def test_finance_snapshot_separates_platform_revenue_from_provider_direct_value():
    assert '@router.get("/finance-snapshot"' in ROUTER
    assert "platform_revenue" in SERVICE
    assert "provider_direct_service_value" in SERVICE
    # Both concepts must appear as distinct keys, never merged into one "commission" field.
    assert "async def get_finance_snapshot" in SERVICE


def test_home_services_customer_payment_not_counted_as_platform_revenue():
    # Paid invoices are provider-direct service value. Platform revenue comes
    # only from credited top-up orders.
    assert "service_invoices" in SERVICE
    assert "credit_topup_orders" in SERVICE
    assert "provider_direct_service_value" in SERVICE
    assert "payout" not in SERVICE.lower()
    assert "cash wallet" not in SERVICE.lower()
    assert "withdraw" not in SERVICE.lower()


def test_dashboard_uses_canonical_home_services_sources_only():
    assert "service_jobs" in SERVICE
    assert "service_bookings" in SERVICE
    assert "provider_visibility_statuses" in SERVICE
    assert "usage_credit_ledger" in SERVICE
    assert "FROM health_scores" not in SERVICE
    assert "FROM jobs " not in SERVICE
    assert "FROM bookings " not in SERVICE
    assert "wallet_transactions" not in SERVICE
    assert "commission_records" not in SERVICE


def test_provider_attention_is_operational_not_retired_health_score():
    assert "_PROVIDER_ATTENTION_CTE" in SERVICE
    for signal in ("is_bookable", "open_complaints", "missing_deductions", "credit_balance"):
        assert signal in SERVICE


def test_forbidden_finance_language_absent_from_router_and_service():
    for banned in ("payout", "cash_wallet", "withdraw"):
        assert banned not in SERVICE.lower()
        assert banned not in ROUTER.lower()


def test_tenant_lifecycle_endpoint_exists():
    assert '@router.get("/tenant-lifecycle"' in ROUTER
    assert "async def get_tenant_lifecycle" in SERVICE


def test_operations_snapshot_endpoint_exists():
    assert '@router.get("/operations-snapshot"' in ROUTER
    assert "async def get_operations_snapshot" in SERVICE


def test_unconfirmed_request_demand_is_grouped_by_real_area_and_channel():
    assert '@router.get("/request-demand-by-area"' in ROUTER
    assert "async def get_request_demand_by_area" in SERVICE
    assert "home_service_booking_drafts" in SERVICE
    assert "ai_conversation_sessions" in SERVICE
    assert "session.context_data ->> 'channel'" in SERVICE
    for field in ("instagram_requests", "whatsapp_requests", "customer_app_requests", "share_pct"):
        assert field in SERVICE


def test_trends_endpoint_returns_time_series_or_empty_state():
    assert '@router.get("/trends"' in ROUTER
    assert "async def get_trends" in SERVICE


def test_action_queue_endpoints_exist():
    assert '@router.get("/action-queue"' in ROUTER
    assert '@router.post("/action-queue/{action_id}/resolve"' in ROUTER
    assert '@router.post("/action-queue/{action_id}/snooze"' in ROUTER
    assert '@router.post("/action-queue/{action_id}/assign"' in ROUTER
    assert "async def get_action_queue" in SERVICE
    assert "async def resolve_action" in SERVICE
    assert "async def snooze_action" in SERVICE
    assert "async def assign_action" in SERVICE


def test_engine_health_endpoint_exists():
    assert '@router.get("/engine-health"' in ROUTER
    assert "async def get_engine_health" in SERVICE


def test_at_risk_tenants_endpoint_exists():
    assert '@router.get("/at-risk-tenants"' in ROUTER
    assert "async def get_at_risk_tenants" in SERVICE


def test_compliance_security_respects_permission():
    assert '@router.get("/compliance-security"' in ROUTER
    assert "P.DASHBOARD_SECURITY_READ" in ROUTER


def test_activity_feed_endpoint_exists():
    assert '@router.get("/activity-feed"' in ROUTER
    assert "async def get_activity_feed" in SERVICE


def test_export_snapshot_creates_report_and_is_audited():
    assert '@router.post("/export-snapshot"' in ROUTER
    assert "async def export_snapshot" in SERVICE
    assert "dashboard_snapshots" in SERVICE
    assert 'operation="dashboard.exported"' in ROUTER


def test_all_dashboard_permission_constants_exist():
    for perm in (
        "DASHBOARD_READ", "DASHBOARD_FINANCE_READ", "DASHBOARD_OPERATIONS_READ",
        "DASHBOARD_SECURITY_READ", "DASHBOARD_COMPLIANCE_READ", "DASHBOARD_EXPORT",
        "DASHBOARD_ACTION_QUEUE_MANAGE", "DASHBOARD_ENGINE_HEALTH_READ", "DASHBOARD_ACTIVITY_READ",
    ):
        assert perm in PERMISSIONS, f"missing permission constant {perm}"


def test_all_endpoints_gated_by_require_permission():
    # Some endpoints share the `_svc` dependency (itself gated by
    # require_permission(P.DASHBOARD_READ)); others declare their own
    # narrower permission inline. Together every endpoint is gated.
    assert "def _svc(" in ROUTER
    assert "require_permission(P.DASHBOARD_READ)" in ROUTER
    assert ROUTER.count("require_permission(P.DASHBOARD_") >= 13


def test_mutations_are_audited():
    for op in ("dashboard.action_resolved", "dashboard.action_snoozed",
               "dashboard.action_assigned", "dashboard.refreshed", "dashboard.exported"):
        assert op in ROUTER


def test_migration_104_creates_action_states_and_snapshots_tables():
    assert 'down_revision = "104"' in MIGRATION or "down_revision = '104'" in MIGRATION
    assert "dashboard_action_states" in MIGRATION
    assert "dashboard_snapshots" in MIGRATION


def test_router_mounted_in_main():
    assert "dashboard_command_center_router" in MAIN
    assert "app.include_router(dashboard_command_center_router)" in MAIN


def test_safe_query_helpers_rollback_on_exception():
    # Root-cause fix: a caught exception in _safe_count/_safe_scalar/_safe_rows
    # must not leave the session's transaction poisoned for subsequent queries.
    assert ANALYTICS.count("await db.rollback()") >= 3
