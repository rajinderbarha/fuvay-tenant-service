"""Regression: nothing in tenant onboarding ever called the publish endpoint.

Services & Pricing (step 4) can only set draft pricing -- publish_service
(admin_catalog/tenant_service.py) requires an active coverage area, which
is configured in Coverage & Availability (step 5), one step LATER. No page
anywhere in the onboarding flow ever called homeServicesSetupApi.publish(),
so tenant_services stayed in setup_status='draft' forever no matter how
completely a tenant configured pricing -- Services & Pricing showed
"incomplete" on Review & Submit with no way to fix it.

Fix: Coverage & Availability's Save & Continue now publishes eligible
draft services once coverage exists (the earliest point both of
publish_service's requirements are satisfiable), and Review & Submit
offers a "Publish now" retry for tenants who already passed that step
before this fix existed.
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


class TestCoverageAvailabilityAutoPublish:
    def test_imports_setup_api(self):
        c = _read(COVERAGE_PAGE)
        assert "homeServicesSetupApi" in c

    def test_save_and_continue_publishes_eligible_draft_services(self):
        c = _read(COVERAGE_PAGE)
        start = c.index("async function handleSaveAndContinue")
        end = c.index("\n  }", start)
        block = c[start:end]
        assert "listEnabled()" in block
        assert 'svc.setup_status === "published"' in block
        assert "homeServicesSetupApi.publish(svc.tenant_service_id)" in block

    def test_publish_failures_block_navigation_with_a_visible_error(self):
        c = _read(COVERAGE_PAGE)
        start = c.index("async function handleSaveAndContinue")
        end = c.index("\n  }", start)
        block = c[start:end]
        assert "publishErrors" in block
        assert "setError(" in block
        assert "return;" in block


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


class TestServicesPricingPageNeverPublishesItself:
    def test_services_pricing_step_still_only_saves_draft(self):
        """Confirms the documented root cause: this step intentionally can't
        publish (no coverage area exists yet at this point in the flow)."""
        c = _read(SERVICES_PRICING_PAGE)
        assert "homeServicesSetupApi.saveDraft" in c
        assert "homeServicesSetupApi.publish(" not in c
