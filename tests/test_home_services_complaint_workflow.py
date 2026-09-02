"""Contract tests for provider/customer-owned Home Services remedies."""
from pathlib import Path

from app.engines.complaints.constants import (
    ALLOWED_TRANSITIONS,
    STATUS_AWAITING_PROVIDER,
    STATUS_RESOLUTION_PROPOSED,
    STATUS_UNDER_ADMIN_REVIEW,
)


ROOT = Path(__file__).resolve().parents[1]


def test_admin_complaint_case_routes_are_filtered_from_mount():
    main = (ROOT / "app/main.py").read_text(encoding="utf-8")
    assert 'if "/complaints" not in getattr(route, "path", "")' in main
    assert "admin_complaint_router," not in main


def test_admin_navigation_has_no_complaint_case_workspace():
    layout = (ROOT / "frontend/super-admin/components/layout/AdminLayout.tsx").read_text(encoding="utf-8")
    code = "\n".join(line for line in layout.splitlines() if not line.strip().startswith("//"))
    assert 'href: "/admin/complaints"' not in code
    assert 'href: "/admin/home-services/complaints"' not in code


def test_customer_rejection_returns_to_provider():
    allowed = ALLOWED_TRANSITIONS[STATUS_RESOLUTION_PROPOSED]
    assert STATUS_AWAITING_PROVIDER in allowed
    assert STATUS_UNDER_ADMIN_REVIEW not in allowed


def test_provider_and_customer_routes_remain_mounted_in_main():
    main = (ROOT / "app/main.py").read_text(encoding="utf-8")
    assert "customer_complaint_router" in main
    assert "provider_complaint_router" in main


def test_sla_penalty_uses_canonical_credit_and_health_engines():
    worker = (ROOT / "app/jobs/complaint_sla.py").read_text(encoding="utf-8")
    assert "charge_complaint_sla_penalty" in worker
    assert "compute_health_score" in worker
    assert "run_ai_auto_start()" not in worker.split("async def run_all()", 1)[1]
