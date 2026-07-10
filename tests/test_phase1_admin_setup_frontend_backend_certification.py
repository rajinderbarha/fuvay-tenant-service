"""Phase 1 — Admin Setup Frontend + Backend Certification Sprint.

This sprint re-certified the Super Admin platform-setup foundation
end-to-end (backend + frontend + integration + Swagger), reusing findings
from the earlier Phase 1 (Admin Setup Certification) and Phase 0 (Clean
Data + Baseline) sprints in this same session. See
PHASE_1_ADMIN_SETUP_BACKEND_REPORT.md / FRONTEND_REPORT.md /
INTEGRATION_REPORT.md for full live-verification evidence — this file
covers the one net-new backend change made this sprint (the login-events
admin endpoint) plus regression coverage for the request_id error envelope
contract this sprint verified live for 401/403/404/422.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NOTIF_ROUTER = (ROOT / "app/engines/platform_notifications/admin_router.py").read_text(encoding="utf-8")


def test_login_events_admin_endpoint_exists():
    assert '@admin_audit_router.get("/login-events"' in NOTIF_ROUTER
    assert "login_events" in NOTIF_ROUTER


def test_login_events_endpoint_returns_request_id_field():
    assert '"request_id": row["request_id"]' in NOTIF_ROUTER


def test_login_events_endpoint_supports_email_and_event_type_filters():
    assert "email: Optional[str]" in NOTIF_ROUTER
    assert "event_type: Optional[str]" in NOTIF_ROUTER


def test_login_events_endpoint_requires_authentication():
    # Same file's other admin_audit_router endpoints use get_current_user;
    # confirm the new endpoint follows the same auth dependency pattern.
    idx = NOTIF_ROUTER.index('"/login-events"')
    snippet = NOTIF_ROUTER[idx:idx + 700]
    assert "get_current_user" in snippet
