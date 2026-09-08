"""Cross-step regressions for plan -> team -> coverage -> finance onboarding."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROVIDER = (ROOT / "app/engines/provider_portal/router.py").read_text(encoding="utf-8")
FINANCE = (ROOT / "app/engines/vertical_catalog/tenant_finance_readiness_router.py").read_text(encoding="utf-8")
TEAM_PAGE = (ROOT / "frontend/tenant-portal/app/(onboarding)/tenant/home-services/setup/staff/StaffSetupPage.tsx").read_text(encoding="utf-8")
COVERAGE_PAGE = (ROOT / "frontend/tenant-portal/app/(onboarding)/tenant/home-services/setup/coverage-availability/page.tsx").read_text(encoding="utf-8")
FINANCE_PAGE = (ROOT / "frontend/tenant-portal/app/(onboarding)/tenant/home-services/setup/finance/page.tsx").read_text(encoding="utf-8")


def test_staff_step_does_not_require_the_next_steps_business_hours():
    assert "include_availability: bool = Query(True)" in PROVIDER
    assert "providerTeamMembersApi.readiness(false)" in TEAM_PAGE
    assert "providerTeamMembersApi.coverage(false)" in TEAM_PAGE


def test_role_conversion_and_owner_reactivation_cannot_bypass_seats():
    update = PROVIDER[PROVIDER.index("async def update_team_member"):PROVIDER.index("async def delete_team_member")]
    assert "was_seat_consumer" in update
    assert "assert_seat_available" in update
    invite_start = PROVIDER.index("async def activate_team_member_account")
    invite_end = PROVIDER.index("async def get_team_member(\n", invite_start)
    invite = PROVIDER[invite_start:invite_end]
    assert "SET status='active'" not in invite


def test_business_hour_toggle_has_one_mutation_path_and_dynamic_inheritance_copy():
    assert '<span onClick={() => handleToggleDay' not in COVERAGE_PAGE
    editor = (ROOT / "frontend/tenant-portal/components/availability/WeeklyScheduleEditor.tsx").read_text(encoding="utf-8")
    assert "Staff and managers do not add booking capacity" in editor
    assert "future schedule edits apply immediately" in (ROOT / "frontend/tenant-portal/components/onboarding/AddTeamMemberWizard.tsx").read_text(encoding="utf-8")


def test_finance_is_cash_upi_and_invoice_only():
    assert "resolve_activation_funding_quote" not in FINANCE
    assert '"activation_requirements"' not in FINANCE
    assert 'key: "accepts_cash"' in FINANCE_PAGE
    assert 'key: "accepts_upi"' in FINANCE_PAGE
    assert "Activation requirements pending" not in FINANCE_PAGE
    assert "Select Cash or UPI before continuing." in FINANCE_PAGE
