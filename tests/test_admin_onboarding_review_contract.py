"""Regression coverage for the Admin provider-review handoff."""
from pathlib import Path

from app.main import app


def test_business_document_review_route_is_registered():
    routes = set()
    for included in app.routes:
        candidates = included.original_router.routes if type(included).__name__ == "_IncludedRouter" else [included]
        for route in candidates:
            if getattr(route, "path", None):
                routes.add((route.path, frozenset(getattr(route, "methods", None) or set())))
    assert any(
        path == "/v1/admin/onboarding/providers/{tenant_id}/documents/{document_id}/review"
        and "POST" in methods
        for path, methods in routes
    )


def test_submission_and_queue_use_the_same_tenant_state_projection():
    submit_source = Path("app/engines/vertical_catalog/service.py").read_text(encoding="utf-8")
    queue_source = Path("app/engines/provider_portal/admin_router.py").read_text(encoding="utf-8")
    assert "verification_status='pending'" in submit_source
    assert "status='under_review'" in submit_source
    assert "t.verification_status" in queue_source
    assert "_build_admin_review_context" in queue_source
    assert 'if not review["can_approve"]' in queue_source


def test_admin_preview_opens_tab_before_authenticated_fetch():
    source = Path("frontend/super-admin/lib/open-admin-media-preview.ts").read_text(encoding="utf-8")
    assert source.index('window.open("about:blank"') < source.index("await fetch(")
    assert "serviceos_admin_token" in source
    assert "URL.revokeObjectURL" in source


def test_onboarding_review_ui_exposes_document_decisions_and_server_gate():
    source = Path("frontend/super-admin/app/admin/home-services/providers/page.tsx").read_text(encoding="utf-8")
    assert "Verification documents" in source
    assert "reviewDocument" in source
    assert 'decision: "changes_requested"' in source
    assert "!r.can_approve" in source
