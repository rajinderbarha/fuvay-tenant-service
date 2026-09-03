"""
P0 Fix — Provider Onboarding Page
Tests that /v1/admin/onboarding/providers loads from real tables (not the
non-existent provider_onboarding_statuses table) and that the frontend page
no longer shows a red error.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# ── 1. Backend: route file exists and imports cleanly ───────────────────────

def test_admin_router_imports():
    from app.engines.provider_portal import admin_router as ar
    assert hasattr(ar, "admin_router")


def test_admin_router_no_nonexistent_table_reference():
    src = Path("app/engines/provider_portal/admin_router.py").read_text(encoding="utf-8")
    assert "provider_onboarding_statuses" not in src, \
        "admin_router must not reference the non-existent provider_onboarding_statuses table"


def test_queue_cte_uses_tenants_table():
    src = Path("app/engines/provider_portal/admin_router.py").read_text(encoding="utf-8")
    assert "FROM tenants" in src or "FROM tenants t" in src


def test_enrich_row_function_exists():
    src = Path("app/engines/provider_portal/admin_router.py").read_text(encoding="utf-8")
    assert "_enrich_row" in src


def test_review_status_map_present():
    src = Path("app/engines/provider_portal/admin_router.py").read_text(encoding="utf-8")
    assert "_REVIEW_STATUS_MAP" in src
    assert "pending_review" in src
    assert "changes_requested" in src
    assert "not_submitted" in src


def test_summary_returned_in_response():
    src = Path("app/engines/provider_portal/admin_router.py").read_text(encoding="utf-8")
    assert '"summary"' in src or "'summary'" in src


def test_approve_endpoint_exists():
    src = Path("app/engines/provider_portal/admin_router.py").read_text(encoding="utf-8")
    assert "/approve" in src


def test_reject_endpoint_exists():
    src = Path("app/engines/provider_portal/admin_router.py").read_text(encoding="utf-8")
    assert "/reject" in src


def test_request_changes_endpoint_exists():
    src = Path("app/engines/provider_portal/admin_router.py").read_text(encoding="utf-8")
    assert "/request-changes" in src


# ── 2. Backend: tenant admin_service changes ─────────────────────────────────

def test_valid_verification_statuses_includes_changes_requested():
    from app.engines.tenant_engine.admin_service import VALID_VERIFICATION_STATUSES
    assert "changes_requested" in VALID_VERIFICATION_STATUSES


def test_verify_tenant_accepts_changes_requested():
    src = Path("app/engines/tenant_engine/admin_service.py").read_text(encoding="utf-8")
    assert '"changes_requested"' in src or "'changes_requested'" in src


# ── 3. Backend: enrich_row logic ─────────────────────────────────────────────

def test_enrich_row_maps_verification_status():
    import importlib
    import app.engines.provider_portal.admin_router as mod
    row = {
        "tenant_id": "00000000-0000-0000-0000-000000000001",
        "verification_status": "pending",
        "tenant_status": "trial",
        "profile_completion_percentage": 80,
    }
    result = mod._enrich_row(dict(row))
    assert result["review_status"] == "pending_review"
    assert result["onboarding_status"] == "submitted"
    assert result["readiness_status"] == "ready_for_review"
    assert result["bookable_status"] == "pending_approval"


def test_enrich_row_not_started():
    import app.engines.provider_portal.admin_router as mod
    row = {
        "tenant_id": "00000000-0000-0000-0000-000000000002",
        "verification_status": "not_started",
        "tenant_status": "trial",
        "profile_completion_percentage": 60,
    }
    result = mod._enrich_row(dict(row))
    assert result["review_status"] == "not_submitted"
    assert result["onboarding_status"] == "setup_in_progress"
    assert result["readiness_status"] == "incomplete"


def test_enrich_row_changes_requested():
    import app.engines.provider_portal.admin_router as mod
    row = {
        "tenant_id": "00000000-0000-0000-0000-000000000003",
        "verification_status": "changes_requested",
        "tenant_status": "trial",
        "profile_completion_percentage": 100,
    }
    result = mod._enrich_row(dict(row))
    assert result["review_status"] == "changes_requested"
    assert result["readiness_status"] == "needs_changes"


def test_enrich_row_approved_active_is_bookable():
    import app.engines.provider_portal.admin_router as mod
    row = {
        "tenant_id": "00000000-0000-0000-0000-000000000004",
        "verification_status": "approved",
        "tenant_status": "active",
        "profile_completion_percentage": 100,
    }
    result = mod._enrich_row(dict(row))
    assert result["review_status"] == "approved"
    assert result["bookable_status"] == "bookable"


def test_enrich_row_rejected():
    import app.engines.provider_portal.admin_router as mod
    row = {
        "tenant_id": "00000000-0000-0000-0000-000000000005",
        "verification_status": "rejected",
        "tenant_status": "rejected",
        "profile_completion_percentage": 100,
    }
    result = mod._enrich_row(dict(row))
    assert result["review_status"] == "rejected"
    assert result["readiness_status"] == "rejected"


# ── 4. Frontend API client ────────────────────────────────────────────────────

def test_api_ts_new_interface_fields():
    src = Path("frontend/super-admin/lib/api.ts").read_text(encoding="utf-8")
    assert "review_status: string" in src
    assert "onboarding_status: string" in src
    assert "readiness_status: string" in src
    assert "bookable_status: string" in src
    assert "profile_completion_percentage: number" in src


def test_api_ts_summary_interface_exists():
    src = Path("frontend/super-admin/lib/api.ts").read_text(encoding="utf-8")
    assert "OnboardingProviderSummary" in src
    assert "pending_review: number" in src
    assert "not_submitted: number" in src
    assert "changes_requested: number" in src
    assert "rejected: number" in src


def test_api_ts_approve_method():
    src = Path("frontend/super-admin/lib/api.ts").read_text(encoding="utf-8")
    assert "approve:" in src or "approve =" in src


def test_api_ts_reject_method():
    src = Path("frontend/super-admin/lib/api.ts").read_text(encoding="utf-8")
    assert "reject:" in src or "reject =" in src


def test_api_ts_request_changes_method():
    src = Path("frontend/super-admin/lib/api.ts").read_text(encoding="utf-8")
    assert "requestChanges" in src


# ── 5. Frontend page ──────────────────────────────────────────────────────────

def test_legacy_page_is_deleted():
    assert not Path("frontend/super-admin/app/admin/onboarding/providers/page.tsx").exists()


def test_page_no_provider_onboarding_statuses_reference():
    src = Path("frontend/super-admin/app/admin/home-services/providers/page.tsx").read_text(encoding="utf-8")
    assert "provider_onboarding_statuses" not in src


def test_legacy_page_is_not_kept_as_redirect_code():
    assert not Path("frontend/super-admin/app/admin/onboarding/providers/page.tsx").exists()


def test_canonical_page_uses_review_api_and_summary_cards():
    src = Path("frontend/super-admin/app/admin/home-services/providers/page.tsx").read_text(encoding="utf-8")
    assert "adminOnboardingProvidersApi.approve" in src
    assert "adminOnboardingProvidersApi.reject" in src
    assert "adminOnboardingProvidersApi.requestChanges" in src
    assert "SummaryCard" in src
    assert "pending_review" in src or "Pending Review" in src


def test_page_links_to_tenant_detail():
    src = Path("frontend/super-admin/app/admin/home-services/providers/page.tsx").read_text(encoding="utf-8")
    assert "/admin/home-services/providers/" in src


def test_page_has_proper_empty_state():
    src = Path("frontend/super-admin/app/admin/home-services/providers/page.tsx").read_text(encoding="utf-8")
    assert "No providers in queue" in src or "onboarding queue" in src.lower()


def test_page_disables_decisions_until_provider_resubmits():
    src = Path("frontend/super-admin/app/admin/home-services/providers/page.tsx").read_text(encoding="utf-8")
    assert 'const canAct = r.review_status === "pending_review"' in src
    assert "after the provider updates and resubmits" in src
