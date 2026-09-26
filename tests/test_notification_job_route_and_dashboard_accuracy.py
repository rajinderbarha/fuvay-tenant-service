"""Regression checks for provider notification routing and dashboard truthfulness."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CREATION = (ROOT / "app/engines/final_records/creation_service.py").read_text(encoding="utf-8-sig")
PROJECTION = (ROOT / "app/engines/platform_notifications/workspace_projection.py").read_text(encoding="utf-8-sig")
PROVIDER_ROUTER = (ROOT / "app/engines/platform_notifications/provider_router.py").read_text(encoding="utf-8-sig")
DESTINATION = (ROOT / "frontend/tenant-portal/lib/notificationDestination.ts").read_text(encoding="utf-8-sig")
LEGACY_ROUTE = (ROOT / "frontend/tenant-portal/app/(tenant)/service-jobs/page.tsx").read_text(encoding="utf-8-sig")
DASHBOARD = (ROOT / "app/engines/dashboard_command_center/service.py").read_text(encoding="utf-8-sig")
DASHBOARD_UI = (ROOT / "frontend/super-admin/app/admin/dashboard/page.tsx").read_text(encoding="utf-8-sig")


def test_new_booking_notification_targets_the_created_job():
    assert "job_id=job.id" in CREATION
    assert 'source_record_type="service_jobs", source_record_id=job_id' in CREATION
    assert 'action_url=f"/home-services/bookings-jobs?job_id={job_id}"' in CREATION


def test_provider_notification_list_returns_trusted_projection():
    handler = PROVIDER_ROUTER.split("async def provider_list_notifications", 1)[1].split(
        '@provider_notif_router.get("/workspace"', 1
    )[0]
    assert "get_workspace_items" in handler
    assert "read_status=read_status" in handler
    assert '"booking.new": "/home-services/bookings-jobs"' in PROJECTION


def test_historical_notification_route_has_safe_compatibility():
    assert 'candidate.startsWith("//")' in DESTINATION
    assert 'candidate === "/service-jobs"' in DESTINATION
    assert 'redirect("/home-services/bookings-jobs")' in LEGACY_ROUTE


def test_dashboard_distinguishes_job_and_complaint_sla():
    assert "j.sla_breached_at IS NOT NULL" in DASHBOARD
    assert '"complaint_sla_breaches": complaint_sla_breaches' in DASHBOARD
    assert 'label="Job SLA Breaches"' in DASHBOARD_UI
    assert "complaint SLA breaches" in DASHBOARD_UI


def test_dashboard_live_job_link_uses_supported_drawer_parameter():
    assert "/admin/home-services/bookings-jobs?job_id=${item.id}" in DASHBOARD_UI
    assert "/admin/home-services/bookings-jobs?job=${item.id}" not in DASHBOARD_UI


def test_dashboard_readiness_reports_real_missing_deductions():
    assert '"missing_deductions": missing_completed_deductions' in DASHBOARD
    assert "missing in the last 30 days" in DASHBOARD_UI


def test_dashboard_operational_queries_are_home_services_scoped():
    operations = DASHBOARD.split("async def get_operations_snapshot", 1)[1].split(
        "async def get_request_demand_by_area", 1
    )[0]
    assert operations.count("t.vertical='home_services'") >= 6
