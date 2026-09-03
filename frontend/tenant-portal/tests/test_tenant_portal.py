"""Current tenant portal route and API connectivity certification."""
from pathlib import Path
import re


PORTAL = Path(__file__).resolve().parents[1]
APP = PORTAL / "app"
API = (PORTAL / "lib/api.ts").read_text(encoding="utf-8-sig")
WORKSPACE_API = (PORTAL / "lib/api-tenant-workspaces.ts").read_text(encoding="utf-8-sig")
LAYOUT = (PORTAL / "components/layout/TenantLayout.tsx").read_text(encoding="utf-8-sig")

CANONICAL_HOME_SERVICES_PAGES = [
    "app/(tenant)/dashboard/page.tsx",
    "app/(tenant)/home-services/bookings-jobs/page.tsx",
    "app/(tenant)/home-services/dispatch/page.tsx",
    "app/(tenant)/home-services/availability/page.tsx",
    "app/(tenant)/home-services/services/[[...serviceId]]/page.tsx",
    "app/(tenant)/home-services/team/[[...staffId]]/page.tsx",
    "app/(tenant)/home-services/finance/page.tsx",
    "app/(tenant)/business/coverage-hours/page.tsx",
    "app/(tenant)/inventory/page.tsx",
    "app/(tenant)/customers/page.tsx",
    "app/(tenant)/home-services/reviews/page.tsx",
    "app/(tenant)/home-services/complaints/page.tsx",
    "app/(tenant)/provider/refund-requests/page.tsx",
]

RETIRED_PAGES = [
    "app/(tenant)/jobs/page.tsx",
    "app/(tenant)/jobs/[id]/page.tsx",
    "app/(tenant)/bookings/page.tsx",
    "app/(tenant)/catalog/page.tsx",
    "app/(tenant)/finance/page.tsx",
    "app/(tenant)/provider/service-areas/page.tsx",
    "app/(tenant)/provider/service-options/page.tsx",
    "app/(tenant)/services/page.tsx",
]


def test_canonical_home_services_pages_exist():
    missing = [path for path in CANONICAL_HOME_SERVICES_PAGES if not (PORTAL / path).exists()]
    assert not missing


def test_retired_duplicate_pages_are_deleted():
    remaining = [path for path in RETIRED_PAGES if (PORTAL / path).exists()]
    assert not remaining


def test_sidebar_targets_canonical_home_services_routes():
    for route in (
        "/home-services/bookings-jobs", "/home-services/dispatch",
        "/home-services/availability", "/home-services/services",
        "/home-services/team", "/home-services/finance",
        "/business/coverage-hours", "/inventory",
        "/home-services/reviews", "/home-services/complaints",
        "/provider/refund-requests",
    ):
        assert f'href: "{route}"' in LAYOUT


def test_home_services_pages_do_not_call_fetch_inline():
    violations = []
    for relative in CANONICAL_HOME_SERVICES_PAGES:
        source = (PORTAL / relative).read_text(encoding="utf-8-sig")
        if re.search(r"\bfetch\s*\(", source):
            violations.append(relative)
    assert not violations


def test_api_auth_and_tenant_context_are_centralized():
    assert 'localStorage.getItem("serviceos_tenant_id")' in API
    assert '"Authorization"' in API
    assert "process.env.NEXT_PUBLIC_API_URL" in API


def test_canonical_home_services_api_clients_exist():
    for client in (
        "servicesWorkspaceApi", "homeServicesSetupApi", "providerServiceAreasApi",
        "providerServiceOptionApi", "providerTeamMembersApi",
    ):
        assert client in API + WORKSPACE_API
