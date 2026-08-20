"""Regression coverage for the tenant service publication boundary.

Services & Pricing (step 4) can only set draft pricing -- publish_service
(admin_catalog/tenant_service.py) requires an active coverage area, which
is configured in Coverage & Availability (step 5), one step later.

Coverage must not publish because an unrelated pricing omission must never
trap a tenant on the coverage step. Review & Submit is the explicit, single
publication boundary and reports named service blockers with an edit action.
"""
import os
import pathlib

BASE = str(pathlib.Path(__file__).parent.parent.resolve())
COVERAGE_PAGE = os.path.join(
    BASE, "frontend/tenant-portal/app/(onboarding)/tenant/home-services/setup/coverage-availability/page.tsx"
)
REVIEW_PAGE = os.path.join(
    BASE, "frontend/tenant-portal/app/(onboarding)/tenant/home-services/setup/review/page.tsx"
)
SERVICES_PRICING_PAGE = os.path.join(
    BASE, "frontend/tenant-portal/app/(onboarding)/tenant/home-services/setup/services-pricing/page.tsx"
)


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


class TestCoverageAvailabilityDoesNotPublish:
    def test_does_not_import_setup_api(self):
        c = _read(COVERAGE_PAGE)
        assert "homeServicesSetupApi" not in c

    def test_save_and_continue_validates_only_coverage_owned_requirements(self):
        c = _read(COVERAGE_PAGE)
        start = c.index("async function handleSaveAndContinue")
        end = c.index("\n  }", start)
        block = c[start:end]
        assert "activeCoverageCount === 0" in block
        assert "openDaysCount === 0" in block
        assert 'router.push("/tenant/home-services/setup/staff")' in block
        assert "listEnabled()" not in block
        assert "publish(" not in block


class TestReviewPagePublishRetry:
    def test_imports_setup_api(self):
        c = _read(REVIEW_PAGE)
        assert "homeServicesSetupApi" in c

    def test_retry_publish_handler_exists(self):
        c = _read(REVIEW_PAGE)
        assert "async function retryPublishServices" in c
        assert "homeServicesSetupApi.publish(svc.tenant_service_id)" in c

    def test_retry_button_wired_only_to_incomplete_services_pricing_section(self):
        c = _read(REVIEW_PAGE)
        assert 's.key === "SERVICES_PRICING" && s.status !== "complete"' in c
        assert "onRetryPublish" in c
        assert "Validate & publish" in c

    def test_publish_failures_name_the_service_and_offer_resolution(self):
        c = _read(REVIEW_PAGE)
        assert "serviceNameByPair" in c
        assert "Some enabled services still need attention before publication" in c
        assert "turn off an offering you do not want to publish" in c
        load_call = c.index("      load();", c.index("async function retryPublishServices"))
        error_call = c.index("        setError(`Some enabled services", load_call)
        assert load_call < error_call


class TestServicesPricingPageNeverPublishesItself:
    def test_services_pricing_step_still_only_saves_draft(self):
        """Confirms the documented root cause: this step intentionally can't
        publish (no coverage area exists yet at this point in the flow)."""
        c = _read(SERVICES_PRICING_PAGE)
        assert "homeServicesSetupApi.saveDraft" in c
        assert "homeServicesSetupApi.publish(" not in c
