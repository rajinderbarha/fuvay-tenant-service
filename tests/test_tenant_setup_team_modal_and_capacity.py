"""Regression guards for tenant setup team creation and slot capacity."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEAM_MODAL = (ROOT / "frontend/tenant-portal/components/onboarding/AddTeamMemberWizard.tsx").read_text(encoding="utf-8")
TEAM_PAGE = (ROOT / "frontend/tenant-portal/app/(onboarding)/tenant/home-services/setup/staff/page.tsx").read_text(encoding="utf-8")
SLOTS = (ROOT / "app/engines/home_service_booking/provider_slot_service.py").read_text(encoding="utf-8")
OVERVIEW = (ROOT / "app/engines/vertical_catalog/home_services_setup_service.py").read_text(encoding="utf-8")
FINAL_CREATION = (ROOT / "app/engines/final_records/creation_service.py").read_text(encoding="utf-8")
PROVIDER_ROUTER = (ROOT / "app/engines/provider_portal/router.py").read_text(encoding="utf-8")
TENANT_API = (ROOT / "frontend/tenant-portal/lib/api.ts").read_text(encoding="utf-8")
SETUP_ENTRY = (ROOT / "frontend/tenant-portal/app/(onboarding)/tenant/home-services/setup/page.tsx").read_text(encoding="utf-8")
NAV_CONFIG = (ROOT / "frontend/tenant-portal/lib/nav-config.ts").read_text(encoding="utf-8")
PROFILE_OVERVIEW = (ROOT / "frontend/tenant-portal/components/business-profile/OverviewTab.tsx").read_text(encoding="utf-8")


def test_team_add_and_edit_open_the_same_modal():
    assert "<AddTeamMemberWizard" in TEAM_PAGE
    assert 'role="dialog"' in TEAM_MODAL
    assert 'aria-modal="true"' in TEAM_MODAL
    assert 'aria-labelledby="team-member-dialog-title"' in TEAM_MODAL
    assert 'event.key === "Escape"' in TEAM_MODAL
    assert "document.body.style.overflow = \"hidden\"" in TEAM_MODAL


def test_team_modal_has_no_manual_job_limit():
    assert "Maximum simultaneous jobs" not in TEAM_MODAL
    assert "max_concurrent_jobs:" not in TEAM_MODAL
    assert "Slot capacity is calculated automatically" in TEAM_MODAL
    assert "servicesLoadFailed" in TEAM_MODAL
    assert "Wait for the enabled services to finish loading" in TEAM_MODAL


def test_new_technician_inherits_every_open_business_day():
    assert "inherit_business_hours: isTechnician" in TEAM_MODAL
    assert "inherit_business_hours" in PROVIDER_ROUTER
    assert "BUSINESS_HOURS_REQUIRED" in PROVIDER_ROUTER
    assert "for rule in business_rules" in PROVIDER_ROUTER
    assert "'staff_member'" in PROVIDER_ROUTER


def test_slot_capacity_is_service_and_weekday_scoped():
    assert "master_service_id" in SLOTS
    assert "supported_offering_ids" in SLOTS
    assert "provider_availability_rules" in SLOTS
    assert "day.isoweekday() % 7" in SLOTS
    assert "return max(technicians, 0)" in SLOTS
    assert "pg_advisory_xact_lock" in FINAL_CREATION
    assert "home-service-slot:" in FINAL_CREATION


def test_review_readiness_uses_canonical_team_and_service_coverage():
    assert "compute_team_summary" in OVERVIEW
    assert "compute_service_coverage" in OVERVIEW
    assert 'scope_type=\'provider\'' in OVERVIEW
    assert "priced_count == published_count" in OVERVIEW


def test_team_readiness_has_a_non_paginated_canonical_endpoint():
    assert '@router.get("/team-members/readiness")' in PROVIDER_ROUTER
    assert "compute_team_summary" in PROVIDER_ROUTER
    assert 'apiFetch<TeamReadinessSummary>("/v1/provider/team-members/readiness")' in TENANT_API


def test_setup_entry_and_operational_links_do_not_open_legacy_setup_pages():
    assert 'redirect("/tenant/home-services/setup/overview")' in SETUP_ENTRY
    assert 'href: "/tenant/setup/services"' not in NAV_CONFIG
    assert 'href="/tenant/setup/services"' not in PROFILE_OVERVIEW
    assert 'href="/provider/staff"' not in PROFILE_OVERVIEW
