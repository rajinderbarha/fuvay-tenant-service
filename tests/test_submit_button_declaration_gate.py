"""Regression: Submit for review stayed disabled even after checking all 3
declaration checkboxes.

The button's enabled condition used overview.can_submit, a server flag that
folds in "declarations already accepted in the database" -- a snapshot
taken BEFORE the tenant checks the boxes on this very page. The actual
accept() call only happens inside doSubmit(), one click later. So checking
all 3 boxes updated local state but never changed the stale server flag,
and the button never re-enabled without an extra, unprompted "Save draft"
click first (which persists the declarations and refetches the overview).

Fix: expose sections_ready (required-sections completeness only, never
gated on declarations) from get_setup_overview, and have the frontend gate
the button on sections_ready + its own up-to-date local checkbox state
instead of the stale combined can_submit flag. The server-side submit
endpoint (service.py::submit_for_review) already re-validates everything
fresh and remains the real authority -- this only fixes premature
client-side disabling.
"""
import os
import pathlib

BASE = str(pathlib.Path(__file__).parent.parent.resolve())
OVERVIEW = os.path.join(BASE, "app/engines/vertical_catalog/home_services_setup_service.py")
REVIEW_PAGE = os.path.join(
    BASE, "frontend/tenant-portal/app/(onboarding)/tenant/home-services/setup/review/page.tsx"
)
API_TYPES = os.path.join(BASE, "frontend/tenant-portal/lib/api.ts")


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


class TestSectionsReadyExposed:
    def test_backend_returns_sections_ready_not_gated_on_declarations(self):
        c = _read(OVERVIEW)
        assert '"sections_ready": review_ready,' in c

    def test_frontend_type_declares_sections_ready(self):
        c = _read(API_TYPES)
        start = c.index("export interface HomeServicesSetupOverview")
        end = c.index("export interface DeclarationItem")
        block = c[start:end]
        assert "sections_ready: boolean;" in block


class TestSubmitButtonUsesFreshLocalDeclarationState:
    def test_can_submit_uses_sections_ready_not_stale_can_submit(self):
        c = _read(REVIEW_PAGE)
        assert "overview.sections_ready && allChecked && !isLockedForReview" in c
        assert "overview.can_submit && allChecked" not in c

    def test_server_remains_final_authority_on_actual_submit(self):
        """doSubmit still round-trips through the real accept + submit
        endpoints -- this fix only touches the button's local enablement,
        never bypasses server-side validation."""
        c = _read(REVIEW_PAGE)
        start = c.index("async function doSubmit")
        end = c.index("if (loading)")
        block = c[start:end]
        assert "onboardingDeclarationsApi.accept(keys)" in block
        assert "homeServicesSetupOverviewApi.submitForReview()" in block
