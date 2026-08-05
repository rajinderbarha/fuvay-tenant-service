"""Regression: "Add services" on the Services & Pricing workspace pointed
at a route that doesn't exist (/tenant/setup/services), a dead link found
while wiring the still-open Add Services item. The real, functional
enable-service flow lives at the onboarding services-pricing page
(same enable/types/brands/pricing/publish endpoints this workspace itself
uses) -- fixed to link there with a return_to param so Back/Save & continue
return to the workspace instead of advancing into the onboarding flow,
which has no meaning for an already-active tenant.
"""
import os
import pathlib

BASE = str(pathlib.Path(__file__).parent.parent.resolve())
WORKSPACE_PAGE = os.path.join(
    BASE, "frontend/tenant-portal/app/(tenant)/home-services/services/[[...serviceId]]/page.tsx"
)
ONBOARDING_PAGE = os.path.join(
    BASE, "frontend/tenant-portal/app/(onboarding)/tenant/home-services/setup/services-pricing/page.tsx"
)
REAL_PAGE_DIR = os.path.join(
    BASE, "frontend/tenant-portal/app/(onboarding)/tenant/home-services/setup/services-pricing"
)


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


class TestAddServicesLink:
    def test_dead_route_no_longer_referenced(self):
        c = _read(WORKSPACE_PAGE)
        assert "/tenant/setup/services" not in c

    def test_links_to_the_real_existing_page(self):
        c = _read(WORKSPACE_PAGE)
        assert "/tenant/home-services/setup/services-pricing?return_to=" in c
        assert os.path.isdir(REAL_PAGE_DIR)

    def test_onboarding_page_honors_return_to_instead_of_advancing_onboarding(self):
        c = _read(ONBOARDING_PAGE)
        assert "useSearchParams" in c
        assert 'returnTo = searchParams.get("return_to")' in c
        assert "router.push(returnTo ||" in c

    def test_onboarding_page_wrapped_in_suspense_for_use_search_params(self):
        c = _read(ONBOARDING_PAGE)
        assert "<Suspense fallback={null}>" in c
        assert "<ServicesPricingPageContent />" in c
